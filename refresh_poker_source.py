"""Refresh the public pokerbot/ copy from the editable heads-up-bundle/.

The challenge checkout has its own Git history and is ignored by the shared
repository. This explicit allowlist copies source and reviewed evidence only.
It never changes Git state, starts servers, or calls an API.
"""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "heads-up-bundle"
DESTINATION = ROOT / "pokerbot"
FILES = ("agent.py", "equity.py", "game.py", "evaluator.py",
         "judge_engine.py", "test_agent.py", "test_strategy.py", "benchmark.py",
         "practice_bot.py", "package_submission.py", "requirements.txt", "requirements-dev.txt", ".gitignore",
         ".dockerignore", "START_HERE.md", "STRATEGY.md", "SUBMISSION.md",
         "VALIDATION.md", "AI_DISCLOSURE.md")


def main():
    if not (SOURCE / "agent.py").is_file():
        raise SystemExit("No local heads-up-bundle checkout; edit pokerbot/ directly in a fresh clone.")
    DESTINATION.mkdir(exist_ok=True)
    copied = []
    for name in FILES:
        source = SOURCE / name
        if source.is_file() and not source.is_symlink():
            shutil.copyfile(source, DESTINATION / name)
            copied.append(name)
    for folder in ("baseline-bots", "docker", "tools"):
        for source in (SOURCE / folder).glob("*"):
            if source.is_file() and (source.suffix in (".py", ".sh")
                                     or source.name.startswith("Dockerfile.")):
                if source.is_symlink():
                    raise SystemExit(f"Refusing symlink: {source}")
                target = DESTINATION / folder / source.name
                target.parent.mkdir(exist_ok=True)
                shutil.copy2(source, target)
                copied.append(str(source.relative_to(SOURCE)))
                if folder in ("docker", "tools"):
                    (ROOT / folder).mkdir(exist_ok=True)
                    shutil.copy2(source, ROOT / folder / source.name)
    # Docker's dependency-install step can only see the root requirements file.
    shutil.copyfile(SOURCE / "requirements.txt", ROOT / "requirements.txt")
    # Preserve the organizer's README alongside our project-specific entry page.
    shutil.copyfile(SOURCE / "README.md", DESTINATION / "PARTICIPANT_BUNDLE.md")
    if (SOURCE / "START_HERE.md").is_file():
        shutil.copyfile(SOURCE / "START_HERE.md", DESTINATION / "README.md")
    print(f"Refreshed {len(copied)} poker files in {DESTINATION}")


if __name__ == "__main__":
    main()
