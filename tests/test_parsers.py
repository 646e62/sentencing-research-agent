import logging
import logging.handlers
import os
import tempfile
import unittest

import pandas as pd

from cli import run_cli
from sentencing_data_processing import (
    calculate_total_days,
    parse_appeal_string,
    parse_conditions_string,
    parse_date_string,
    parse_fine_string,
    parse_jail_string,
    parse_mode_string,
    parse_offence_string,
    parse_uid_string,
    process_uid_string,
    process_master_row,
    validate_master_schema,
)


class TestParsers(unittest.TestCase):
    def test_uid_default_defendant(self) -> None:
        parsed = parse_uid_string("2024mbpc96_None_1")
        self.assertEqual(parsed["defendant"], "a")

    def test_uid_logging_branch(self) -> None:
        logger = logging.getLogger("test_uid_logging")
        logger.setLevel(logging.INFO)
        handler = logging.handlers.BufferingHandler(capacity=10)
        logger.addHandler(handler)

        process_uid_string(
            "2024mbpc96_None_1_a",
            log=True,
            log_level=logging.INFO,
            logger_override=logger,
        )

        self.assertTrue(handler.buffer)
        record = handler.buffer[0]
        self.assertIn("Parsed UID string", record.getMessage())

    def test_date_parsing(self) -> None:
        single = parse_date_string("2024-12-18")
        self.assertEqual(single["offence_date"], "2024-12-18")
        self.assertIsNone(single["offence_start_date"])
        self.assertIsNone(single["offence_end_date"])

        ranged = parse_date_string("1970-09-01&1981-07-01")
        self.assertEqual(ranged["offence_start_date"], "1970-09-01")
        self.assertEqual(ranged["offence_end_date"], "1981-07-01")
        self.assertIsNone(ranged["offence_date"])

    def test_mode_parsing(self) -> None:
        self.assertEqual(parse_mode_string("jail-consecutive"), ("jail", "consecutive"))
        self.assertEqual(parse_mode_string("jail"), ("jail", None))

    def test_conditions_parsing(self) -> None:
        parsed = parse_conditions_string("18m-probation")
        self.assertEqual(parsed["time"], 18.0)
        self.assertEqual(parsed["unit"], "m")
        self.assertEqual(parsed["type"], "probation")

    def test_fine_parsing(self) -> None:
        self.assertEqual(parse_fine_string("$1,000"), "$1000.00")
        self.assertEqual(parse_fine_string(2500), "$2500.00")
        self.assertIsNone(parse_fine_string("not-a-number"))

    def test_appeal_parsing(self) -> None:
        parsed = parse_appeal_string("2024skca79_upheld")
        self.assertEqual(parsed["court"], "2024skca79")
        self.assertEqual(parsed["result"], "upheld")

        parsed = parse_appeal_string("2024skca79")
        self.assertEqual(parsed["court"], "2024skca79")
        self.assertIsNone(parsed["result"])

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

    def test_validate_master_schema(self) -> None:
        df = pd.DataFrame(
            columns=[
                "uid",
                "offence",
                "date",
                "jail",
                "mode",
                "conditions",
                "fine",
                "appeal",
                "extra_col",
            ]
        )
        result = validate_master_schema(df)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["extra"], ["extra_col"])

    def test_calculate_total_days_mixed_units(self) -> None:
        df = pd.DataFrame(
            [
                {"quantity": 1, "unit": "y"},
                {"quantity": 6, "unit": "m"},
                {"quantity": 15, "unit": "d"},
            ]
        )
        self.assertEqual(calculate_total_days(df), 365 + (6 * 30) + 15)

    def test_calculate_total_days_12_months_is_year(self) -> None:
        df = pd.DataFrame([{"quantity": 12, "unit": "m"}])
        self.assertEqual(calculate_total_days(df), 365)

    def test_offence_positive_lookup(self) -> None:
        offences_df = pd.DataFrame(
            [
                {"section": "cc_101", "offence_name": "Test offence"},
            ]
        )
        parsed = parse_offence_string("cc_101", offences_df=offences_df)
        self.assertEqual(parsed["offence_code"], "cc_101")
        self.assertEqual(parsed["offence_name"], "Test offence")

    def test_process_master_row_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            offences_file = os.path.join(tmp_dir, "offences.csv")
            pd.DataFrame(
                [{"section": "cc_101", "offence_name": "Test offence"}]
            ).to_csv(offences_file, index=False)

            row = {
                "uid": "2024mbpc96_None_1_a",
                "offence": "cc_101",
                "date": "2024-12-18",
                "jail": "1y&6m&3d",
                "mode": "jail-consecutive",
                "conditions": "18m-probation",
                "fine": "1000",
                "appeal": "2024skca79_upheld",
            }
            parsed = process_master_row(row, offences_file=offences_file, verbose=False)

        self.assertEqual(parsed["uid"]["defendant"], "a")
        self.assertEqual(parsed["offence"]["offence_name"], "Test offence")
        self.assertEqual(parsed["date"]["offence_date"], "2024-12-18")
        self.assertEqual(parsed["jail"]["total_days"], 365 + (6 * 30) + 3)
        self.assertFalse(parsed["jail"]["is_indeterminate"])
        self.assertFalse(parsed["jail"]["is_unrecognized"])
        self.assertEqual(parsed["mode"]["jail_type"], "jail")
        self.assertEqual(parsed["mode"]["sentence_mode"], "consecutive")
        self.assertEqual(parsed["conditions"]["type"], "probation")
        self.assertEqual(parsed["fine"], "$1000.00")
        self.assertEqual(parsed["appeal"]["result"], "upheld")

    def test_run_cli_validate_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            master_file = os.path.join(tmp_dir, "master.csv")
            offences_file = os.path.join(tmp_dir, "offences.csv")
            pd.DataFrame(
                [
                    {
                        "uid": "2024mbpc96_None_1_a",
                        "offence": "cc_101",
                        "date": "2024-12-18",
                        "jail": "1y",
                        "mode": "jail-consecutive",
                        "conditions": "18m-probation",
                        "fine": "1000",
                        "appeal": "2024skca79_upheld",
                    }
                ]
            ).to_csv(master_file, index=False)
            pd.DataFrame(
                [{"section": "cc_101", "offence_name": "Test offence"}]
            ).to_csv(offences_file, index=False)

            argv_backup = os.sys.argv[:]
            try:
                os.sys.argv = [
                    "sentencing_data_processing.py",
                    "--master",
                    master_file,
                    "--offences",
                    offences_file,
                    "--validate-only",
                ]
                exit_code = run_cli()
            finally:
                os.sys.argv = argv_backup

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
