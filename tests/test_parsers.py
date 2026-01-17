import unittest

import pandas as pd

from sentencing_data_processing import (
    calculate_total_days,
    parse_jail_string,
    parse_offence_string,
    parse_uid_string,
)


class TestParsers(unittest.TestCase):
    def test_uid_default_defendant(self) -> None:
        parsed = parse_uid_string("2024mbpc96_None_1")
        self.assertEqual(parsed["defendant"], "a")

    def test_offence_preserves_ycja_on_unmatched(self) -> None:
        offences_df = pd.DataFrame(columns=["section", "offence_name"])
        parsed = parse_offence_string("cc_999_ycja", offences_df=offences_df)
        self.assertEqual(parsed["offence_code"], "cc_999_ycja")
        self.assertIsNone(parsed["offence_name"])

    def test_jail_unrecognized(self) -> None:
        parsed = parse_jail_string("n/a")
        self.assertIsNone(parsed)
        self.assertIsNone(calculate_total_days(parsed))

    def test_jail_empty_is_zero(self) -> None:
        parsed = parse_jail_string("")
        self.assertTrue(hasattr(parsed, "empty"))
        self.assertEqual(calculate_total_days(parsed), 0)


if __name__ == "__main__":
    unittest.main()
