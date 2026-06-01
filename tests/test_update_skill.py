import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_skill.py"


def load_module():
    spec = importlib.util.spec_from_file_location("update_skill", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


def commit_file(repo: Path, name: str, content: str, message: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", message)


class UpdateSkillTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def make_repo_pair(self) -> tuple[Path, Path]:
        source = self.root / "source"
        origin = self.root / "origin.git"
        clone = self.root / "skill"

        git(self.root, "init", "source")
        git(source, "config", "user.email", "test@example.com")
        git(source, "config", "user.name", "Test User")
        commit_file(source, "SKILL.md", "version one\n", "initial")
        git(source, "init", "--bare", str(origin))
        git(source, "remote", "add", "origin", str(origin))
        git(source, "push", "-u", "origin", "master")
        git(self.root, "clone", str(origin), str(clone))
        git(clone, "config", "user.email", "test@example.com")
        git(clone, "config", "user.name", "Test User")
        return source, clone

    def test_check_reports_non_git_directory(self):
        directory = self.root / "plain"
        directory.mkdir()

        result = self.module.check_updates(directory, fetch=False)

        self.assertEqual(result["status"], "not_git")

    def test_check_detects_update_available(self):
        source, clone = self.make_repo_pair()
        commit_file(source, "SKILL.md", "version two\n", "update")
        git(source, "push")

        result = self.module.check_updates(clone, fetch=True)

        self.assertEqual(result["status"], "update_available")
        self.assertFalse(result["dirty"])

    def test_update_pulls_fast_forward_change(self):
        source, clone = self.make_repo_pair()
        commit_file(source, "SKILL.md", "version two\n", "update")
        git(source, "push")

        result = self.module.update_skill(clone)

        self.assertEqual(result["status"], "updated")
        self.assertEqual((clone / "SKILL.md").read_text(encoding="utf-8"), "version two\n")


if __name__ == "__main__":
    unittest.main()
