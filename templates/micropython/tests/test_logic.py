import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from logic import blink_interval_ms


class FirmwareLogicTests(unittest.TestCase):
    def test_valid_interval(self):
        self.assertEqual(blink_interval_ms(500), 500)

    def test_invalid_interval(self):
        for n in (0, 10, 60001, -10):
            with self.subTest(n=n), self.assertRaises(ValueError):
                blink_interval_ms(n)


if __name__ == "__main__":
    unittest.main()
