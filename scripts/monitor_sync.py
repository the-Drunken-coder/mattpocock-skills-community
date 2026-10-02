"""Check sync failures and freshness using the repository's Actions history."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode


def evaluate_health(
    runs: list[dict[str, object]],
    *,
    branch: str,
    now: datetime,
    max_age: timedelta = timedelta(hours=2),
) -> dict[str, object]:
    completed = [
        run
        for run in runs
        if run.get("status") == "completed"
        and run.get("event") in ("schedule", "workflow_dispatch")
        and run.get("head_branch") == branch
    ]
    completed.sort(key=lambda run: str(run["updated_at"]), reverse=True)
    latest = completed[0] if completed else None
    successful = next(
        (run for run in completed if run.get("conclusion") == "success"), None
    )
    reasons = []
    if latest and latest.get("conclusion") != "success":
        reasons.append(f"Latest completed sync concluded {latest.get('conclusion')}.")
    last_success_at = successful["updated_at"] if successful else None
    if last_success_at is None:
        reasons.append("No successful sync found on the default branch.")
    else:
        completed_at = datetime.fromisoformat(
            str(last_success_at).replace("Z", "+00:00")
        )
        if now - completed_at > max_age:
            reasons.append(
                f"Last successful sync is older than {max_age.total_seconds() / 3600:g} hours."
            )
    return {
        "status": "failure" if reasons else "success",
        "checked_at": now.isoformat(),
        "branch": branch,
        "max_age_hours": max_age.total_seconds() / 3600,
        "reasons": reasons,
        "last_success_at": last_success_at,
        "last_success_url": successful.get("html_url") if successful else None,
        "latest_completed_url": latest.get("html_url") if latest else None,
        "latest_completed_conclusion": latest.get("conclusion") if latest else None,
    }


def github_json(endpoint: str) -> dict[str, object]:
    result = subprocess.run(
        ["gh", "api", endpoint], check=True, capture_output=True, text=True, timeout=60
    )
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--branch", required=True)
    parser.add_argument("--max-age-hours", type=float, default=2)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not args.repository:
        parser.error("--repository or GITHUB_REPOSITORY is required")
    if args.max_age_hours <= 0:
        parser.error("--max-age-hours must be positive")
    try:
        endpoint = f"repos/{args.repository}/actions/workflows/sync-upstream.yml"
        workflow = github_json(endpoint)
        query = urlencode({"branch": args.branch, "per_page": 100})
        history = github_json(f"{endpoint}/runs?{query}")
        report = evaluate_health(
            history["workflow_runs"],
            branch=args.branch,
            now=datetime.now(timezone.utc),
            max_age=timedelta(hours=args.max_age_hours),
        )
        if workflow.get("state") != "active":
            report["status"] = "failure"
            report["reasons"].append(
                f"Sync workflow is {workflow.get('state', 'unknown')}."
            )
    except (
        subprocess.SubprocessError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        report = {
            "status": "failure",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "reasons": [f"Unable to check sync health: {error}"],
        }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = ["## Upstream sync health", "", f"Status: **{report['status']}**", ""]
        lines.extend(f"- {reason}" for reason in report["reasons"])
        if report.get("last_success_url"):
            lines.append(
                f"- [Last successful sync]({report['last_success_url']}) at {report['last_success_at']}"
            )
        if report.get("latest_completed_url"):
            lines.append(f"- [Latest completed sync]({report['latest_completed_url']})")
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")
    print(json.dumps(report, indent=2))
    if report["status"] != "success":
        print("Upstream sync health check failed.", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
