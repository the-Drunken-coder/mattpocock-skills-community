import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import monitor_sync
from scripts.monitor_sync import evaluate_health

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)


def run(
    age_minutes: int,
    *,
    conclusion: str = "success",
    branch: str = "main",
    event: str = "schedule",
    status: str = "completed",
) -> dict[str, object]:
    """Create an Actions run fixture at a controlled age."""
    return {
        "status": status,
        "conclusion": conclusion,
        "event": event,
        "head_branch": branch,
        "updated_at": (NOW - timedelta(minutes=age_minutes)).isoformat(),
        "html_url": f"https://github.com/example/repo/actions/runs/{age_minutes}",
    }


class SyncHealthTests(unittest.TestCase):
    def test_recent_success_is_healthy(self) -> None:
        report = evaluate_health([run(10)], branch="main", now=NOW)
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["reasons"], [])

    def test_latest_failure_is_unhealthy_even_with_a_recent_success(self) -> None:
        report = evaluate_health(
            [run(20), run(5, conclusion="failure")], branch="main", now=NOW
        )
        self.assertEqual(report["status"], "failure")
        self.assertEqual(report["latest_completed_conclusion"], "failure")
        self.assertEqual(report["last_success_url"], run(20)["html_url"])

    def test_stale_success_is_unhealthy(self) -> None:
        report = evaluate_health([run(121)], branch="main", now=NOW)
        self.assertEqual(report["status"], "failure")
        self.assertIn("older than 2 hours", report["reasons"][0])

    def test_missing_success_is_unhealthy(self) -> None:
        report = evaluate_health([], branch="main", now=NOW)
        self.assertEqual(report["status"], "failure")
        self.assertIsNone(report["last_success_at"])

    def test_other_branches_and_events_do_not_count_as_heartbeat(self) -> None:
        report = evaluate_health(
            [run(5, branch="feature"), run(5, event="pull_request"), run(130)],
            branch="main",
            now=NOW,
        )
        self.assertEqual(report["status"], "failure")

    def test_in_progress_run_does_not_reset_freshness(self) -> None:
        report = evaluate_health(
            [run(0, status="in_progress"), run(130)], branch="main", now=NOW
        )
        self.assertEqual(report["status"], "failure")

    def test_success_after_failure_recovers_health(self) -> None:
        report = evaluate_health(
            [run(30, conclusion="failure"), run(5, event="workflow_dispatch")],
            branch="main",
            now=NOW,
        )
        self.assertEqual(report["status"], "success")

    def test_disabled_workflow_fails_and_writes_a_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "health.json"
            with (
                patch.object(
                    monitor_sync,
                    "github_json",
                    side_effect=[
                        {"state": "disabled_manually"},
                        {"workflow_runs": [run(5)]},
                    ],
                ),
                patch(
                    "sys.argv",
                    [
                        "monitor_sync.py",
                        "--repository",
                        "example/repo",
                        "--branch",
                        "main",
                        "--report",
                        str(report_path),
                    ],
                ),
                patch("sys.stdout", new=io.StringIO()),
                patch("sys.stderr", new=io.StringIO()),
                self.assertRaises(SystemExit) as error,
            ):
                monitor_sync.main()
            self.assertEqual(error.exception.code, 1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failure")
            self.assertTrue(
                any("disabled_manually" in reason for reason in report["reasons"])
            )

    def test_api_errors_are_reported_as_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "health.json"
            with (
                patch.object(
                    monitor_sync, "github_json", side_effect=OSError("API unavailable")
                ),
                patch(
                    "sys.argv",
                    [
                        "monitor_sync.py",
                        "--repository",
                        "example/repo",
                        "--branch",
                        "main",
                        "--report",
                        str(report_path),
                    ],
                ),
                patch("sys.stdout", new=io.StringIO()),
                patch("sys.stderr", new=io.StringIO()),
                self.assertRaises(SystemExit) as error,
            ):
                monitor_sync.main()
            self.assertEqual(error.exception.code, 1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failure")
            self.assertIn("API unavailable", report["reasons"][0])


if __name__ == "__main__":
    unittest.main()
