import unittest

from panoptibot.catchup.social import SocialFact, render_catchup_bullets


class CatchupBulletsTest(unittest.TestCase):
    def test_renders_social_fact_as_source_linked_bullet(self) -> None:
        fact = SocialFact(
            subject_names=("Kromer",),
            related_names=("Bitzy",),
            action="would_hang_out_later",
            evidence_urls=("https://discord.com/channels/1/2/3",),
            confidence=0.91,
        )

        bullets = render_catchup_bullets([fact], viewer_name="Jack")

        self.assertEqual(
            bullets,
            [
                "Catch-up for @Jack",
                "- Kromer said he would hang out with Bitzy later. Source: https://discord.com/channels/1/2/3",
            ],
        )

    def test_hedges_low_confidence_social_fact(self) -> None:
        fact = SocialFact(
            subject_names=("Jack",),
            related_names=(),
            action="can_vc_now",
            evidence_urls=("https://discord.com/channels/1/2/4",),
            confidence=0.42,
        )

        bullets = render_catchup_bullets([fact], viewer_name="Jack")

        self.assertIn(
            "- Looks like Jack said he can VC right now. Source: https://discord.com/channels/1/2/4",
            bullets,
        )


if __name__ == "__main__":
    unittest.main()
