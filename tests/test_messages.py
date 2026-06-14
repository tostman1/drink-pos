import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"


class MessageCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_env = {
            key: os.environ.pop(key, None)
            for key in [
                "DRINK_POS_DB",
                "DRINK_POS_ENV",
                "DRINK_POS_MESSAGES",
                "DRINK_POS_PIN",
            ]
        }
        os.environ["DRINK_POS_ENV"] = "development"
        os.environ["DRINK_POS_DB"] = str(Path(self.temp_dir.name) / "drink_pos_test.db")
        os.environ["DRINK_POS_PIN"] = "1234"

        sys.modules.pop("main", None)
        sys.path.insert(0, str(APP_DIR))
        self.main = importlib.import_module("main")

    def tearDown(self):
        sys.modules.pop("main", None)
        try:
            sys.path.remove(str(APP_DIR))
        except ValueError:
            pass
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def test_init_db_creates_persistent_message_file(self):
        self.main.init_db()

        runtime_messages = Path(self.temp_dir.name) / "messages.json"
        self.assertTrue(runtime_messages.exists())
        data = json.loads(runtime_messages.read_text(encoding="utf-8"))
        self.assertEqual(data["card_visual_waiting_title"], "Warten auf Kartenterminal")
        self.assertIn("messages", self.main.messages())

    def test_runtime_message_file_overrides_defaults(self):
        self.main.init_db()
        runtime_messages = Path(self.temp_dir.name) / "messages.json"
        runtime_messages.write_text(
            json.dumps({"card_visual_waiting_title": "Terminal bitte anschauen"}, ensure_ascii=False),
            encoding="utf-8",
        )

        catalog = self.main.load_message_catalog()
        self.assertEqual(catalog["card_visual_waiting_title"], "Terminal bitte anschauen")
        self.assertIn("payment_status_paid", catalog)

    def test_message_text_formats_known_placeholders(self):
        self.main.init_db()

        text = self.main.message_text(
            "payment_status_created",
            "{payment_label} wird vorbereitet.",
            payment_label="Testzahlung",
        )

        self.assertEqual(text, "Testzahlung wird vorbereitet.")


if __name__ == "__main__":
    unittest.main()
