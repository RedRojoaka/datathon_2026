"""Refresh the reviewed GitHub snapshot from the local challenge workspace.

Does not change Git remotes, initialize a repository, stage, commit, push, or call Gemini.
Only the explicitly packaged source files and submission archives are copied.
"""
from pathlib import Path, PurePosixPath
import json
import shutil
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
WORKING = ROOT / 'dashboard-royale/royale-lab'


def refresh():
    if not (WORKING / 'package_submission.py').is_file():
        raise SystemExit('This helper is for the original working workspace. In a fresh clone, edit royale-lab directly.')
    destination = ROOT / 'royale-lab'
    if (destination / '.git').exists():
        raise SystemExit('Refusing to export into a nested Git repository.')
    subprocess.run([sys.executable, 'package_submission.py'], cwd=WORKING, check=True)
    count = 0
    with zipfile.ZipFile(WORKING / 'submission/SOURCE_CODE.zip') as archive:
        entries = []
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if info.is_dir():
                continue
            if (path.is_absolute() or '..' in path.parts or path.parts[0] != 'royale-lab'
                    or len(path.parts) < 2 or '\\' in info.filename
                    or stat.S_ISLNK(info.external_attr >> 16)):
                raise ValueError('Unsafe source archive path')
            if (any(p in {'.git', '.runtime', '.venv', 'node_modules'} for p in path.parts)
                    or (path.name.startswith('.env') and path.name != '.env.example')):
                raise ValueError('Credential or local runtime path is not publishable')
            target = ROOT.joinpath(*path.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError('Source archive target escapes the export directory')
            payload = archive.read(info)
            if path.name == '.env.example':
                for line in payload.decode().splitlines():
                    name, separator, value = line.partition('=')
                    if separator and name.strip() == 'GEMINI_API_KEY' and value.strip():
                        raise ValueError('Public API key template must be blank')
            entries.append((target, payload))
        for target, payload in entries:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            count += 1
    output = ROOT / 'submission'
    output.mkdir(exist_ok=True)
    for name in ['SOURCE_CODE.zip', 'SUBMISSION_MATERIALS.zip']:
        shutil.copy2(WORKING / 'submission' / name, output / name)
    print(json.dumps({'source_directory': 'royale-lab', 'source_files': count,
                      'submission_archives': 2, 'gemini_requests': 0}, indent=2))


if __name__ == '__main__':
    refresh()
