"""Read-only, bounded GitHub CI waiting; no model calls or resource mutations."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode

WORKFLOW = "container.yml"
REQUIRED_JOBS = (
    "checks / Python 3.12 / Node 24",
    "checks / Python 3.13 / Node 24",
    "Non-publishing container verification",
)
OPTIONAL_SKIPPED = {"Explicit owner-triggered main publication"}
EXIT_CODES = {
    "success": 0,
    "failed": 1,
    "cancelled": 2,
    "timed_out": 3,
    "rate_limited": 4,
    "unavailable": 5,
    "invalid_input": 6,
    "interrupted": 7,
}


class Stop(Exception):
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop("invalid_input", message)


def arguments(argv):
    parser = Parser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Explicit OWNER/REPO on github.com")
    parser.add_argument("--sha", required=True, help="Expected full 40-character HEAD SHA")
    parser.add_argument("--run-id", type=int)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--pr", type=int)
    target.add_argument("--branch", help="Exact push branch (also used to validate an explicit run)")
    parser.add_argument("--workflow", default=WORKFLOW)
    parser.add_argument(
        "--require-job", action="append", default=[], help="Additional required job; defaults remain mandatory"
    )
    parser.add_argument(
        "--require-check", action="append", default=[], help="Additional required PR check/status context"
    )
    parser.add_argument("--initial-delay", type=float, default=90)
    parser.add_argument("--discovery-delay", type=float, default=30)
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--long-interval", type=float, default=120)
    parser.add_argument("--long-after", type=float, default=600)
    parser.add_argument("--max-wait", type=float, default=1800)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-base", type=float, default=15)
    parser.add_argument("--request-timeout", type=float, default=30)
    parser.add_argument("--result-file", type=Path, help="New outside-Git JSON path; existing files are never reused")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        parser.error("--repo must be OWNER/REPO")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.sha):
        parser.error("--sha must be a full 40-character commit SHA")
    args.sha = args.sha.lower()
    if not (args.run_id or args.pr or args.branch):
        parser.error("identify --run-id, --pr or --branch")
    if any(value is not None and value <= 0 for value in (args.run_id, args.pr)):
        parser.error("run and PR IDs must be positive")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.ya?ml", args.workflow):
        parser.error("--workflow must be a workflow filename")
    for name in ("discovery_delay", "interval", "long_interval", "max_wait", "retry_base", "request_timeout"):
        value = getattr(args, name)
        if not 0 < value < float("inf"):
            parser.error(f"--{name.replace('_', '-')} must be positive and finite")
    for name in ("initial_delay", "long_after"):
        if not 0 <= getattr(args, name) < float("inf"):
            parser.error(f"--{name.replace('_', '-')} must be nonnegative and finite")
    if not 0 <= args.max_retries <= 3:
        parser.error("--max-retries must be 0..3")
    if args.require_check and not args.pr:
        parser.error("--require-check needs --pr")
    return args


def parse_response(text):
    # gh api --include emits status + headers + JSON, including on API errors.
    parts = text.replace("\r\n", "\n").split("\n\n", 1)
    if len(parts) != 2 or not re.match(r"HTTP/\S+ \d{3}", parts[0]):
        raise Stop("unavailable", "GitHub CLI response lacks HTTP headers")
    lines = parts[0].splitlines()
    status = int(lines[0].split()[1])
    headers = {
        key.strip().lower(): value.strip() for line in lines[1:] if ":" in line for key, value in [line.split(":", 1)]
    }
    try:
        body = json.loads(parts[1])
    except ValueError:
        if status < 400:
            raise Stop("unavailable", "GitHub returned malformed JSON") from None
        body = {}
    return status, headers, body


def retry_deadline(headers, now):
    deadlines = []
    retry = headers.get("retry-after")
    if retry:
        try:
            deadlines.append(now + max(0, float(retry)))
        except ValueError:
            try:
                deadlines.append(parsedate_to_datetime(retry).timestamp())
            except (ValueError, TypeError, OverflowError):
                pass
    if headers.get("x-ratelimit-remaining") == "0":
        try:
            deadlines.append(float(headers["x-ratelimit-reset"]) + 1)
        except (ValueError, KeyError):
            pass
    return max(deadlines, default=now)


class Monitor:
    def __init__(self, args, result):
        self.args = args
        self.result = result
        self.started = time.monotonic()
        self.deadline = self.started + args.max_wait
        self.not_before = 0
        self.run_id = args.run_id
        self.run_attempt = None
        self.jobs_verified = False
        self.prefix = f"repos/{args.repo}"

    def remaining(self):
        return self.deadline - time.monotonic()

    def wait(self, delay, status="timed_out"):
        remaining = self.remaining()
        if delay >= remaining:
            if status == "rate_limited":
                raise Stop(status, "permitted API retry is outside this waiting budget; resume at retry_at_epoch")
            if remaining > 0:
                time.sleep(remaining)
            raise Stop(status, "maximum waiting duration reached; no CI success established")
        if delay > 0:
            time.sleep(delay)

    def api(self, suffix, *, discover=False):
        for attempt in range(self.args.max_retries + 1):
            if self.not_before > time.time():
                self.result["retry_at_epoch"] = self.not_before
                self.wait(self.not_before - time.time(), "rate_limited")
            if self.remaining() <= 0:
                raise Stop("timed_out", "maximum waiting duration reached")
            try:
                response = subprocess.run(
                    [
                        "gh",
                        "api",
                        "--method",
                        "GET",
                        "--include",
                        "--hostname",
                        "github.com",
                        f"{self.prefix}/{suffix}",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=min(self.args.request_timeout, self.remaining()),
                    env={**os.environ, "GH_PROMPT_DISABLED": "1", "GH_PAGER": "cat", "GH_DEBUG": ""},
                )
            except FileNotFoundError:
                raise Stop("unavailable", "gh is not installed/on PATH") from None
            except (subprocess.TimeoutExpired, OSError):
                response = None
            headers, body = {}, {}
            if response is None or (response.returncode and not response.stdout.startswith("HTTP/")):
                status = 0  # network/CLI transport failure; never print raw auth-bearing stderr
            else:
                status, headers, body = parse_response(response.stdout)
            now = time.time()
            allowed = retry_deadline(headers, now)
            message = str(body.get("message", "")).lower() if isinstance(body, dict) else ""
            limited = status == 429 or (
                status == 403
                and (headers.get("x-ratelimit-remaining") == "0" or "retry-after" in headers or "rate limit" in message)
            )
            if limited:
                resource = headers.get("x-ratelimit-resource", "secondary-or-unspecified")
                self.result["rate_limit_resource"] = resource
                delay = max(allowed - now, 60 * 2**attempt)
                self.not_before = now + delay
                self.result["retry_at_epoch"] = self.not_before
                if attempt == self.args.max_retries:
                    raise Stop("rate_limited", "bounded API retries exhausted; resume at retry_at_epoch")
                self.wait(delay, "rate_limited")
                continue
            self.not_before = max(self.not_before, allowed)
            if 200 <= status < 300:
                if not isinstance(body, dict):
                    raise Stop("unavailable", "unexpected GitHub response shape")
                return body
            if status == 404 and discover:
                return None
            if status == 0 or status in (408, 500, 502, 503, 504):
                if attempt == self.args.max_retries:
                    raise Stop("unavailable", "bounded transient network/API retries exhausted")
                self.wait(max(self.args.retry_base * 2**attempt, allowed - now))
                continue
            raise Stop("unavailable", f"GitHub HTTP {status}; check authentication, permissions or target identity")
        raise Stop("unavailable", "no usable API result")

    def pages(self, suffix, key):
        records = []
        separator = "&" if "?" in suffix else "?"
        for page in range(1, 11):
            body = self.api(f"{suffix}{separator}per_page=100&page={page}")
            items = body.get(key)
            if not isinstance(items, list):
                raise Stop("unavailable", f"missing {key} list")
            records.extend(items)
            if len(items) < 100:
                if body.get("total_count", len(records)) > len(records):
                    raise Stop("unavailable", "incomplete paginated evidence")
                return records
        raise Stop("unavailable", "evidence exceeds bounded 1000-record pagination; targeted review needed")

    def pr_head(self):
        pr = self.api(f"pulls/{self.args.pr}")
        if pr.get("head", {}).get("sha") != self.args.sha:
            raise Stop(
                "unavailable", "PR HEAD changed or differs from expected SHA; approval/evidence must be refreshed"
            )
        self.result["pr_url"] = pr.get("html_url")

    def matches(self, run):
        expected_event = "pull_request" if self.args.pr else "push"
        if (
            run.get("head_sha") != self.args.sha
            or run.get("path") != f".github/workflows/{self.args.workflow}"
            or run.get("event") != expected_event
        ):
            return False
        if self.args.branch and run.get("head_branch") != self.args.branch:
            return False
        if self.args.pr:
            return any(
                pr.get("number") == self.args.pr and pr.get("head", {}).get("sha") == self.args.sha
                for pr in run.get("pull_requests", [])
            )
        return True

    def discover(self):
        params = {"head_sha": self.args.sha, "event": "pull_request" if self.args.pr else "push", "per_page": 100}
        if self.args.branch:
            params["branch"] = self.args.branch
        body = self.api(f"actions/workflows/{self.args.workflow}/runs?{urlencode(params)}", discover=True)
        if body is not None and not isinstance(body.get("workflow_runs"), list):
            raise Stop("unavailable", "discovery response lacks workflow_runs list")
        if body is not None and body.get("total_count", 0) > 100:
            raise Stop("unavailable", "discovery exceeds bounded exact-SHA candidate page; identify run explicitly")
        candidates = [run for run in (body or {}).get("workflow_runs", []) if self.matches(run)]
        if candidates:
            self.run_id = max(candidates, key=lambda run: int(run["id"]))["id"]

    def jobs(self, run):
        attempt = run.get("run_attempt")
        if not isinstance(attempt, int) or attempt < 1:
            raise Stop("unavailable", "missing run attempt identity")
        jobs = self.pages(f"actions/runs/{self.run_id}/attempts/{attempt}/jobs", "jobs")
        required = set(REQUIRED_JOBS) | set(self.args.require_job)
        names = {job.get("name") for job in jobs}
        if not required <= names:
            raise Stop("unavailable", "required workflow jobs missing: " + ", ".join(sorted(required - names)))
        for job in jobs:
            if job.get("conclusion") == "success":
                continue
            if (
                job.get("conclusion") == "skipped"
                and job.get("name") in OPTIONAL_SKIPPED
                and job.get("name") not in required
            ):
                continue
            raise Stop("unavailable", "job did not succeed: " + str(job.get("name")))
        self.result["checks"] = [{"name": job["name"], "conclusion": job["conclusion"]} for job in jobs]
        self.jobs_verified = True

    def pr_checks(self):
        checks = self.pages(f"commits/{self.args.sha}/check-runs?filter=latest", "check_runs")
        statuses = self.pages(f"commits/{self.args.sha}/status", "statuses")
        latest = {}
        for check in sorted(checks, key=lambda item: int(item["id"])):
            key = (check["name"], check.get("app", {}).get("id"))
            latest[key] = check
        contexts = {}
        for status in statuses:  # GitHub sorts commit statuses newest first
            contexts.setdefault(status["context"], status)
        names = {check["name"] for check in latest.values()} | contexts.keys()
        if not set(self.args.require_check) <= names:
            return False  # a required external check may not yet have appeared
        pending = False
        for check in latest.values():
            if check.get("head_sha") != self.args.sha:
                raise Stop("unavailable", "check belongs to another commit")
            if check.get("status") != "completed":
                pending = True
            elif check.get("conclusion") != "success" and not (
                check.get("name") in OPTIONAL_SKIPPED
                and check.get("conclusion") == "skipped"
                and check.get("name") not in self.args.require_check
            ):
                conclusion = check.get("conclusion")
                category = (
                    "cancelled" if conclusion == "cancelled" else "timed_out" if conclusion == "timed_out" else "failed"
                )
                raise Stop(category, "PR check did not succeed: " + check["name"])
        for name, status in contexts.items():
            if status.get("state") == "pending":
                pending = True
            elif status.get("state") != "success":
                raise Stop("failed", "PR status did not succeed: " + name)
        if checks or statuses:
            self.result["pr_checks"] = [
                {"name": check["name"], "status": check.get("status"), "conclusion": check.get("conclusion")}
                for check in latest.values()
            ] + [{"name": name, "status": status.get("state")} for name, status in contexts.items()]
        return bool(checks or statuses) and not pending

    def monitor(self):
        self.wait(self.args.initial_delay)
        if self.args.pr:
            self.pr_head()
        while True:
            if not self.run_id:
                self.discover()
                if not self.run_id:
                    self.wait(self.args.discovery_delay)
                    continue
            self.result["run_id"] = self.run_id
            self.result["run_url"] = f"https://github.com/{self.args.repo}/actions/runs/{self.run_id}"
            run = self.api(f"actions/runs/{self.run_id}", discover=True)
            if run is None:
                self.wait(self.args.discovery_delay)
                continue
            if not self.matches(run):
                raise Stop("unavailable", "run does not match expected SHA/workflow/event/branch/PR identity")
            if run.get("id") != self.run_id:
                raise Stop("unavailable", "returned run ID differs from pinned target")
            if self.run_attempt is not None and run.get("run_attempt") != self.run_attempt:
                raise Stop("unavailable", "run attempt changed; rerun requires new verification")
            self.run_attempt = run.get("run_attempt")
            self.result.update(
                workflow=run["path"], run_attempt=run.get("run_attempt"), conclusion=run.get("conclusion")
            )
            if run.get("status") == "completed":
                conclusion = run.get("conclusion")
                if conclusion != "success":
                    category = {
                        "failure": "failed",
                        "cancelled": "cancelled",
                        "timed_out": "timed_out",
                        "action_required": "failed",
                        "startup_failure": "failed",
                    }.get(conclusion, "unavailable")
                    raise Stop(category, "workflow conclusion: " + str(conclusion))
                if not self.jobs_verified:
                    self.jobs(run)
                if not self.args.pr or self.pr_checks():
                    if self.args.pr:
                        self.pr_head()  # close the HEAD-change race during final evidence retrieval
                    self.result["verified_sha"] = self.args.sha
                    return
            elif run.get("status") not in {"queued", "in_progress", "waiting", "requested", "pending"}:
                raise Stop("unavailable", "unknown workflow state")
            interval = (
                self.args.long_interval
                if time.monotonic() - self.started >= self.args.long_after
                else self.args.interval
            )
            self.wait(interval)


def atomic_result(path, result):
    # Only replace the file reserved by this process. Same-directory rename is atomic.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(result, stream, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main(argv=None):
    result = {"schema_version": 1, "pid": os.getpid(), "started_at_epoch": time.time()}
    reserved = None
    try:
        args = arguments(argv)
        result.update(repo=args.repo, expected_sha=args.sha, pr=args.pr, run_id=args.run_id)
        if args.result_file:
            if args.result_file.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
                raise Stop("invalid_input", "result file must be outside this repository")
            # O_EXCL protects another monitor's result and detects accidental path reuse.
            with args.result_file.open("x", encoding="utf-8") as stream:
                json.dump({**result, "status": "pending", "max_wait_seconds": args.max_wait}, stream)
            reserved = args.result_file
        Monitor(args, result).monitor()
        result.update(
            status="success", reason="exact-head workflow and required evidence succeeded; not merge authorization"
        )
    except Stop as exc:
        result.update(status=exc.status, reason=exc.reason)
    except KeyboardInterrupt:
        result.update(status="interrupted", reason="monitor interrupted; GitHub resources were not changed")
    except FileExistsError:
        result.update(status="invalid_input", reason="result file already exists; use a new operation path")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result.update(
            status="unavailable",
            reason=f"local output or evidence error ({type(exc).__name__}); no success established",
        )
    result.update(exit_code=EXIT_CODES[result["status"]], finished_at_epoch=time.time())
    if reserved:
        try:
            atomic_result(reserved, result)
        except OSError:
            result.update(
                status="unavailable", exit_code=5, reason="cannot persist terminal result; stdout is authoritative"
            )
    print(json.dumps(result, separators=(",", ":")), flush=True)
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
