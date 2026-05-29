import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from jira_tempo_client import fetch_issue_details, summarize_tempo_worklogs


class TempoSummaryTest(unittest.TestCase):
    def test_summary_includes_project_fields_from_tempo_issue_payload(self):
        rows = summarize_tempo_worklogs(
            [
                {
                    "dateStarted": "2026-05-25T00:00:00.000",
                    "timeSpentSeconds": 28800,
                    "issue": {
                        "key": "EXAMPLE-101",
                        "summary": "Feature development",
                        "project": {"key": "EXAMPLE", "name": "Example Project"},
                    },
                }
            ]
        )

        self.assertEqual(
            rows[0],
            {
                "date": "2026-05-25",
                "project_key": "EXAMPLE",
                "project_name": "Example Project",
                "issue_key": "EXAMPLE-101",
                "issue_summary": "Feature development",
                "hours": 8.0,
            },
        )

    def test_summary_derives_project_key_when_tempo_payload_omits_project(self):
        rows = summarize_tempo_worklogs(
            [
                {
                    "dateStarted": "2026-05-25T00:00:00.000",
                    "timeSpentSeconds": 14400,
                    "issue": {
                        "key": "EXAMPLE-101",
                        "summary": "Feature development",
                    },
                }
            ]
        )

        self.assertEqual(rows[0]["project_key"], "EXAMPLE")
        self.assertEqual(rows[0]["project_name"], "")

    def test_fetch_issue_details_reads_project_fields_from_jira_search(self):
        class FakeClient:
            def __init__(self):
                self.jql = None

            def search_issues(self, jql, fields, max_results):
                self.jql = jql
                self.fields = fields
                self.max_results = max_results
                return {
                    "issues": [
                        {
                            "key": "EXAMPLE-101",
                            "fields": {
                                "summary": "Feature development",
                                "project": {
                                    "key": "EXAMPLE",
                                    "name": "Example Project",
                                },
                            },
                        }
                    ]
                }

        fake = FakeClient()
        details = fetch_issue_details(fake, ["EXAMPLE-101"])

        self.assertIn('"EXAMPLE-101"', fake.jql)
        self.assertEqual(fake.fields, "summary,project")
        self.assertEqual(fake.max_results, 1)
        self.assertEqual(
            details["EXAMPLE-101"],
            {
                "issue_summary": "Feature development",
                "project_key": "EXAMPLE",
                "project_name": "Example Project",
            },
        )


if __name__ == "__main__":
    unittest.main()
