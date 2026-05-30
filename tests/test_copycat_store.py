from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from panoptibot.copycat.store import CopycatStore


class CopycatStoreTest(unittest.TestCase):
    def test_session_round_trips_and_expires(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = CopycatStore(Path(temp_dir))
            now = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)

            store.enable_session(
                owner_user_id="123",
                display_name="Jack",
                duration_minutes=30,
                now=now,
                status_note="away gaming",
            )
            active = store.find_active_session_for_mentions(
                mentioned_user_ids={"123"},
                channel_id="456",
                now=now,
            )
            self.assertIsNone(active)

            store.add_channel("123", "456")
            active = store.find_active_session_for_mentions(
                mentioned_user_ids={"123"},
                channel_id="456",
                now=now,
            )
            self.assertIsNotNone(active)
            self.assertEqual(active.display_name, "Jack")

            expired = store.find_active_session_for_mentions(
                mentioned_user_ids={"123"},
                channel_id="456",
                now=now + timedelta(minutes=31),
            )
            self.assertIsNone(expired)

    def test_history_cache_keeps_only_opted_in_user_text(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = CopycatStore(Path(temp_dir))
            store.update_profile("123", display_name="Jack", history_enabled=True)
            store.update_profile("999", display_name="Maya", history_enabled=False)

            self.assertTrue(
                store.record_history_message(
                    user_id="123",
                    channel_id="456",
                    message_id="1",
                    content="haha we aint doin tht bruv",
                    timestamp=datetime(2026, 5, 30, 12, 0, tzinfo=UTC),
                )
            )
            self.assertFalse(
                store.record_history_message(
                    user_id="999",
                    channel_id="456",
                    message_id="2",
                    content="do not cache me",
                    timestamp=datetime(2026, 5, 30, 12, 0, tzinfo=UTC),
                )
            )
            examples = store.recent_examples("123", limit=5)
            self.assertEqual(examples, ["haha we aint doin tht bruv"])


if __name__ == "__main__":
    unittest.main()
