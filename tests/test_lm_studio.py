import unittest

from panoptibot.copycat.lm_studio import build_lm_studio_payload


class LmStudioTest(unittest.TestCase):
    def test_payload_uses_openai_compatible_chat_contract(self) -> None:
        payload = build_lm_studio_payload(
            model="local-model",
            system_prompt="You are an away proxy.",
            user_prompt="Reply like Jack.",
            max_tokens=80,
            temperature=0.4,
        )

        self.assertEqual(payload["model"], "local-model")
        self.assertEqual(payload["max_tokens"], 80)
        self.assertEqual(payload["temperature"], 0.4)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")


if __name__ == "__main__":
    unittest.main()
