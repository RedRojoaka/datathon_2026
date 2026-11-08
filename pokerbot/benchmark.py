"""Play reproducible HTTP matches with fresh servers for every half.

Run from the shared repository root:
  python pokerbot/benchmark.py --seeds 7 23 91 --deals 1000
No remote services, credentials, or paid APIs are used.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OPPONENTS = {name: HERE / "baseline-bots" / f"baseline_{name}.py" for name in
             ("random", "always_half", "always_pot", "calling_station")}
OPPONENTS.update({name: HERE / "practice_bot.py" for name in ("surprise", "selective", "equity")})


def source_hashes():
    paths = [ROOT / "agent.py", ROOT / "requirements.txt"]
    paths += [HERE / name for name in ("agent.py", "equity.py", "game.py",
                                       "evaluator.py", "requirements.txt")]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def server(path, port, log, mode=""):
    env = dict(os.environ, PORT=str(port), PRACTICE_MODE=mode,
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    env.pop("AGENT_TOKEN", None)
    with log.open("w") as handle:
        process = subprocess.Popen([sys.executable, str(path)], cwd=ROOT, env=env,
                                   stdout=handle, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"server failed: {log.read_text()}")
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.2)
                    conn.request("GET", "/")
                    response = conn.getresponse()
                    if response.status == 200:
                        response.read()
                        break
                except OSError:
                    time.sleep(0.05)
                finally:
                    if "conn" in locals():
                        conn.close()
            else:
                raise RuntimeError("server exceeded 15-second startup limit")
            yield
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", default=["7", "23", "91"])
    parser.add_argument("--opponents", nargs="+", choices=list(OPPONENTS), default=list(OPPONENTS))
    parser.add_argument("--deals", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=HERE / "results" / "validation")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(),
               "source_sha256": source_hashes(), "deals_per_half": args.deals,
               "fresh_process_each_half": True, "matches": []}
    for opponent in args.opponents:
        for seed in args.seeds:
            stem = f"{opponent}-seed{seed}"
            halves = []
            for half in (1, 2):
                one, two = free_port(), free_port()
                result = args.output / f"{stem}-half{half}.json"
                with server(ROOT / "agent.py", one, args.output / "agent.log"), \
                        server(OPPONENTS[opponent], two, args.output / "opponent.log", opponent):
                    run = subprocess.run(
                        [sys.executable, str(HERE / "judge_engine.py"), "--half", str(half),
                         "--agent1", str(one), "--agent2", str(two), "--seed", str(seed),
                         "--deals", str(args.deals), "--json", str(result)],
                        cwd=ROOT, capture_output=True, text=True, timeout=180)
                    if run.returncode:
                        raise RuntimeError(run.stdout + run.stderr)
                halves.append(result)
            combined = args.output / f"{stem}.json"
            run = subprocess.run([sys.executable, str(HERE / "judge_engine.py"), "combine",
                                  *(str(p) for p in halves), "--json", str(combined)],
                                 capture_output=True, text=True, check=True)
            (args.output / f"{stem}.txt").write_text(run.stdout)
            data = json.loads(combined.read_text())
            stats = data["agent_stats"]["agent1"]
            entry = {"opponent": opponent, "seed": str(seed), "result_file": combined.name,
                     "verdict": data["verdict"], "mean_bb": data["mean_bb_per_deal"], "ci": data["ci"],
                     "stats": stats}
            summary["matches"].append(entry)
            (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(f'{opponent:16} seed {seed}: {data["verdict"]} '
                  f'{data["mean_bb_per_deal"]:+.3f} bb/deal; '
                  f'bot seconds {[s["time_seconds"] for s in stats]}', flush=True)
            if any(s["errors"] or s["forfeited"] or s["timed_out"] for s in stats):
                raise RuntimeError(f"bot failed runtime validation: {combined}")
    print(f"Saved {len(summary['matches'])} matches to {args.output}")


if __name__ == "__main__":
    main()
