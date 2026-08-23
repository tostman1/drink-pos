import os
import unittest

from app.core.build import build_commit, build_info


class BuildInfoTests(unittest.TestCase):
    def setUp(self):
        self.original_build_commit = os.environ.pop("APP_BUILD_COMMIT", None)

    def tearDown(self):
        if self.original_build_commit is None:
            os.environ.pop("APP_BUILD_COMMIT", None)
        else:
            os.environ["APP_BUILD_COMMIT"] = self.original_build_commit

    def test_build_commit_uses_safe_local_fallback(self):
        self.assertEqual(build_commit(), "local-dev")
        self.assertEqual(build_info(), {"commit": "local-dev"})

    def test_build_commit_reads_container_environment(self):
        os.environ["APP_BUILD_COMMIT"] = "abc123"

        self.assertEqual(build_commit(), "abc123")
        self.assertEqual(build_info(), {"commit": "abc123"})


if __name__ == "__main__":
    unittest.main()
