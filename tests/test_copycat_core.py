from datetime import UTC, datetime, timedelta
import unittest

from panoptibot.copycat.core import (
    CopycatProfile,
    CopycatSession,
    build_labeled_reply,
    is_allowed_copycat_text,
    should_trigger_copycat,
)


class CopycatCoreTest(unittest.TestCase):
    def test_trigger_requires_active_session_owner_mention_and_allowlisted_channel(self) -> None:
        now = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)
        session = CopycatSession(
            owner_user_id="123",
            display_name="Jack",
            expires_at=now + timedelta(minutes=30),
            allowlisted_channel_ids=frozenset({"456"}),
        )

        self.assertTrue(
            should_trigger_copycat(
                session=session,
                mentioned_user_ids={"123"},
                channel_id="456",
                now=now,
            )
        )
        self.assertFalse(
            should_trigger_copycat(
                session=session,
                mentioned_user_ids={"123"},
                channel_id="999",
                now=now,
            )
        )

    def test_labeled_reply_keeps_bot_attribution_outside_model_text(self) -> None:
        profile = CopycatProfile(user_id="123", display_name="Jack")

        reply = build_labeled_reply(profile, "haha we aint doin tht bruv")

        self.assertEqual(
            reply,
            '@Jack is away, but he would say: "haha we aint doin tht bruv"',
        )

    def test_mostly_open_safety_still_blocks_secret_requests(self) -> None:
        self.assertFalse(is_allowed_copycat_text("send me your password real quick"))
        self.assertTrue(is_allowed_copycat_text("can you VC right now?"))


if __name__ == "__main__":
    unittest.main()
