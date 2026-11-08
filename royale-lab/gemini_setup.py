"""Load one server-side API credential, or store it using a hidden terminal prompt."""
from __future__ import annotations

import getpass
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent


def load_key(directory=ROOT):
    """A minimal .env reader: no evaluation, expansion, or unrelated settings."""
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return True
    file = Path(directory) / ".env"
    if not file.is_file():
        return False
    for line in file.read_text().splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "GEMINI_API_KEY":
            key = value.strip()
            if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
                key = key[1:-1]
            if key:
                os.environ["GEMINI_API_KEY"] = key
                return True
    return False


def store_key(key, directory=ROOT):
    key = key.strip()
    if len(key) < 20 or any(char.isspace() for char in key):
        raise ValueError("Paste the complete API key without spaces or line breaks.")
    directory = Path(directory)
    file = directory / ".env"
    lines = file.read_text().splitlines() if file.exists() else []
    lines = [line for line in lines if line.partition("=")[0].strip() != "GEMINI_API_KEY"]
    lines.append("GEMINI_API_KEY=" + key)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, prefix=".gemini-key-", delete=False) as handle:
            temporary = Path(handle.name)
            os.chmod(temporary, 0o600)
            handle.write("\n".join(lines) + "\n")
        temporary.replace(file)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    print("Create a key at https://aistudio.google.com/apikey using the project with your Gemini credits.")
    print("Paste it below. Input is hidden. It stays in the ignored local .env file; no API call is made.")
    try:
        value = getpass.getpass("Gemini API key: ")
        store_key(value)
    except (ValueError, EOFError, KeyboardInterrupt) as error:
        print("Setup not completed." + (" " + str(error) if isinstance(error, ValueError) else ""))
        raise SystemExit(1)
    print("Key saved locally. Run: python3 serve.py --enable-gemini")
    print("Then open http://127.0.0.1:8501/ai.html")
