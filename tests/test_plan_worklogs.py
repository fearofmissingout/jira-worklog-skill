import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan_worklogs.py"


def run_plan(payload, extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


class PlanWorklogsTest(unittest.TestCase):
    def test_splits_multi_week_default_plan_into_weekly_issues(self):
        result = run_plan(
            {
                "date_from": "2026-05-18",
                "date_to": "2026-05-29",
                "project": {"key": "EXAMPLE", "name": "Example Project"},
                "default_hours": 8,
                "description": "Feature development",
                "category": "Development",
            }
        )

        self.assertEqual([issue["week_start"] for issue in result["issue_drafts"]], [
            "2026-05-18",
            "2026-05-25",
        ])
        self.assertTrue(all(issue["project_key"] == "EXAMPLE" for issue in result["issue_drafts"]))
        self.assertTrue(all(len(issue["worklogs"]) == 5 for issue in result["issue_drafts"]))
        self.assertTrue(all(worklog["hours"] == 8 for issue in result["issue_drafts"] for worklog in issue["worklogs"]))
        self.assertEqual(result["questions"], [])

    def test_uses_one_issue_per_explicit_daily_activity_without_crossing_weeks(self):
        result = run_plan(
            {
                "date_from": "2026-05-25",
                "date_to": "2026-05-26",
                "project": {"key": "EXAMPLE", "name": "Example Project"},
                "category": "Development",
                "activities": [
                    {"date": "2026-05-25", "description": "API integration", "hours": 4},
                    {"date": "2026-05-25", "description": "Data sync", "hours": 4},
                    {"date": "2026-05-26", "description": "Report fix", "hours": 8},
                ],
            }
        )

        self.assertEqual(len(result["issue_drafts"]), 3)
        self.assertEqual({issue["week_start"] for issue in result["issue_drafts"]}, {"2026-05-25"})
        self.assertEqual([issue["worklogs"][0]["hours"] for issue in result["issue_drafts"]], [4, 4, 8])

    def test_removes_holidays_and_adds_makeup_workdays(self):
        result = run_plan(
            {
                "date_from": "2026-05-01",
                "date_to": "2026-05-03",
                "project": {"key": "EXAMPLE", "name": "Example Project"},
                "default_hours": 8,
                "description": "Feature development",
                "category": "Development",
                "non_workdays": ["2026-05-01"],
                "extra_workdays": ["2026-05-02"],
            }
        )

        worklog_dates = [
            worklog["date"]
            for issue in result["issue_drafts"]
            for worklog in issue["worklogs"]
        ]
        self.assertEqual(worklog_dates, ["2026-05-02"])
        self.assertEqual(result["questions"], [])

    def test_blocks_day_totals_over_eight_hours(self):
        result = run_plan(
            {
                "date_from": "2026-05-25",
                "date_to": "2026-05-25",
                "project": {"key": "EXAMPLE", "name": "Example Project"},
                "category": "Development",
                "activities": [
                    {"date": "2026-05-25", "description": "API integration", "hours": 8},
                    {"date": "2026-05-25", "description": "Bug fix", "hours": 2},
                ],
            }
        )

        self.assertEqual(result["blocking_errors"], [
            "2026-05-25 totals 10.0h, above the 8.0h daily limit."
        ])

    def test_reuses_matching_existing_issue_for_same_week_only(self):
        result = run_plan(
            {
                "date_from": "2026-05-18",
                "date_to": "2026-05-29",
                "project": {"key": "EXAMPLE", "name": "Example Project"},
                "default_hours": 8,
                "description": "Feature development",
                "existing_issues": [
                    {
                        "key": "EXAMPLE-101",
                        "summary": "2026-W21 Feature development",
                        "week_start": "2026-05-18",
                    },
                    {
                        "key": "EXAMPLE-102",
                        "summary": "2026-W22 Feature development",
                        "week_start": "2026-05-25",
                    },
                ],
            }
        )

        self.assertEqual([issue["issue_key"] for issue in result["issue_drafts"]], [
            "EXAMPLE-101",
            "EXAMPLE-102",
        ])
        self.assertTrue(all(issue["needs_issue_creation"] is False for issue in result["issue_drafts"]))

    def test_reads_default_category_from_environment_json(self):
        result = run_plan(
            {
                "date_from": "2026-06-01",
                "date_to": "2026-06-05",
                "project": {"key": "EXAMPLE", "name": "Example Project"},
                "default_hours": 8,
                "description": "Feature development",
            },
            extra_env={"JIRA_DEFAULT_CATEGORIES_JSON": '{"EXAMPLE":"Development"}'},
        )

        self.assertEqual(result["issue_drafts"][0]["category"], "Development")
        self.assertEqual(result["questions"], [])


if __name__ == "__main__":
    unittest.main()
