"""No real credentials or network calls. All exports and state live in temp directories."""
import csv
from contextlib import closing
from io import BytesIO
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gemini_briefing import briefing_context, current_insights, export_insights
from gemini_guard import GeminiExplainer, BudgetError, MAX_ATTEMPTS
from gemini_setup import load_key, store_key
from serve import DashboardHandler

ROOT = Path(__file__).resolve().parents[1]


class HandlerProbe(DashboardHandler):
    def __init__(self, explainer, topics, root, body, origin="http://127.0.0.1:8501"):
        self.explainer=explainer
        self.briefing_topics=topics
        self.export_root=root
        self.generation_lock=threading.Lock()
        self.path="/api/explain"
        raw=json.dumps(body).encode()
        self.rfile=BytesIO(raw)
        self.headers={"Content-Length":str(len(raw)),"Host":"127.0.0.1:8501","Origin":origin}
        self.server=type("Server",(),{"server_port":8501})()

    def _json(self, value, status=200):
        self.response=value
        self.response_status=status


class BriefingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        raw=json.loads((ROOT/'dist/data.json').read_text())
        self.data,self.topics=briefing_context(raw)
        self.calls=[]

    def tearDown(self):
        self.temp.cleanup()

    def transport(self,op,body):
        self.calls.append((op,body))
        if op=='countTokens':return {"totalTokens":1800}
        return {"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"Mocked explanation for tests only. Evidence F-01; no causal effect is established."}]}}]}

    def explainer(self,enabled=True):
        return GeminiExplainer(self.data,self.root/'allowance.sqlite',enabled=enabled,transport=self.transport)

    def test_topics_are_grounded_and_carry_scope(self):
        self.assertEqual(len(self.topics),4)
        evidence={item['id']:item for item in self.data['evidence']}
        for topic in self.topics:
            self.assertTrue(topic['scope'])
            for fact in topic['facts']:
                self.assertIn(fact['result'],evidence[topic['id']]['result'])
                self.assertIn(fact['alternative'],evidence[topic['id']]['alternative'])

    @patch.dict(os.environ,{'GEMINI_API_KEY':'test-key-not-a-real-credential'})
    def test_four_topics_export_and_reuse_one_shared_budget(self):
        explainer=self.explainer()
        for topic in self.topics:
            handler=HandlerProbe(explainer,self.topics,self.root,{"evidence_id":topic['id']})
            handler.do_POST()
            self.assertEqual(handler.response_status,200)
        with (self.root/'tableau_support/gemini_insights.csv').open() as file:
            rows=list(csv.DictReader(file))
        self.assertEqual(len(rows),4)
        self.assertEqual({r['topic'] for r in rows},{'forecast','machines','guests','budget'})
        self.assertTrue(all(r['generated_at_utc'] and r['evidence_ids'] for r in rows))
        self.assertAlmostEqual(explainer.status()['reserved_usd'],.0148)
        self.assertEqual(explainer.status()['attempts'],4)
        restarted=self.explainer()
        for topic in self.topics:self.assertTrue(restarted.explain(topic['id'])['cached'])
        self.assertEqual(len(self.calls),8)
        self.assertEqual(restarted.status()['attempts'],4)
        self.assertTrue((self.root/'submission/GEMINI_BRIEF.md').exists())

    @patch.dict(os.environ,{'GEMINI_API_KEY':'test-key-not-a-real-credential'})
    def test_saved_responses_remain_readable_with_generation_disabled(self):
        explainer=self.explainer()
        explainer.explain('AI-FORECAST')
        disabled=self.explainer(enabled=False)
        self.assertFalse(disabled.status()['enabled'])
        self.assertEqual(disabled.status()['attempts'],1)
        self.assertEqual(len(current_insights(disabled,self.topics)),1)
        self.assertTrue(disabled.explain('AI-FORECAST')['cached'])
        with self.assertRaises(BudgetError):disabled.explain('AI-BUDGET')
        self.assertEqual(len(self.calls),2)

    def test_disabled_mode_exports_no_placeholder_or_fake_insight(self):
        explainer=self.explainer(enabled=False)
        self.assertEqual(export_insights(explainer,self.topics,self.root)['rows'],0)
        self.assertFalse((self.root/'tableau_support/gemini_insights.csv').exists())
        self.assertEqual(self.calls,[])

    @patch.dict(os.environ,{'GEMINI_API_KEY':'test-key-not-a-real-credential'})
    def test_changed_facts_invalidate_saved_explanation(self):
        explainer=self.explainer()
        explainer.explain('AI-FORECAST')
        raw=json.loads((ROOT/'dist/data.json').read_text())
        next(item for item in raw['evidence'] if item['id']=='F-01')['result']='Changed source result'
        changed,new_topics=briefing_context(raw)
        updated=GeminiExplainer(changed,explainer.db_path,enabled=False,transport=self.transport)
        self.assertEqual(current_insights(updated,new_topics),[])
        self.assertNotEqual(new_topics[0]['context_digest'],self.topics[0]['context_digest'])

    def test_cross_origin_and_arbitrary_prompt_are_refused(self):
        explainer=self.explainer(False)
        wrong_origin=HandlerProbe(explainer,self.topics,self.root,{'evidence_id':'AI-FORECAST'},origin='https://another-site.example')
        wrong_origin.do_POST()
        self.assertEqual(wrong_origin.response_status,403)
        arbitrary=HandlerProbe(explainer,self.topics,self.root,{'prompt':'Run an arbitrary request'})
        arbitrary.do_POST()
        self.assertEqual(arbitrary.response_status,400)
        self.assertEqual(self.calls,[])

    @patch.dict(os.environ,{'GEMINI_API_KEY':'test-key-not-a-real-credential'})
    def test_payment_required_is_explained_without_leaking_or_retrying(self):
        error=HTTPError('https://provider.example',402,'Payment Required',{},
                        BytesIO(b'Private provider body: test-key-not-a-real-credential'))
        explainer=GeminiExplainer(self.data,self.root/'billing.sqlite',enabled=True)
        with patch('gemini_guard.urlopen',side_effect=[BytesIO(b'{"totalTokens":1800}'),error]) as request:
            handler=HandlerProbe(explainer,self.topics,self.root,{'evidence_id':'AI-BUDGET'})
            handler.do_POST()
        self.assertEqual(handler.response_status,502)
        message=handler.response['error']
        self.assertIn('HTTP 402',message)
        self.assertIn('Google AI Studio Billing',message)
        self.assertIn('Prepay balance',message)
        self.assertIn('No automatic retry',message)
        self.assertNotIn('Private provider body',message)
        self.assertNotIn('test-key-not-a-real-credential',message)
        self.assertEqual(request.call_count,2)  # One count, one generation, no retry.
        self.assertEqual(explainer.status()['attempts'],1)
        self.assertAlmostEqual(explainer.status()['reserved_usd'],.0037)
        self.assertEqual(current_insights(explainer,self.topics),[])
        self.assertFalse((self.root/'tableau_support/gemini_insights.csv').exists())

    @patch.dict(os.environ,{'GEMINI_API_KEY':'test-key-not-a-real-credential'})
    def test_legacy_cache_schema_migrates_without_resetting_allowance(self):
        file=self.root/'legacy.sqlite'
        with closing(sqlite3.connect(file)) as connection:
            connection.executescript('CREATE TABLE attempts(id INTEGER PRIMARY KEY,reserved_micro_usd INTEGER NOT NULL,created_at TEXT); CREATE TABLE cache(digest TEXT PRIMARY KEY,response TEXT NOT NULL); INSERT INTO attempts VALUES(1,3700,"old");')
            connection.commit()
        migrated=GeminiExplainer(self.data,file,enabled=False)
        self.assertEqual(migrated.status()['attempts'],1)
        self.assertAlmostEqual(migrated.status()['reserved_usd'],.0037)


class KeySetupTests(unittest.TestCase):
    @patch.dict(os.environ,{},clear=True)
    def test_local_key_is_private_and_other_settings_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'.env').write_text('EXAMPLE_SETTING=keep\n')
            store_key('fake-local-key-for-unit-testing',root)
            self.assertEqual((root/'.env').stat().st_mode&0o777,0o600)
            self.assertIn('EXAMPLE_SETTING=keep',(root/'.env').read_text())
            self.assertTrue(load_key(root))
            self.assertEqual(os.environ['GEMINI_API_KEY'],'fake-local-key-for-unit-testing')

    def test_invalid_key_does_not_create_a_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):store_key('key\nwith whitespace',folder)
            self.assertFalse((Path(folder)/'.env').exists())


if __name__=='__main__':unittest.main()
