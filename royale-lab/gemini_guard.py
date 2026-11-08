"""Opt-in, text-only Gemini explanations with a persistent conservative allowance.

No SDK background retries, tools, batches, model fallbacks or automatic reloads.
Every generation attempt permanently reserves its maximum token cost, even if it fails.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MODEL = "gemini-3.5-flash-lite"
MAX_INPUT = 4000
MAX_OUTPUT = 1000
MAX_ATTEMPTS = 500
# Millionths of a dollar, avoiding floating-point accounting.
MAX_REQUEST_MICRO_USD = 3700  # 4000 × $0.30/M + 1000 × $2.50/M
MAX_TOTAL_MICRO_USD = 5_000_000
API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models/"


class BudgetError(RuntimeError):
    pass


class GeminiExplainer:
    def __init__(self, data, db_path, enabled=False, transport=None):
        self.data = data
        self.db_path = Path(db_path)
        self.enabled = enabled and bool(os.environ.get("GEMINI_API_KEY"))
        self.transport = transport or self._request
        # A disabled server may read existing saved explanations and allowance,
        # but never creates a new state file or sends a request.
        if self.enabled or self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connection() as connection:
                connection.executescript("""
                    CREATE TABLE IF NOT EXISTS attempts (
                        id INTEGER PRIMARY KEY, reserved_micro_usd INTEGER NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS cache (
                        digest TEXT PRIMARY KEY, response TEXT NOT NULL, generated_at TEXT
                    );
                """)
                columns = {row[1] for row in connection.execute("PRAGMA table_info(cache)")}
                if "generated_at" not in columns:
                    connection.execute("ALTER TABLE cache ADD COLUMN generated_at TEXT")

    def _db(self):
        return sqlite3.connect(self.db_path, timeout=30)

    @contextmanager
    def _connection(self):
        connection = self._db()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def status(self):
        attempts, reserved = 0, 0
        cached_count = 0
        if self.db_path.exists():
            with self._connection() as connection:
                attempts, reserved = connection.execute(
                    "SELECT COUNT(*), COALESCE(SUM(reserved_micro_usd), 0) FROM attempts").fetchone()
                cached_count = connection.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        return {"enabled": self.enabled, "model": MODEL, "attempts": attempts,
                "reserved_usd": reserved / 1e6, "max_attempts": MAX_ATTEMPTS,
                "cached_explanations": cached_count,
                "remaining_attempts": max(0, MAX_ATTEMPTS - attempts),
                "max_request_usd": MAX_REQUEST_MICRO_USD / 1e6,
                "max_total_reserve_usd": min(MAX_TOTAL_MICRO_USD, MAX_ATTEMPTS * MAX_REQUEST_MICRO_USD) / 1e6}

    def _reserve(self):
        connection = self._db()
        try:
            connection.execute("BEGIN IMMEDIATE")
            count, spent = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(reserved_micro_usd), 0) FROM attempts").fetchone()
            if count >= MAX_ATTEMPTS or spent + MAX_REQUEST_MICRO_USD > MAX_TOTAL_MICRO_USD:
                raise BudgetError("Local Gemini allowance exhausted. Use the saved evidence explanation.")
            connection.execute("INSERT INTO attempts(reserved_micro_usd) VALUES (?)", (MAX_REQUEST_MICRO_USD,))
            connection.commit()
        finally:
            connection.close()

    def _request(self, operation, body):
        request = Request(API_ROOT + MODEL + ":" + operation,
                          data=json.dumps(body).encode(), method="POST",
                          headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            # Never reflect upstream bodies, request headers or the API key to the UI.
            code = error.code
            error.close()
            if code == 402:
                raise RuntimeError(
                    "Gemini returned HTTP 402 (Payment Required). Check Google AI Studio Billing "
                    "for the project linked to your API key and confirm a usable Gemini Prepay balance. "
                    "Promotional/Cloud credits may require a positive prepaid balance first. "
                    "No automatic retry was made; no credits were purchased."
                ) from None
            raise RuntimeError(f"Gemini returned HTTP {code}. No automatic retry was made.") from None
        except (URLError, TimeoutError):
            raise RuntimeError("Gemini connection failed. No automatic retry was made.") from None

    def _prompt(self, evidence_id):
        evidence = next((item for item in self.data["evidence"] if item["id"] == evidence_id), None)
        if evidence is None:
            raise ValueError("Unknown evidence identifier")
        return (
            "Explain the following audited evidence to a beginner casino manager in at most 180 words. "
            "This is a fictional casino with synthetic data. Use only the supplied figures. "
            "Do not invent numbers, causal effects, crimes, forecasts or recommendations. "
            "Distinguish actual win, expected win and contribution after supplied costs. "
            "Include the alternative explanation and limitation. Do not encourage targeting heavy losers. "
            "If evidence is insufficient, say so. Return plain text, citing the evidence ID.\n\n"
            + json.dumps(evidence, ensure_ascii=True)
        )

    def cached(self, evidence_id):
        prompt = self._prompt(evidence_id)
        digest = hashlib.sha256((MODEL + prompt).encode()).hexdigest()
        if not self.db_path.exists():
            return None
        with self._connection() as connection:
            cached = connection.execute("SELECT response, generated_at FROM cache WHERE digest=?", (digest,)).fetchone()
        if cached:
            return {"text": cached[0], "cached": True, "evidence_id": evidence_id,
                    "model": MODEL, "generated_at": cached[1]}
        return None

    def explain(self, evidence_id):
        cached = self.cached(evidence_id)
        if cached:
            return cached
        if not self.enabled:
            raise BudgetError("Gemini is disabled. Run python3 gemini_setup.py, then python3 serve.py --enable-gemini.")
        prompt = self._prompt(evidence_id)
        digest = hashlib.sha256((MODEL + prompt).encode()).hexdigest()
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        token_result = self.transport("countTokens", {"contents": contents})
        count = token_result.get("totalTokens")
        if not isinstance(count, int) or count < 0 or count > MAX_INPUT:
            raise BudgetError("Input exceeds the bounded request allowance; no generation was made.")
        self._reserve()  # Persist before generation, including failed/ambiguous attempts.
        result = self.transport("generateContent", {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": MAX_OUTPUT, "thinkingConfig": {"thinkingLevel": "minimal"}},
        })
        candidates = result.get("candidates", [])
        if not candidates or candidates[0].get("finishReason") != "STOP":
            raise RuntimeError("Gemini did not finish a complete explanation. Reserved allowance is retained; no retry was made.")
        text = "\n".join(part["text"] for part in candidates[0].get("content", {}).get("parts", [])
                         if part.get("text") and not part.get("thought"))
        if not text.strip():
            raise RuntimeError("Gemini returned no explanation. No retry was made.")
        generated_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            connection.execute("INSERT OR REPLACE INTO cache(digest,response,generated_at) VALUES (?,?,?)", (digest, text, generated_at))
        return {"text": text, "cached": False, "evidence_id": evidence_id,
                "model": MODEL, "generated_at": generated_at}
