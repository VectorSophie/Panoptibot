from datetime import UTC, datetime
import unittest

from panoptibot.ml.feature_engineering import (
    FEATURE_NAMES,
    build_feature_vector,
    calculate_rarity_score,
    normalize_time_of_day,
)


class FeatureEngineeringTest(unittest.TestCase):
    def test_feature_vector_order_is_stable(self) -> None:
        features = {name: index for index, name in enumerate(FEATURE_NAMES, start=1)}
        vector = build_feature_vector(features)
        self.assertEqual(len(vector), len(FEATURE_NAMES))
        self.assertEqual(vector[0], 1.0)
        self.assertEqual(vector[-1], float(len(FEATURE_NAMES)))

    def test_rarity_score_zero_safe(self) -> None:
        self.assertEqual(calculate_rarity_score(0, 10), 0.0)
        self.assertGreater(calculate_rarity_score(1, 10), 0.0)

    def test_normalize_time_of_day(self) -> None:
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        self.assertAlmostEqual(normalize_time_of_day(timestamp), 0.5, places=2)


if __name__ == "__main__":
    unittest.main()
