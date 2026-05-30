from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from panoptibot.bot.doctor import DoctorResult, check_writable_directory


class DoctorTest(unittest.TestCase):
    def test_check_writable_directory_creates_missing_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "copycat"

            result = check_writable_directory("copycat_dir", path)

            self.assertEqual(result, DoctorResult("copycat_dir", True, str(path)))
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
