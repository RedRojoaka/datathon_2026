"""Grounded briefings and genuine generated-text exports for Tableau."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import tempfile

from gemini_guard import GeminiExplainer, BudgetError
from gemini_setup import load_key

ROOT = Path(__file__).resolve().parent
TOPICS = [
    {"key": "forecast", "id": "AI-FORECAST", "title": "Demand & forecast",
     "question": "What does the forecast tell us about planning coverage?",
     "scope": "Jan–June observations; frozen May–June test; July 1–30, 2025 outlook",
     "sources": ["F-01", "F-02", "F-03"]},
    {"key": "machines", "id": "AI-MACHINES", "title": "Machine health",
     "question": "Why investigate a low earner before replacing it?",
     "scope": "Whole-property January–June 2025 machine analysis",
     "sources": ["M-01", "D-01"]},
    {"key": "guests", "id": "AI-GUESTS", "title": "Tracked guests & loyalty",
     "question": "How should a manager interpret player results and comp costs?",
     "scope": "January–June 2025; tracked player results and separately identified property comp ratios",
     "sources": ["G-01", "C-01"]},
    {"key": "budget", "id": "AI-BUDGET", "title": "Staffing & promotion decisions",
     "question": "What must be true for staffing or a promotion to break even?",
     "scope": "July 1–30, 2025 operating budget; promotion comparison July 19–20",
     "sources": ["B-01", "B-02"]},
]


def briefing_context(data):
    sources = {item["id"]: item for item in data["evidence"]}
    topics, grouped_evidence = [], []
    for topic in TOPICS:
        facts = [sources[key] for key in topic["sources"] if key in sources]
        # Partial test/minimal datasets remain useful; absent topics are omitted.
        if not facts:
            continue
        digest = hashlib.sha256(json.dumps({"topic": topic, "facts": facts}, sort_keys=True).encode()).hexdigest()
        topics.append({**topic, "facts": facts, "context_digest": digest})
        grouped_evidence.append({
            "id": topic["id"], "claim": topic["question"], "scope": topic["scope"],
            "source": "; ".join(item["id"] + ": " + item.get("source", "") for item in facts),
            "result": "\n".join(item["id"] + ": " + item["result"] for item in facts),
            "alternative": "\n".join(item["id"] + ": " + item.get("alternative", "") for item in facts),
            "limitation": "\n".join(item["id"] + ": " + item.get("limitation", "") for item in facts),
        })
    ids = {item["id"] for item in data["evidence"]}
    return {**data, "evidence": list(data["evidence"]) + [item for item in grouped_evidence if item["id"] not in ids]}, topics


def atomic_text(file, value):
    file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=file.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(value)
        temporary.replace(file)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def current_insights(explainer, topics):
    rows = []
    for topic in topics:
        cached = explainer.cached(topic["id"])
        if cached:
            rows.append({"topic": topic["key"], "title": topic["title"], "explanation": cached["text"],
                         "evidence_ids": ", ".join(topic["sources"]), "scope": topic["scope"],
                         "model": cached["model"], "generated_at_utc": cached["generated_at"] or "Legacy cache; timestamp unavailable",
                         "context_digest": topic["context_digest"],
                         "source": "Gemini API; cached genuine response; verify against the evidence appendix"})
    return rows


def export_insights(explainer, topics, root=ROOT):
    """Export only successful real responses. Tests use isolated output directories."""
    rows = current_insights(explainer, topics)
    if not rows:
        return {"rows": 0, "files": []}
    root = Path(root)
    from io import StringIO
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    csv_text = buffer.getvalue()
    files = [root / "tableau_support/gemini_insights.csv", root / "dist/downloads/gemini_insights.csv"]
    for file in files:
        atomic_text(file, csv_text)
    atomic_text(root / "dist/downloads/gemini_insights.json", json.dumps(rows, indent=2))
    markdown = "# Gemini-generated management briefing\n\nReview these explanations against the audited evidence before submission. Tableau filters are not automatically sent to Gemini.\n\n"
    for row in rows:
        markdown += (f"## {row['title']}\n\n{row['explanation']}\n\n"
                     f"Evidence: {row['evidence_ids']}\n\nScope: {row['scope']}\n\n"
                     f"Model: {row['model']} · Generated: {row['generated_at_utc']}\n\n")
    atomic_text(root / "submission/GEMINI_BRIEF.md", markdown)
    atomic_text(root / "submission/GEMINI_USAGE.json", json.dumps({
        "model": explainer.status()["model"], "brief_topics": [r["topic"] for r in rows],
        "allowance": explainer.status(),
        "note": "Conservative local allowance, not a provider billing statement. Append this record to the AI-use disclosure when submitting."
    }, indent=2))
    return {"rows": len(rows), "files": [str(f) for f in files]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", choices=[t["key"] for t in TOPICS] + ["all"], default="all")
    parser.add_argument("--cached-only", action="store_true", help="Export existing cached responses with no API calls")
    args = parser.parse_args()
    load_key()
    data, topics = briefing_context(json.loads((ROOT / "dist/data.json").read_text()))
    explainer = GeminiExplainer(data, ROOT / ".runtime/gemini.sqlite", enabled=not args.cached_only)
    if not args.cached_only and not explainer.enabled:
        parser.error("No key configured. Run python3 gemini_setup.py first. No API call was made.")
    for topic in topics:
        if args.topic not in ["all", topic["key"]]:
            continue
        if args.cached_only:
            continue
        print("Generating or reusing: " + topic["title"], flush=True)
        try:
            result = explainer.explain(topic["id"])
        except (BudgetError, RuntimeError, ValueError) as error:
            print(str(error))
            export_insights(explainer, topics)
            raise SystemExit(1)
        print("Cached response reused." if result["cached"] else "Generated one bounded API response.")
        export_insights(explainer, topics)
    exported = export_insights(explainer, topics)
    print(json.dumps({"exported_topics": exported["rows"], "status": explainer.status()}, indent=2))


if __name__ == "__main__":
    main()
