import unittest

from panoptibot.culture.memory import bridge_users, culture_memory_lines


class CultureMemoryTest(unittest.TestCase):
    def test_bridge_users_sums_weighted_edges(self) -> None:
        rows = [
            {"source_user": "a", "target_user": "b", "weight": 2},
            {"source_user": "c", "target_user": "b", "weight": 3},
        ]

        self.assertEqual(bridge_users(rows, limit=2), [("b", 5.0), ("c", 3.0)])

    def test_culture_memory_lines_describes_observed_patterns(self) -> None:
        lines = culture_memory_lines(
            emoji_rows=[{"emoji": "🔥", "usage_count": 4}],
            bridge_rows=[("b", 5.0)],
        )

        self.assertIn("- Emoji showing up most: 🔥 (4 uses)", lines)
        self.assertIn("- Bridge user candidate: <@b> connects active conversations", lines)


if __name__ == "__main__":
    unittest.main()
