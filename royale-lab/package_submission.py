"""Refresh submission archives without including credentials or private runtime state."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent


def package():
    submission = ROOT / "submission"
    submission.mkdir(exist_ok=True)
    for source in [ROOT / "dist/downloads/CLAIMS_AND_EVIDENCE.md", ROOT / "dist/downloads/forecast_methodology.json", ROOT / "dist/downloads/input_audit.json"]:
        shutil.copy2(source, submission / source.name)
    disclosure = (ROOT / "docs/AI_DISCLOSURE.md").read_text()
    usage_file = submission / "GEMINI_USAGE.json"
    if usage_file.exists():
        usage = json.loads(usage_file.read_text())
        disclosure += ("\n\n## Recorded later Gemini briefing use\n\n"
                       "A successful generated-briefing export is included in GEMINI_BRIEF.md. "
                       f"Model: {usage['model']}. Generated topics: {', '.join(usage['brief_topics'])}. "
                       "Dates and evidence identifiers accompany the text. The local allowance record is in GEMINI_USAGE.json; it is not a provider billing statement. "
                       "Review generated wording against the evidence appendix before submission.\n")
    (submission / "AI_DISCLOSURE.md").write_text(disclosure)
    source_paths = [ROOT / name for name in [".gitignore", ".env.example", "README.md", "requirements.txt", "analysis.py", "forecasting.py", "build_analysis.py", "prepare_tableau_support.py", "serve.py", "gemini_guard.py", "gemini_setup.py", "gemini_briefing.py", "package_submission.py"]]
    for directory, suffixes in [("web", {".html", ".css", ".js", ".svg"}), ("docs", {".md"}), ("tests", {".py", ".cjs"}), ("tableau_support", {".csv", ".md"})]:
        source_paths.extend(p for p in (ROOT / directory).rglob("*") if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts)
    source_paths.extend(p for p in submission.iterdir() if p.is_file() and p.suffix in {".md", ".json"})
    for file in source_paths:
        if file.is_symlink():
            raise ValueError("Source archive excludes symlinks")
        if (file.name.startswith(".env") and file.name != ".env.example") or ".runtime" in file.parts:
            raise ValueError("Credential/runtime file excluded")
    with zipfile.ZipFile(submission / "SOURCE_CODE.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(source_paths):
            archive.write(file, Path("royale-lab") / file.relative_to(ROOT))
    with zipfile.ZipFile(submission / "SUBMISSION_MATERIALS.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(submission.iterdir()):
            if file.is_file() and file.name != "SUBMISSION_MATERIALS.zip" and file.suffix in {".md", ".json", ".zip"}:
                archive.write(file, file.name)
    main_text = (submission / "WRITEUP_DRAFT.md").read_text().split("\n\n", 1)[1]
    words = len(main_text.split())
    if words > 400:
        raise ValueError(f"Write-up exceeds 400 words: {words}")
    print(json.dumps({"writeup_words": words, "source_files": len(source_paths), "recorded_gemini_brief": usage_file.exists(),
                      "archive": str(submission / "SUBMISSION_MATERIALS.zip")}, indent=2))


if __name__ == "__main__":
    package()
