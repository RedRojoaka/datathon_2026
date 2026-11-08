"""Serve the static dashboard on localhost; Gemini is off unless explicitly enabled."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading

from gemini_guard import GeminiExplainer, BudgetError
from gemini_setup import load_key
from gemini_briefing import briefing_context, current_insights, export_insights

ROOT = Path(__file__).resolve().parent


class DashboardHandler(SimpleHTTPRequestHandler):
    explainer = None
    briefing_topics = []
    export_root = ROOT
    generation_lock = threading.Lock()

    def _json(self, value, status=200):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _local_request(self):
        host = self.headers.get("Host", "")
        valid_hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        return host in valid_hosts and (origin is None or origin == f"http://{host}")

    def do_GET(self):
        if self.path == "/api/briefing":
            if not self._local_request():
                return self._json({"error": "Local requests only"}, 403)
            return self._json({"topics": self.briefing_topics,
                               "insights": current_insights(self.explainer, self.briefing_topics),
                               "status": self.explainer.status(), "local_server": True})
        if self.path == "/api/status":
            if not self._local_request():
                return self._json({"error": "Local requests only"}, 403)
            return self._json(self.explainer.status())
        if self.path.startswith("/api/"):
            return self._json({"error": "Unknown API route"}, 404)
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/explain":
            return self._json({"error": "Unknown route"}, 404)
        if not self._local_request():
            return self._json({"error": "Local requests only"}, 403)
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 1024:
                return self._json({"error": "Small JSON request required"}, 400)
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or set(body) != {"evidence_id"}:
                return self._json({"error": "Supply one evidence_id"}, 400)
            if not self.generation_lock.acquire(blocking=False):
                return self._json({"error": "One explanation is already running. No new request was made."}, 429)
            try:
                result = self.explainer.explain(body["evidence_id"])
                if body["evidence_id"] in {t["id"] for t in self.briefing_topics}:
                    try:
                        result["export"] = export_insights(self.explainer, self.briefing_topics, root=self.export_root)
                    except OSError:
                        result["export_warning"] = "Explanation is safely cached; export files could not be updated. Run gemini_briefing.py --cached-only to retry without another generation."
                return self._json(result)
            finally:
                self.generation_lock.release()
        except BudgetError as error:
            return self._json({"error": str(error)}, 403)
        except (ValueError, json.JSONDecodeError):
            return self._json({"error": "Invalid explanation request"}, 400)
        except RuntimeError as error:
            return self._json({"error": str(error)}, 502)
        except Exception:
            return self._json({"error": "Explanation unavailable. Use the audited evidence text."}, 500)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--enable-gemini", action="store_true", help="Opt into paid Gemini requests; requires GEMINI_API_KEY")
    args = parser.parse_args()
    if not (ROOT / "dist/data.json").exists():
        parser.error("Run python3 build_analysis.py first")
    load_key()
    if args.enable_gemini and not os.environ.get("GEMINI_API_KEY"):
        parser.error("No Gemini key configured. Run python3 gemini_setup.py first. No API request was made.")
    data, topics = briefing_context(json.loads((ROOT / "dist/data.json").read_text()))
    DashboardHandler.briefing_topics = topics
    DashboardHandler.explainer = GeminiExplainer(data, ROOT / ".runtime/gemini.sqlite", enabled=args.enable_gemini)
    handler = partial(DashboardHandler, directory=str(ROOT / "dist"))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Dashboard: http://127.0.0.1:{args.port}", flush=True)
    print(f"Gemini Briefing: http://127.0.0.1:{args.port}/ai.html", flush=True)
    print("Gemini: " + ("enabled; persistent 500-attempt allowance" if DashboardHandler.explainer.enabled else "disabled; $0 in API calls"), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
