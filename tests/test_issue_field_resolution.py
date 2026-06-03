import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from jira_tempo_client import select_allowed_option
from jira_worklog_cli import resolve_create_fields, validate_submittable


class IssueFieldResolutionTest(unittest.TestCase):
    def test_selects_development_validation_from_technical_intent(self):
        selected = select_allowed_option(
            [
                {"id": "1", "value": "方案文档"},
                {"id": "2", "value": "测试验证"},
                {"id": "3", "value": "会议沟通"},
            ],
            intent_text="trivy QA环境验证 drsec 数据导出接口 drsec 统一Lua处理方案",
            preferred_value="方案文档",
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["id"], "2")
        self.assertEqual(selected["payload"], {"id": "2"})

    def test_uses_work_category_policy_for_specific_typical_items(self):
        selected = select_allowed_option(
            [
                {"id": "1", "value": "方案与文档"},
                {"id": "2", "value": "开发测试与验证"},
                {"id": "3", "value": "会议与沟通"},
            ],
            intent_text="整理功能测试报告和验收材料",
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["value"], "方案与文档")

    def test_resolves_required_option_field_from_jira_metadata(self):
        result = resolve_create_fields(
            fields_meta={
                "project": {"required": True},
                "summary": {"required": True},
                "issuetype": {"required": True},
                "customfield_10000": {
                    "name": "Work Category",
                    "required": True,
                    "allowedValues": [
                        {"id": "1", "value": "方案与文档"},
                        {"id": "2", "value": "测试验证"},
                    ],
                },
            },
            local_rule={
                "category_field": "customfield_10000",
                "category": "方案与文档",
            },
            intent_text="QA验证和接口开发",
            assignee=None,
        )

        self.assertEqual(result["extra_fields"]["customfield_10000"], {"id": "2"})
        self.assertEqual(result["questions"], [])
        self.assertEqual(result["blocking_errors"], [])

    def test_submit_validation_requires_baseline_when_llm_used(self):
        errors = validate_submittable(
            {
                "issue_drafts": [
                    {
                        "needs_issue_creation": False,
                        "issue_key": "EXAMPLE-1",
                        "issue_summary": "Agent-assisted validation",
                        "worklogs": [
                            {
                                "date": "2026-06-01",
                                "hours": 4,
                                "llm_used": True,
                            }
                        ],
                    }
                ]
            }
        )

        self.assertEqual(errors, ["2026-06-01 used LLM/Agent but has no without_llm_hours baseline."])


if __name__ == "__main__":
    unittest.main()
