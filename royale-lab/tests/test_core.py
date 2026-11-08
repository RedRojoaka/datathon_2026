import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import action_cost, validate_plan, player_summary
from forecasting import run_forecast, predict
from gemini_guard import GeminiExplainer, BudgetError, MAX_ATTEMPTS

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('ROYALE_DATA', str(ROOT.parent / 'data'))).expanduser()


class FinancialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'dist/data.json').read_text())
        cls.actions = cls.data['actions']

    def test_lease_cost_includes_only_16_operating_days(self):
        lease = next(a for a in self.actions if a['action_type_id'] == 'A-REPLACE-LEASE')
        self.assertEqual(action_cost(lease, 1), 3380)
        with self.assertRaises(ValueError):
            action_cost(lease, 21)

    def test_plan_constraints_policy_and_target_conflict(self):
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            validate_plan([{'action_type_id':'A-COMP-PILOT','quantity':1},
                           {'action_type_id':'A-COMP-CHANGE','quantity':1}],self.actions)
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            validate_plan([{'action_type_id':'A-MOVE-MACHINE','quantity':1,'targets':['M-1158']},
                           {'action_type_id':'A-REPLACE-LEASE','quantity':1,'targets':['M-1158']}],self.actions)
        with self.assertRaisesRegex(ValueError, 'budget'):
            validate_plan([{'action_type_id':'A-REPLACE-BUY','quantity':5,
                            'targets':['M-1001','M-1002','M-1003','M-1004','M-1005']}],self.actions)

    def test_players_are_deduplicated_before_ahead_count(self):
        frame=pd.DataFrame({'player_id':['a','a','b'], 'tracked_coin_in_usd':[100,100,100],
                            'tracked_payout_usd':[150,20,120], 'tracked_net_usd':[50,-80,20],
                            'theo_usd':[10,10,10], 'comp_cost_usd':[0,0,0]})
        result=player_summary(frame)
        self.assertEqual(result['unique_tracked_players'],2)
        self.assertEqual(result['ahead_share'],.5)
        self.assertEqual(result['tracked_player_net_usd'],-10)

    def test_built_artifacts_reconcile_and_include_dst(self):
        self.assertTrue(all(self.data['meta']['checks'].values()))
        frame=pd.read_csv(ROOT/'dist/downloads/machine_day.csv')
        dst=frame[frame.gaming_date=='2025-03-08']
        self.assertTrue((dst.scheduled_hours<=23).all())
        self.assertFalse(frame.duplicated(['machine_id','gaming_date']).any())
        self.assertEqual(self.data['summary']['off_floor_rows_excluded'],1018)

    def test_promotion_break_even_uses_two_days_after_lead_time(self):
        comparison=self.data['staffing_promotion_comparison']
        promo=comparison['promotion']
        self.assertEqual(promo['event_days'],2)
        self.assertTrue(all(pd.Timestamp(d)>pd.Timestamp('2025-07-14') for d in promo['dates']))
        self.assertAlmostEqual(promo['break_even_additional_wagers_usd']*self.data['forecast']['assumed_theo_hold'],promo['cost_usd'])
        self.assertAlmostEqual(promo['baseline_wagers_usd']*promo['break_even_lift_fraction'],promo['break_even_additional_wagers_usd'])


class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame=pd.read_parquet(DATA/'1_prepared_views/property_day.parquet')
        cls.frame.gaming_date=pd.to_datetime(cls.frame.gaming_date)

    def test_holdout_outcomes_cannot_change_selection_or_test_predictions(self):
        original, predictions, _=run_forecast(self.frame)
        changed=self.frame.copy()
        changed['coin_in_usd']=changed.coin_in_usd.astype(float)
        changed.loc[changed.gaming_date>='2025-05-01','coin_in_usd']*=10
        altered, new_predictions, _=run_forecast(changed)
        self.assertEqual(original['selected_model'],altered['selected_model'])
        self.assertEqual(original['radius_90_usd'],altered['radius_90_usd'])
        np.testing.assert_allclose(predictions.forecast_usd,new_predictions.forecast_usd)

    def test_weekday_forecast_uses_only_training_weekdays(self):
        train=self.frame[self.frame.gaming_date<'2025-05-01'].copy()
        train['coin_in_usd']=train.coin_in_usd.astype(float)
        dates=pd.date_range('2025-07-01',periods=14)
        values=predict(train,dates,'weekday')
        np.testing.assert_allclose(values[:7],values[7:])


class GeminiBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.data={'evidence':[{'id':'F-01','claim':'Test evidence','result':'$10', 'alternative':'Timing','limitation':'Synthetic'}]}
        self.calls=[]

    def tearDown(self):
        self.temp.cleanup()

    def transport(self,op,body):
        self.calls.append((op,body))
        if op=='countTokens':return {'totalTokens':200}
        return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'Bounded evidence explanation.'}]}}]}

    def explainer(self,enabled=True,transport=None):
        return GeminiExplainer(self.data,Path(self.temp.name)/'allowance.sqlite',enabled=enabled,transport=transport or self.transport)

    def test_disabled_means_no_network_and_no_state(self):
        e=self.explainer(False)
        with self.assertRaises(BudgetError):e.explain('F-01')
        self.assertEqual(self.calls,[])
        self.assertFalse(e.db_path.exists())

    @patch.dict(os.environ,{'GEMINI_API_KEY':'mock-key-only'})
    def test_cached_and_persistent_across_restarts(self):
        e=self.explainer()
        self.assertFalse(e.explain('F-01')['cached'])
        restarted=self.explainer()
        self.assertTrue(restarted.explain('F-01')['cached'])
        self.assertEqual(restarted.status()['attempts'],1)
        self.assertAlmostEqual(restarted.status()['reserved_usd'],.0037)
        body=self.calls[1][1]
        self.assertEqual(body['generationConfig']['maxOutputTokens'],1000)
        self.assertNotIn('tools',body)

    @patch.dict(os.environ,{'GEMINI_API_KEY':'mock-key-only'})
    def test_large_input_does_not_generate(self):
        def transport(op,body):
            self.assertEqual(op,'countTokens')
            return {'totalTokens':4001}
        e=self.explainer(transport=transport)
        with self.assertRaises(BudgetError):e.explain('F-01')
        self.assertEqual(e.status()['attempts'],0)

    @patch.dict(os.environ,{'GEMINI_API_KEY':'mock-key-only'})
    def test_failed_generation_keeps_reserve_without_retry(self):
        def transport(op,body):
            self.calls.append(op)
            if op=='countTokens':return {'totalTokens':50}
            raise RuntimeError('Simulated network failure')
        e=self.explainer(transport=transport)
        with self.assertRaises(RuntimeError):e.explain('F-01')
        self.assertEqual(self.calls,['countTokens','generateContent'])
        self.assertEqual(e.status()['attempts'],1)

    @patch.dict(os.environ,{'GEMINI_API_KEY':'mock-key-only'})
    def test_501st_attempt_is_refused_before_generation(self):
        e=self.explainer()
        for _ in range(MAX_ATTEMPTS):e._reserve()
        with self.assertRaises(BudgetError):e.explain('F-01')
        self.assertEqual([op for op,_ in self.calls],['countTokens'])
        self.assertAlmostEqual(e.status()['reserved_usd'],1.85)


if __name__=='__main__':
    unittest.main()
