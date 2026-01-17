import unittest

from case_data_processing import get_sentencing_data_for_case_id
from sentencing_data_processing import load_master_csv, parse_uid_string


class TestCaseDataProcessing(unittest.TestCase):
    def test_sentencing_data_multiple_uids_for_case_id(self) -> None:
        df = load_master_csv()
        if df.empty or "uid" not in df.columns:
            self.skipTest("master.csv missing or has no uid column")

        case_id_counts = {}
        for uid_value in df["uid"].tolist():
            parsed = parse_uid_string(uid_value)
            case_id = parsed.get("case_id")
            if not case_id:
                continue
            case_id_counts[case_id] = case_id_counts.get(case_id, 0) + 1

        multi_case_ids = [cid for cid, count in case_id_counts.items() if count > 1]
        if not multi_case_ids:
            self.skipTest("No case_id with multiple uids found in master.csv")

        case_id = multi_case_ids[0]
        expected_uids = {
            str(uid).strip()
            for uid in df["uid"].tolist()
            if parse_uid_string(uid).get("case_id") == case_id
        }

        result = get_sentencing_data_for_case_id(case_id)

        self.assertEqual(set(result.keys()), expected_uids)
        self.assertEqual(len(result), case_id_counts[case_id])


if __name__ == "__main__":
    unittest.main()
