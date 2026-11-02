import unittest
from unittest.mock import patch

import requests

from core.assistant import Assistant


class AssistantTests(unittest.TestCase):
    def test_changing_model_clears_history(self):
        assistant = Assistant(model="model-a")
        assistant.history.extend([
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ])
        assistant.set_model("model-b")
        self.assertEqual(assistant.model, "model-b")
        self.assertEqual(assistant.history, [])

    def test_connection_error_has_actionable_message(self):
        assistant = Assistant()
        with patch("core.assistant.requests.post", side_effect=requests.exceptions.ConnectionError):
            output = "".join(assistant.ask("Проверка"))
        self.assertIn("localhost:11434", output)
        self.assertEqual(assistant.history, [])


if __name__ == "__main__":
    unittest.main()
