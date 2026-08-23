import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def test_agent_and_mcp_manuals_are_present(self):
        required_docs = [
            ROOT / "docs" / "agent-api.md",
            ROOT / "docs" / "mcp.md",
            ROOT / "docs" / "ai-agent-manual.md",
            ROOT / "docs" / "todos.md",
        ]

        for path in required_docs:
            with self.subTest(path=path.name):
                self.assertTrue(path.exists(), f"{path} is missing")
                self.assertGreater(len(path.read_text(encoding="utf-8").strip()), 200)

    def test_mcp_status_is_not_overstated(self):
        mcp_text = (ROOT / "docs" / "mcp.md").read_text(encoding="utf-8").lower()
        ai_text = (ROOT / "docs" / "ai-agent-manual.md").read_text(encoding="utf-8").lower()

        self.assertIn("native mcp protocol server: not implemented", mcp_text)
        self.assertIn("/api/agent/book-drink", ai_text)
        self.assertIn("do not use", ai_text)

    def test_requested_todos_remain_visible(self):
        todo_text = (ROOT / "docs" / "todos.md").read_text(encoding="utf-8").lower()

        self.assertIn("ipad landscape", todo_text)
        self.assertIn("sse or websocket", todo_text)
        self.assertIn("native mcp server", todo_text)


if __name__ == "__main__":
    unittest.main()
