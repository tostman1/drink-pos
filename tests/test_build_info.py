import os
import unittest

from app.core.build import build_commit, build_info, build_tags, image_ref_label, short_commit


class BuildInfoTests(unittest.TestCase):
    def setUp(self):
        self.original_env = {
            key: os.environ.pop(key, None)
            for key in [
                "APP_BUILD_COMMIT",
                "APP_BUILD_REF",
                "APP_BUILD_CHANNEL",
                "APP_BUILD_TAGS",
                "DRINK_POS_IMAGE_REF",
            ]
        }

    def tearDown(self):
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_build_commit_uses_safe_local_fallback(self):
        self.assertEqual(build_commit(), "local-dev")
        self.assertEqual(
            build_info(),
            {
                "commit": "local-dev",
                "short_commit": "local-dev",
                "ref": "",
                "channel": "",
                "tags": [],
                "runtime_image_ref": "",
                "runtime_image_label": "",
            },
        )

    def test_build_commit_reads_container_environment(self):
        os.environ["APP_BUILD_COMMIT"] = "abc123456789"
        os.environ["APP_BUILD_REF"] = "main"
        os.environ["APP_BUILD_CHANNEL"] = "stable"
        os.environ["APP_BUILD_TAGS"] = "stable, latest\nsha-abc1234"
        os.environ["DRINK_POS_IMAGE_REF"] = "ghcr.io/tostman1/drink-pos:stable"

        self.assertEqual(build_commit(), "abc123456789")
        self.assertEqual(short_commit(), "abc1234")
        self.assertEqual(build_tags(), ["stable", "latest", "sha-abc1234"])
        self.assertEqual(image_ref_label(os.environ["DRINK_POS_IMAGE_REF"]), "stable")
        self.assertEqual(
            build_info(),
            {
                "commit": "abc123456789",
                "short_commit": "abc1234",
                "ref": "main",
                "channel": "stable",
                "tags": ["stable", "latest", "sha-abc1234"],
                "runtime_image_ref": "ghcr.io/tostman1/drink-pos:stable",
                "runtime_image_label": "stable",
            },
        )


if __name__ == "__main__":
    unittest.main()
