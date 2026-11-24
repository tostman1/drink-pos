"""EF-03 / DP-018, DP-019: deterministic read-only CI orchestration."""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
REQUIRED = ["checks / Python 3.12 / Node 24", "checks / Python 3.13 / Node 24", "Non-publishing container verification"]


def load_helper():
    spec = importlib.util.spec_from_file_location("ci_wait", ROOT / "scripts/wait_for_ci.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def response(body=None, status=200, headers=None):
    lines = [f"HTTP/2.0 {status}"] + [f"{key}: {value}" for key, value in (headers or {}).items()]
    text = "\r\n".join(lines) + "\r\n\r\n" + json.dumps(body or {})
    return subprocess.CompletedProcess([], 0 if status == 200 else 1, text, "")


def run_record(conclusion="success", status="completed", **changes):
    record = dict(
        id=42,
        head_sha=SHA,
        head_branch="feature/example",
        event="push",
        path=".github/workflows/container.yml",
        run_attempt=1,
        status=status,
        conclusion=conclusion,
        html_url="https://github.com/owner/repo/actions/runs/42",
        pull_requests=[{"number": 7, "head": {"sha": SHA}}],
    )
    record.update(changes)
    return record


def jobs():
    return {
        "total_count": 4,
        "jobs": [{"name": name, "conclusion": "success"} for name in REQUIRED]
        + [{"name": "Explicit owner-triggered main publication", "conclusion": "skipped"}],
    }


def check_record(name="Security", conclusion="success", status="completed", **changes):
    record = {"id": 100, "name": name, "head_sha": SHA, "status": status, "conclusion": conclusion, "app": {"id": 1}}
    record.update(changes)
    return record


def pr_evidence(*checks):
    return [response({"check_runs": list(checks or [check_record()])}), response({"statuses": []})]


class Clock:
    def __init__(self):
        self.value = 0
        self.sleeps = []

    def now(self):
        return self.value

    def sleep(self, delay):
        self.sleeps.append(delay)
        self.value += delay


class CIWaitTests(unittest.TestCase):
    def invoke(self, replies, *arguments, initial=0, maximum=300):
        helper = load_helper()
        clock = Clock()
        calls = []
        queue = list(replies)

        def command(args, **kwargs):
            calls.append((args, kwargs))
            self.assertEqual(args[1:4], ["api", "--method", "GET"])
            self.assertIn("--include", args)
            self.assertGreater(kwargs["timeout"], 0)
            item = queue.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item

        argv = ["--repo", "owner/repo", "--sha", SHA, "--initial-delay", str(initial), "--max-wait", str(maximum)]
        if not any(option in arguments for option in ("--pr", "--branch", "--run-id")):
            argv += ["--run-id", "42"]
        argv += list(arguments)
        output = io.StringIO()
        with (
            patch.object(helper.subprocess, "run", side_effect=command),
            patch.object(helper.time, "monotonic", clock.now),
            patch.object(helper.time, "time", lambda: 1000 + clock.value),
            patch.object(helper.time, "sleep", clock.sleep),
            contextlib.redirect_stdout(output),
        ):
            code = helper.main(argv)
        result = json.loads(output.getvalue())
        self.assertEqual(code, result["exit_code"])
        self.assertEqual(len(output.getvalue().splitlines()), 1)
        return result, clock, calls

    def test_success_is_exact_head_read_only_with_required_jobs(self):
        result, clock, calls = self.invoke([response(run_record()), response(jobs())], initial=90)
        self.assertEqual((result["status"], result["exit_code"], result["verified_sha"]), ("success", 0, SHA))
        self.assertEqual(clock.sleeps, [90])
        self.assertEqual(len(calls), 2)
        self.assertIn("/attempts/1/jobs", calls[-1][0][-1])

    def test_terminal_results_are_distinct(self):
        for conclusion, status, code in [
            ("failure", "failed", 1),
            ("cancelled", "cancelled", 2),
            ("timed_out", "timed_out", 3),
            ("skipped", "unavailable", 5),
        ]:
            with self.subTest(conclusion=conclusion):
                result, _, _ = self.invoke([response(run_record(conclusion))])
                self.assertEqual((result["status"], result["exit_code"]), (status, code))

    def test_pending_waits_internally_then_succeeds(self):
        result, clock, calls = self.invoke(
            [response(run_record(None, "in_progress")), response(run_record()), response(jobs())]
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(clock.sleeps, [60])
        self.assertEqual(len(calls), 3)

    def test_pending_timeout_is_never_success(self):
        result, clock, calls = self.invoke([response(run_record(None, "queued"))], maximum=35)
        self.assertEqual((result["status"], result["exit_code"]), ("timed_out", 3))
        self.assertEqual(clock.sleeps, [35])
        self.assertEqual(len(calls), 1)

    def test_stale_sha_workflow_branch_or_event_fail_closed(self):
        for changes in (
            {"head_sha": "b" * 40},
            {"path": ".github/workflows/unrelated.yml"},
            {"head_branch": "other"},
            {"event": "workflow_dispatch"},
        ):
            with self.subTest(changes=changes):
                result, _, calls = self.invoke(
                    [response(run_record(**changes))], "--branch", "feature/example", "--run-id", "42"
                )
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(len(calls), 1)

    def test_missing_or_skipped_required_job_and_unknown_skipped_job_are_not_passes(self):
        for altered in (
            jobs()["jobs"][1:],
            [{"name": REQUIRED[0], "conclusion": "skipped"}] + jobs()["jobs"][1:],
            jobs()["jobs"] + [{"name": "Security", "conclusion": "skipped"}],
        ):
            with self.subTest(altered=altered):
                result, _, _ = self.invoke(
                    [response(run_record()), response({"total_count": len(altered), "jobs": altered})]
                )
                self.assertNotEqual(result["exit_code"], 0)

    def test_pr_discovery_and_final_head_guard(self):
        pr = {"head": {"sha": SHA}, "html_url": "https://github.com/owner/repo/pull/7"}
        record = run_record(event="pull_request")
        result, _, calls = self.invoke(
            [
                response(pr),
                response({"workflow_runs": [record], "total_count": 1}),
                response(record),
                response(jobs()),
                *pr_evidence(),
                response(pr),
            ],
            "--pr",
            "7",
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["pr"], 7)
        self.assertEqual(len(calls), 7)

    def test_changed_pr_head_does_not_accept_success(self):
        pr = {"head": {"sha": SHA}}
        record = run_record(event="pull_request")
        replies = [
            response(pr),
            response({"workflow_runs": [record]}),
            response(record),
            response(jobs()),
            *pr_evidence(),
            response({"head": {"sha": "b" * 40}}),
        ]
        result, _, _ = self.invoke(replies, "--pr", "7")
        self.assertEqual(result["status"], "unavailable")

    def test_discovery_uses_30_seconds_and_never_chooses_unrelated_or_older_run(self):
        record = run_record(id=43)
        unrelated = run_record(id=44, head_sha="b" * 40)
        result, clock, _ = self.invoke(
            [
                response({"workflow_runs": []}),
                response({"workflow_runs": [unrelated, record]}),
                response(record),
                response(jobs()),
            ],
            "--branch",
            "feature/example",
        )
        self.assertEqual(result["run_id"], 43)
        self.assertEqual(clock.sleeps, [30])

    def test_pr_never_chooses_push_run_or_another_pr(self):
        result, _, _ = self.invoke(
            [
                response({"head": {"sha": SHA}}),
                response({"workflow_runs": [run_record()]}),
                response({"workflow_runs": []}),
            ],
            "--pr",
            "7",
            maximum=31,
        )
        self.assertEqual(result["status"], "timed_out")

    def test_rate_limit_headers_wait_without_reset_probes(self):
        headers = {
            "Retry-After": "120",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1180",
            "X-RateLimit-Resource": "core",
        }
        result, clock, calls = self.invoke(
            [response(status=403, headers=headers), response(run_record()), response(jobs())]
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(clock.sleeps, [181])
        self.assertEqual(len(calls), 3)

    def test_impractical_rate_limit_returns_checkpoint_not_timeout_or_success(self):
        result, clock, calls = self.invoke([response(status=429, headers={"Retry-After": "900"})])
        self.assertEqual((result["status"], result["exit_code"]), ("rate_limited", 4))
        self.assertEqual(result["retry_at_epoch"], 1900)
        self.assertEqual(clock.sleeps, [])
        self.assertEqual(len(calls), 1)

    def test_secondary_limit_has_minimum_backoff_and_bounded_retries(self):
        replies = [response({"message": "secondary rate limit"}, 403)] * 4
        result, clock, calls = self.invoke(replies, maximum=1000)
        self.assertEqual(result["status"], "rate_limited")
        self.assertEqual(clock.sleeps, [60, 120, 240])
        self.assertEqual(len(calls), 4)

    def test_transient_network_failures_back_off_and_are_bounded(self):
        result, clock, calls = self.invoke([response(status=502)] * 4)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(clock.sleeps, [15, 30, 60])
        self.assertEqual(len(calls), 4)

    def test_missing_cli_auth_and_malformed_response_are_unavailable(self):
        for reply in (
            FileNotFoundError(),
            response(status=401),
            response(status=403),
            subprocess.CompletedProcess([], 0, "invalid json", ""),
        ):
            with self.subTest(reply=reply):
                result, _, calls = self.invoke([reply])
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(len(calls), 1)

    def test_success_with_exhausted_quota_delays_next_request(self):
        headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1060"}
        result, clock, _ = self.invoke([response(run_record(), headers=headers), response(jobs())])
        self.assertEqual(result["status"], "success")
        self.assertEqual(clock.sleeps, [61])

    def test_long_running_interval_is_120_seconds(self):
        replies = [response(run_record(None, "in_progress"))] * 11 + [response(run_record()), response(jobs())]
        result, clock, _ = self.invoke(replies, maximum=1000)
        self.assertEqual(result["status"], "success")
        self.assertEqual(clock.sleeps, [60] * 10 + [120])

    def test_result_file_is_atomic_compact_and_existing_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            result, _, _ = self.invoke([response(run_record()), response(jobs())], "--result-file", str(path))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), result)
            before = path.read_bytes()
            result, _, calls = self.invoke([], "--result-file", str(path))
            self.assertEqual(result["exit_code"], 6)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(calls, [])

    def test_cli_invalid_sha_exits_without_any_github_request(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/wait_for_ci.py"),
                "--repo",
                "owner/repo",
                "--sha",
                "short",
                "--run-id",
                "42",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 6)
        self.assertEqual(json.loads(completed.stdout)["status"], "invalid_input")

    def test_pr_external_checks_and_statuses_are_not_ignored(self):
        for check, status, expected in (
            (check_record(conclusion="failure"), [], "failed"),
            (check_record(conclusion="cancelled"), [], "cancelled"),
            (check_record(conclusion="timed_out"), [], "timed_out"),
            (check_record(conclusion="neutral"), [], "failed"),
            (check_record(head_sha="b" * 40), [], "unavailable"),
            (check_record(), [{"context": "required-status", "state": "failure"}], "failed"),
        ):
            with self.subTest(check=check, status=status):
                replies = [
                    response({"head": {"sha": SHA}}),
                    response(run_record(event="pull_request")),
                    response(jobs()),
                    response({"check_runs": [check]}),
                    response({"statuses": status}),
                ]
                result, _, _ = self.invoke(replies, "--pr", "7", "--run-id", "42")
                self.assertEqual(result["status"], expected)

    def test_pr_pending_external_check_waits_and_jobs_are_not_redownloaded(self):
        record = run_record(event="pull_request")
        replies = [
            response({"head": {"sha": SHA}}),
            response(record),
            response(jobs()),
            *pr_evidence(check_record(conclusion=None, status="in_progress")),
            response(record),
            *pr_evidence(),
            response({"head": {"sha": SHA}}),
        ]
        result, clock, calls = self.invoke(replies, "--pr", "7", "--run-id", "42", "--require-check", "Security")
        self.assertEqual(result["status"], "success")
        self.assertEqual(clock.sleeps, [60])
        self.assertEqual(sum("/jobs" in args[-1] for args, _ in calls), 1)

    def test_missing_required_pr_context_waits_not_passes(self):
        replies = [
            response({"head": {"sha": SHA}}),
            response(run_record(event="pull_request")),
            response(jobs()),
            *pr_evidence(),
        ]
        result, _, _ = self.invoke(replies, "--pr", "7", "--run-id", "42", "--require-check", "Absent", maximum=30)
        self.assertEqual(result["status"], "timed_out")

    def test_changed_attempt_is_not_silently_accepted(self):
        replies = [response(run_record(None, "in_progress")), response(run_record(run_attempt=2))]
        result, _, _ = self.invoke(replies)
        self.assertEqual(result["status"], "unavailable")

    def test_http_date_retry_after_and_transient_retry_header(self):
        headers = {"Retry-After": "Thu, 01 Jan 1970 00:19:00 GMT"}
        result, clock, _ = self.invoke(
            [response(status=503, headers=headers), response(run_record()), response(jobs())]
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(clock.sleeps, [140])

    def test_request_timeout_and_interruption_do_not_pass(self):
        replies = [subprocess.TimeoutExpired("gh", 30)] * 4
        result, _, _ = self.invoke(replies)
        self.assertEqual(result["status"], "unavailable")
        result, _, _ = self.invoke([KeyboardInterrupt()])
        self.assertEqual((result["status"], result["exit_code"]), ("interrupted", 7))

    def test_pagination_cannot_hide_failed_jobs(self):
        first = jobs()["jobs"] + [{"name": f"Extra {n}", "conclusion": "success"} for n in range(96)]
        replies = [
            response(run_record()),
            response({"total_count": 101, "jobs": first}),
            response({"total_count": 101, "jobs": [{"name": "Extra failing", "conclusion": "failure"}]}),
        ]
        result, _, calls = self.invoke(replies)
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("page=2", calls[-1][0][-1])

    def test_no_status_output_or_api_calls_during_initial_delay(self):
        result, clock, calls = self.invoke([], initial=90, maximum=30)
        self.assertEqual(result["status"], "timed_out")
        self.assertEqual(clock.sleeps, [30])
        self.assertEqual(calls, [])

    def test_repository_result_path_is_rejected_before_requests(self):
        result, _, calls = self.invoke([], "--result-file", str(ROOT / "ci-result.json"))
        self.assertEqual(result["status"], "invalid_input")
        self.assertEqual(calls, [])

    def test_bad_or_excessive_discovery_is_unavailable(self):
        for body in ({"unexpected": []}, {"workflow_runs": [run_record()], "total_count": 101}):
            with self.subTest(body=body):
                result, _, calls = self.invoke([response(body)], "--branch", "feature/example")
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(len(calls), 1)

    def test_same_sha_other_pr_and_returned_run_id_are_rejected(self):
        record = run_record(event="pull_request", pull_requests=[{"number": 8, "head": {"sha": SHA}}])
        result, _, _ = self.invoke([response({"head": {"sha": SHA}}), response(record)], "--pr", "7", "--run-id", "42")
        self.assertEqual(result["status"], "unavailable")
        result, _, _ = self.invoke([response(run_record(id=43))])
        self.assertEqual(result["status"], "unavailable")

    def test_latest_pr_status_and_check_evidence_not_old_failures(self):
        record = run_record(event="pull_request")
        checks = [check_record(id=99, conclusion="failure"), check_record()]
        statuses = [{"context": "lint", "state": "success"}, {"context": "lint", "state": "failure"}]
        replies = [
            response({"head": {"sha": SHA}}),
            response(record),
            response(jobs()),
            response({"check_runs": checks}),
            response({"statuses": statuses}),
            response({"head": {"sha": SHA}}),
        ]
        result, _, _ = self.invoke(replies, "--pr", "7", "--run-id", "42")
        self.assertEqual(result["status"], "success")

    def test_result_persistence_failure_returns_nonzero(self):
        helper = load_helper()
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(helper, "atomic_result", side_effect=OSError),
            patch.object(helper.Monitor, "monitor", return_value=None),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            code = helper.main(
                [
                    "--repo",
                    "owner/repo",
                    "--sha",
                    SHA,
                    "--run-id",
                    "42",
                    "--result-file",
                    str(Path(temporary) / "result.json"),
                ]
            )
        self.assertEqual(code, 5)
        self.assertEqual(json.loads(output.getvalue())["status"], "unavailable")

    def test_policy_is_discoverable_and_preserves_integration_gates(self):
        agent = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        process = (ROOT / "docs/PROCESS.md").read_text(encoding="utf-8")
        self.assertIn("Waiting is not reasoning", agent)
        self.assertIn("scripts/wait_for_ci.py", agent)
        for required in ("Retry-After", "LLM provider token", "post-merge", "exact", "checkpoint", "approval"):
            self.assertIn(required, process)


if __name__ == "__main__":
    unittest.main()
