# Heads Up submission — DataLarp

The participant guide requires **team registration**, followed by a public GitHub repository and the exact commit to build. A video, Tableau workbook, Gemini API integration, and strategy write-up are not listed as requirements for this challenge. The accompanying documentation is supporting material.

| Form field | Value |
| --- | --- |
| Team name | **DataLarp** |
| GitHub repository | **https://github.com/RedRojoaka/datathon_2026** |
| Commit SHA | Full 40-character SHA from the tested, committed, pushed version; obtain it with `git rev-parse HEAD` |
| Bot identity | SteadyAce |

[Mandatory registration](https://docs.google.com/forms/d/e/1FAIpQLSeVRUzERWDfrri24U6kA2tUbjT0530IwudYokp3ZpoxfXVAwA/viewform?usp=sharing&ouid=100967425964110292916) and [submission form](https://forms.gle/Jx9RWE5VgR8dbbcj9) are taken from page 1 of the supplied participant guide. Use the same team name as your registration. The guide contains a placeholder for the deadline, so confirm the actual deadline with the event organizers.

## Final steps

1. In this original workspace, edit the dedicated files in `heads-up-bundle/`, then run `python3 refresh_poker_source.py` from the shared repository root. In a fresh clone, edit `pokerbot/` directly.
2. Run `python -m pytest -q pokerbot/test_agent.py pokerbot/test_strategy.py` in the poker Python environment.
3. From the repository root, run `./tools/check_build.sh`. It must end with `ALL CHECKS PASSED`. Root `agent.py` and `requirements.txt` are required, even though the implementation lives in `pokerbot/`.
4. Review the poker changes, commit them to the existing repository, and push. Do not push the nested `heads-up-bundle` checkout: its origin points at the organizers' repository.
5. Obtain the full SHA with `git rev-parse HEAD`. Confirm that exact commit is visible in the public repository. Re-run the build check if the runtime files changed after validation.
6. Submit **DataLarp**, the repository URL above, and that SHA in the submission form. Registration and form submission require the user's own event identity; the code does not submit forms automatically.

Suggested explicit staging paths after reviewing `git diff` and `git status`:

```sh
git add README.md .dockerignore agent.py requirements.txt docker tools pokerbot refresh_poker_source.py
git diff --cached --stat
git commit -m "Add DataLarp SteadyAce poker bot and validation"
git push origin main
git rev-parse HEAD
```

Your Dashboard Royale files stay in their existing directories. The allowlist in `.dockerignore` keeps them out of the poker image. The root build entry points make the shared repository valid for the poker tournament.

## Optional downloadable source

Run `python pokerbot/package_submission.py` to create a poker-only source ZIP and a SHA-256 manifest in `pokerbot/submission/`. This is convenient for backup and review. The tournament builds your submitted Git commit, not the ZIP.
