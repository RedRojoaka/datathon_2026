"""Create a poker-only source archive from an explicit list of public files."""

import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "pokerbot"


def main():
    files = [ROOT / "agent.py", ROOT / "requirements.txt", ROOT / ".dockerignore",
             ROOT / "refresh_poker_source.py"]
    files += list((ROOT / "docker").glob("Dockerfile.*"))
    files += [ROOT / "tools" / name for name in ("check_build.sh", "smoke_test.py")]
    files += [p for p in PUBLIC.iterdir() if p.is_file() and
              (p.suffix in (".py", ".md") or p.name in
               ("requirements.txt", "requirements-dev.txt", ".gitignore", ".dockerignore"))]
    for folder, suffixes in (("baseline-bots", (".py",)), ("docker", (".base", ".agent")),
                             ("tools", (".py", ".sh"))):
        files += [p for p in (PUBLIC / folder).iterdir() if p.is_file() and p.suffix in suffixes]
    files += list((PUBLIC / "results" / "validation").glob("*.json"))
    files += list((PUBLIC / "results" / "validation").glob("*.txt"))
    files += list((PUBLIC / "results").glob("docker-*.txt"))
    output = PUBLIC / "submission"
    output.mkdir(exist_ok=True)
    manifest = {}
    archive = output / "POKER_SOURCE.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(set(files)):
            if path.is_symlink() or not path.is_file():
                raise SystemExit(f"Invalid source file: {path}")
            name = str(path.relative_to(ROOT))
            data = path.read_bytes()
            manifest[name] = hashlib.sha256(data).hexdigest()
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if path.suffix == ".sh" else 0o100644) << 16
            bundle.writestr(info, data)
        info = zipfile.ZipInfo("SOURCE_MANIFEST.json", date_time=(2026, 11, 8, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        bundle.writestr(info, json.dumps(manifest, indent=2) + "\n")
    (output / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # This is a convenience form draft; it is not evidence of a pushed commit.
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True)
    sha = revision.stdout.strip() if revision.returncode == 0 else None
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "agent.py", "pokerbot/agent.py"],
                             cwd=ROOT, capture_output=True).returncode == 0
    status = subprocess.run(["git", "status", "--porcelain", "--", "agent.py",
                             "requirements.txt", "pokerbot"], cwd=ROOT,
                            capture_output=True, text=True)
    clean = status.returncode == 0 and not status.stdout.strip()
    ready_sha = sha if sha and tracked and clean else "PENDING: commit and push the reviewed poker files first"
    (output / "FORM_FIELDS.txt").write_text(
        "Team name: DataLarp\nRepository: https://github.com/RedRojoaka/datathon_2026\n"
        f"Commit SHA: {ready_sha}\nSubmission: https://forms.gle/Jx9RWE5VgR8dbbcj9\n")
    print(f"Created {archive}: {len(manifest)} files, {archive.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
