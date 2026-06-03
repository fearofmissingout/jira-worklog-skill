import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from jira_tempo_client import JiraTempoClient, fetch_issue_details, jira_estimate_from_hours, summarize_tempo_worklogs


class TempoSummaryTest(unittest.TestCase):
    def test_jira_estimate_from_hours_formats_minutes(self):
        self.assertEqual(jira_estimate_from_hours(8), "8h")
        self.assertEqual(jira_estimate_from_hours(1.5), "1h 30m")
        self.assertEqual(jira_estimate_from_hours(0.25), "15m")

    def test_add_worklog_writes_remaining_estimate_when_baseline_is_supplied(self):
        class FakeClient(JiraTempoClient):
            def __init__(self):
                super().__init__(base_url="https://jira.example.test")
                self.calls = []

            def request(self, method, path, body=None, query=None, use_basic=True):
                self.calls.append({"method": method, "path": path, "body": body, "query": query})
                return {"id": "123"}

        fake = FakeClient()
        fake.add_worklog(
            "EXAMPLE-101",
            "2026-06-01",
            4,
            "Working on: API validation",
            remaining_estimate_hours=6.5,
        )

        self.assertEqual(fake.calls[0]["query"], {"adjustEstimate": "new", "newEstimate": "6h 30m"})
        self.assertEqual(fake.calls[0]["body"]["timeSpentSeconds"], 14400)

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
                "weekday": "周一",
                "project_key": "EXAMPLE",
                "project_name": "Example Project",
                "issue_key": "EXAMPLE-101",
                "issue_summary": "Feature development",
                "hours": 8.0,
                "issue_compliance": "合规",
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
        self.assertEqual(rows[0]["weekday"], "周一")
        self.assertEqual(rows[0]["issue_compliance"], "合规")

    def test_marks_issue_non_compliant_when_observed_dates_cross_weeks(self):
        rows = summarize_tempo_worklogs(
            [
                {
                    "dateStarted": "2026-05-29T00:00:00.000",
                    "timeSpentSeconds": 28800,
                    "issue": {"key": "EXAMPLE-101", "summary": "Feature development"},
                },
                {
                    "dateStarted": "2026-06-01T00:00:00.000",
                    "timeSpentSeconds": 28800,
                    "issue": {"key": "EXAMPLE-101", "summary": "Feature development"},
                },
            ]
        )

        self.assertEqual([row["issue_compliance"] for row in rows], ["不合规：issue跨周", "不合规：issue跨周"])

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
