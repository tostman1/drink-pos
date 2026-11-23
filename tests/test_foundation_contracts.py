import json
import re
import unittest
from pathlib import Path

import yaml

from scripts.check_traceability import validate_catalog

ROOT = Path(__file__).resolve().parents[1]


def workflow(filename):
    # BaseLoader preserves YAML 'on' instead of YAML-1.1 bool conversion.
    return yaml.load((ROOT / ".github/workflows" / filename).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


class FoundationContractTests(unittest.TestCase):
    def test_catalog_links_resolve(self):
        count, external = validate_catalog()
        self.assertEqual((count, external), (23, 0))
        catalog = json.loads((ROOT / "docs/requirements.json").read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(req["id"] for req in catalog["requirements"]), [f"DP-{index:03}" for index in range(1, 24)]
        )

    def test_ci_cannot_publish_on_push_or_pull_request(self):
        container = workflow("container.yml")
        quality = workflow("ci.yml")
        self.assertEqual(container["permissions"], {"contents": "read"})
        self.assertEqual(quality["permissions"], {"contents": "read"})
        self.assertIn("push", container["on"])
        self.assertIn("pull_request", container["on"])
        self.assertNotIn("pull_request_target", container["on"])
        self.assertEqual(container["on"]["workflow_dispatch"]["inputs"]["publish"]["default"], "false")
        publish = container["jobs"]["publish"]
        self.assertIn("github.event_name == 'workflow_dispatch'", publish["if"])
        self.assertIn("inputs.publish == true", publish["if"])
        self.assertIn("github.ref == 'refs/heads/main'", publish["if"])
        self.assertEqual(publish["needs"], ["checks", "verify"])
        self.assertEqual(publish["environment"], "production-images")
        self.assertEqual(publish["permissions"]["packages"], "write")
        for name, job in container["jobs"].items():
            if name != "publish":
                self.assertEqual(job["permissions"], {"contents": "read"})
                text = json.dumps(job)
                self.assertNotIn("secrets.", text)
                self.assertNotIn("login-action", text)
                self.assertNotIn("docker push", text)
                self.assertNotIn('"push": "true"', text)
        self.assertEqual(container["jobs"]["checks"]["uses"], "./.github/workflows/ci.yml")
        verify_steps = json.dumps(container["jobs"]["verify"]["steps"])
        self.assertIn("scripts/container_smoke.py", verify_steps)
        self.assertIn("docker build", verify_steps)
        self.assertIn("config --quiet", verify_steps)
        for definition in (container, quality):
            for job in definition["jobs"].values():
                for step in job.get("steps", []):
                    if "uses" in step:
                        self.assertRegex(step["uses"], r"@[0-9a-f]{40}$")
                    self.assertNotIn("continue-on-error", step)

    def test_compose_mounts_only_data_not_application_code(self):
        for filename in ("compose.yaml", "compose.synology.yaml"):
            document = yaml.safe_load((ROOT / filename).read_text(encoding="utf-8"))
            for service in document["services"].values():
                self.assertEqual(service["volumes"], ["./data:/app/data"])

    def test_syntax_and_manual_procedures_remain_visible(self):
        text = (ROOT / "docs/standard-checks.md").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^### MV-\d{2} —", text, re.MULTILINE)), 6)
        self.assertIn("scripts/standard_checks.py", text)
        self.assertIn("Mocks are not delivery evidence", text)

    def test_authoritative_documents_exist_without_duplicate_old_paths(self):
        for filename in (
            "AGENTS.md",
            "REQUIREMENTS.md",
            "ARCHITECTURE.md",
            "IMPLEMENTATION_PLAN.md",
            "DECISIONS.md",
            "docs/PROCESS.md",
            "docs/PROGRESS.md",
            "docs/HANDOFF.md",
            "docs/AUDIT.md",
        ):
            self.assertTrue((ROOT / filename).is_file(), filename)
        for filename in (
            "PROCESS.md",
            "PROGRESS.md",
            "HANDOFF.md",
            "docs/architecture.md",
            "docs/requirements.md",
            "docs/work-packages.md",
        ):
            self.assertFalse((ROOT / filename).exists(), filename)
