"""Launch a workflow run through the dashboard's /run-agent/start endpoint.

Using the dashboard's own start endpoint (rather than run_workflow.py directly)
means the run is a managed dashboard run: it shows up in the runs list with
working Stop/Resume buttons, and human-in-the-loop prompts surface in the web UI.

The dashboard must already be running (see scripts/run_dashboard.sh).

Example:
    uv run python scripts/launch_run.py \
        --workflow attention_harness_gpt_critic \
        --problem-id GRH.txt \
        --input base_model=sonnet --input key_model=opus \
        --input critic_model=gpt-5.4-mini

Prints the run id and the dashboard URL to open. The dashboard derives the
run's display name from the preset and problem.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workflow", required=True, help="Preset name (e.g. attention_harness_gpt_critic).")
    p.add_argument("--problem-id", required=True, help="Filename of a problem in problems/ (e.g. GRH.txt).")
    p.add_argument("--input", action="append", default=[], help="Workflow input override KEY=VALUE. Repeatable.")
    p.add_argument("--port", type=int, default=5005, help="Dashboard port (default 5005).")
    p.add_argument("--max-parallel", type=int, default=1)
    args = p.parse_args()

    inputs: dict[str, str] = {}
    for raw in args.input:
        if "=" not in raw:
            print(f"invalid --input (expected KEY=VALUE): {raw!r}", file=sys.stderr)
            return 2
        key, value = raw.split("=", 1)
        inputs[key.strip()] = value.strip()

    payload = {
        "preset": args.workflow,
        "problems": [args.problem_id],
        "inputs": inputs,
        "max_parallel": args.max_parallel,
    }

    url = f"http://127.0.0.1:{args.port}/run-agent/start"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
            errs = "; ".join(body.get("errors") or [str(e)])
        except Exception:
            errs = str(e)
        print(f"launch failed: {errs}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"could not reach dashboard at {url}: {e.reason}. Is it running "
              f"(scripts/run_dashboard.sh {args.port})?", file=sys.stderr)
        return 1

    if not body.get("ok"):
        print(f"launch failed: {'; '.join(body.get('errors') or ['unknown error'])}", file=sys.stderr)
        return 1

    run_id = body["run_id"]
    run_url = f"http://localhost:{args.port}/run/{run_id}"
    print(run_id)
    print(run_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
