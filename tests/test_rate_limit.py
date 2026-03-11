import unittest

from panoptibot.bot.rate_limit import SlidingWindowRateLimiter


class RateLimiterTest(unittest.TestCase):
    def test_limiter_blocks_after_limit(self) -> None:
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)
        self.assertTrue(limiter.allow("user"))
        self.assertTrue(limiter.allow("user"))
        self.assertFalse(limiter.allow("user"))


if __name__ == "__main__":
    unittest.main()
