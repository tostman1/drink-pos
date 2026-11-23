import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_syntax import HTMLSources, check_js, check_python
from scripts.check_traceability import validate_test
from scripts.container_smoke import container_base
from scripts.standard_checks import test_environment


class StandardCheckTests(unittest.TestCase):
    def test_container_port_is_rediscovered_after_restart(self):
        with patch("scripts.container_smoke.docker", side_effect=["127.0.0.1:32768", "127.0.0.1:32769"]):
            self.assertEqual(container_base("owned-check"), "http://127.0.0.1:32768")
            self.assertEqual(container_base("owned-check"), "http://127.0.0.1:32769")

    def test_inline_scripts_modules_handlers_and_data_blocks(self):
        parser = HTMLSources()
        parser.feed("""<button onclick="return 1 &amp;&amp; 2">Book</button>
<script>const x = 1;</script><script type="module">export const x = 1;</script>
<script type="application/json">{"x":1}</script><script src="external.js"></script>""")
        self.assertEqual([kind for _, kind, _ in parser.scripts], ["", "module", "application/json"])
        self.assertIn("return 1 && 2", parser.handlers[0][1])
        with patch("scripts.check_syntax.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0)
            check_js("node", "export const x = 1;", True, "module")
            self.assertIn("--input-type=module", run.call_args.args[0])
            run.return_value = subprocess.CompletedProcess([], 1, stderr="bad syntax")
            with self.assertRaisesRegex(ValueError, "bad syntax"):
                check_js("node", "const = ;", False, "broken")
            run.side_effect = FileNotFoundError("missing node")
            with self.assertRaises(FileNotFoundError):
                check_js("missing", "", False, "missing")

    def test_invalid_python_fails_without_importing_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "source.py"
            path.write_text("raise RuntimeError('must not execute')", encoding="utf-8")
            check_python([path])
            self.assertFalse((root / "__pycache__").exists())
            path.write_text("def broken(:", encoding="utf-8")
            with self.assertRaises(SyntaxError):
                check_python([path])

    def test_environment_removes_production_and_service_configuration(self):
        with patch.dict(
            os.environ,
            {
                "DRINK_POS_DB": "production.db",
                "SMTP_PASSWORD": "secret",
                "SUMUP_API_KEY": "secret",
                "PAYMENT_PROVIDER": "sumup",
            },
        ):
            environment = test_environment(Path("disposable"))
        self.assertNotIn("SUMUP_API_KEY", environment)
        self.assertNotIn("SMTP_PASSWORD", environment)
        self.assertNotIn("PAYMENT_PROVIDER", environment)
        self.assertEqual(environment["DRINK_POS_ENV"], "development")
        self.assertNotEqual(environment["DRINK_POS_DB"], "production.db")

    def test_environment_removes_inherited_server_worker_configuration(self):
        with patch.dict(os.environ, {"UVICORN_WORKERS": "4", "WEB_CONCURRENCY": "4"}):
            environment = test_environment(Path("disposable"))
        self.assertNotIn("UVICORN_WORKERS", environment)
        self.assertNotIn("WEB_CONCURRENCY", environment)

    def test_traceability_rejects_nonexistent_test_method(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "test.py").write_text("class Sample:\n    def test_real(self): pass\n", encoding="utf-8")
            validate_test(root, "test.py::Sample.test_real")
            with self.assertRaisesRegex(ValueError, "Missing test method"):
                validate_test(root, "test.py::Sample.test_invented")
