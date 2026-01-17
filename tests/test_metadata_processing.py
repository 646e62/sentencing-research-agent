import unittest
from unittest.mock import patch, Mock

import metadata_processing


class TestMetadataProcessing(unittest.TestCase):
    def test_get_metadata_from_citation_parses_fields(self) -> None:
        parsed = {
            "uid": "2024skca79",
            "style_of_cause": "R v Example",
            "atomic_citation": "2024 SKCA 79",
            "citation_type": "neutral",
            "official_reporter_citation": None,
            "year": "2024",
            "court": "SKCA",
            "decision_number": "79",
            "jurisdiction": "SK",
            "court_name": "Saskatchewan Court of Appeal",
            "court_level": "appellate",
            "long_url": "https://example.com/long",
            "short_url": "https://example.com/short",
            "language": "en",
            "docket_number": "12345",
            "decision_date": "2024-01-01",
            "keywords": ["sentencing"],
            "categories": ["criminal"],
        }

        with patch.object(metadata_processing, "_parse_citation", return_value=parsed):
            metadata = metadata_processing.get_metadata_from_citation("2024 SKCA 79")

        self.assertEqual(metadata["citation"], "R v Example, 2024 SKCA 79 (CanLII)")
        self.assertEqual(metadata["case_id"], "2024skca79")
        self.assertEqual(metadata["court"], "SKCA")
        self.assertEqual(metadata["keywords"], ["sentencing"])

    def test_get_metadata_from_citation_handles_parse_failure(self) -> None:
        with patch.object(metadata_processing, "_parse_citation", return_value=None):
            metadata = metadata_processing.get_metadata_from_citation("bad citation")
        self.assertIsNone(metadata)

    def test_get_citing_cases_missing_api_key(self) -> None:
        with patch.object(metadata_processing.Config, "CANLII_API_KEY", ""):
            result = metadata_processing.get_citing_cases("2024 SKCA 79")
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["cases"], [])

    def test_get_citing_cases_rate_limit(self) -> None:
        response = Mock(status_code=429)
        with patch.object(metadata_processing.Config, "CANLII_API_KEY", "key"), \
             patch.object(metadata_processing, "_parse_citation", return_value={"court": "SKCA", "uid": "2024skca79"}), \
             patch.object(metadata_processing.requests, "get", return_value=response):
            result = metadata_processing.get_citing_cases("2024 SKCA 79")

        self.assertEqual(result["error"], "Rate limit reached")
        self.assertEqual(result["cases"], [])

    def test_get_citing_cases_non_200(self) -> None:
        response = Mock(status_code=500)
        with patch.object(metadata_processing.Config, "CANLII_API_KEY", "key"), \
             patch.object(metadata_processing, "_parse_citation", return_value={"court": "SKCA", "uid": "2024skca79"}), \
             patch.object(metadata_processing.requests, "get", return_value=response):
            result = metadata_processing.get_citing_cases("2024 SKCA 79")

        self.assertEqual(result["error"], "API error: 500")
        self.assertEqual(result["cases"], [])

    def test_get_citing_cases_success(self) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {
            "citingCases": [{"caseId": "1"}],
        }
        with patch.object(metadata_processing.Config, "CANLII_API_KEY", "key"), \
             patch.object(metadata_processing, "_parse_citation", return_value={"court": "SKCA", "uid": "2024skca79"}), \
             patch.object(metadata_processing.requests, "get", return_value=response):
            result = metadata_processing.get_citing_cases("2024 SKCA 79")

        self.assertIsNone(result["error"])
        self.assertEqual(result["cases"], [{"caseId": "1"}])


if __name__ == "__main__":
    unittest.main()
