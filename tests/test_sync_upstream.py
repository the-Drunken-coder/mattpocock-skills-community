import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.sync_upstream import selected_skill_paths, upstream_sha


class SelectedSkillPathsTests(unittest.TestCase):
    def test_includes_promoted_and_in_progress_skills(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_root = root / "skills" / "in-progress" / "pr"
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("---\nname: pr\n---\n")

            paths = selected_skill_paths(
                root,
                {
                    "license": "MIT",
                    "skills": ["./skills/engineering/code-review"],
                },
            )

        self.assertEqual(
            paths,
            ["./skills/engineering/code-review", "./skills/in-progress/pr"],
        )

    def test_ignores_in_progress_directories_without_a_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "skills" / "in-progress" / "notes").mkdir(parents=True)

            paths = selected_skill_paths(
                root,
                {"license": "MIT", "skills": []},
            )

        self.assertEqual(paths, [])

    def test_rejects_duplicate_skill_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_root = root / "skills" / "in-progress" / "pr"
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("---\nname: pr\n---\n")

            with self.assertRaisesRegex(RuntimeError, "duplicate upstream skill directory"):
                selected_skill_paths(
                    root,
                    {"license": "MIT", "skills": ["./skills/engineering/pr"]},
                )


class UpstreamShaTests(unittest.TestCase):
    @patch("scripts.sync_upstream.subprocess.run")
    def test_resolves_branch_with_git_ls_remote(self, run: Mock) -> None:
        sha = "0123456789abcdef0123456789abcdef01234567"
        run.return_value = Mock(stdout=f"{sha}\trefs/heads/main\n")

        self.assertEqual(upstream_sha("main"), sha)
        run.assert_called_once_with(
            [
                "git",
                "ls-remote",
                "https://github.com/mattpocock/skills.git",
                "refs/heads/main",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

    @patch("scripts.sync_upstream.subprocess.run")
    def test_ignores_other_refs_in_git_output(self, run: Mock) -> None:
        expected = "0123456789abcdef0123456789abcdef01234567"
        other = "fedcba9876543210fedcba9876543210fedcba98"
        run.return_value = Mock(
            stdout=f"{other}\trefs/heads/main-old\n{expected}\trefs/heads/main\n"
        )

        self.assertEqual(upstream_sha("main"), expected)

    @patch("scripts.sync_upstream.subprocess.run")
    def test_rejects_missing_exact_ref(self, run: Mock) -> None:
        run.return_value = Mock(
            stdout="0123456789abcdef0123456789abcdef01234567\trefs/heads/main-old\n"
        )

        with self.assertRaisesRegex(RuntimeError, "not uniquely resolved: main"):
            upstream_sha("main")

    @patch("scripts.sync_upstream.subprocess.run")
    def test_reports_git_timeout(self, run: Mock) -> None:
        run.side_effect = subprocess.TimeoutExpired(["git", "ls-remote"], 60)

        with self.assertRaisesRegex(RuntimeError, "timed out resolving upstream ref: main"):
            upstream_sha("main")


if __name__ == "__main__":
    unittest.main()
