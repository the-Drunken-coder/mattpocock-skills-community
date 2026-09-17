import tempfile
import unittest
from pathlib import Path

from scripts.sync_upstream import selected_skill_paths


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


if __name__ == "__main__":
    unittest.main()
