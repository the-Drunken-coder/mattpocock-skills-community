import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import sync_upstream
from scripts.artifact_labels import (
    ARTIFACT_KINDS,
    PATCHES,
    ArtifactLabelError,
    apply_artifact_labels,
    strip_artifact_labels,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "0123456789abcdef0123456789abcdef01234567"


def imported_files() -> dict[str, str]:
    """Load bundled text with the community label additions removed."""
    return {
        relative: strip_artifact_labels(
            relative, (ROOT / "skills" / relative).read_text(encoding="utf-8")
        )
        for relative in dict.fromkeys(item.path for item in PATCHES)
    }


def write_skills(root: Path, files: dict[str, str]) -> None:
    """Write fixture files using the same encoding as the skill importer."""
    for relative, contents in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")


def snapshot(root: Path) -> dict[str, bytes]:
    """Capture file paths and bytes to detect partial package publication."""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def archive_with(files: dict[str, str]) -> bytes:
    """Build a minimal upstream archive from the supplied skill fixtures."""
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "upstream"
        write_skills(root / "skills" / "engineering", files)
        (root / "skills" / "in-progress").mkdir()
        manifest = root / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir()
        manifest.write_text(
            json.dumps(
                {
                    "license": "MIT",
                    "skills": [
                        f"./skills/engineering/{name}"
                        for name in sorted({Path(path).parts[0] for path in files})
                    ],
                }
            ),
            encoding="utf-8",
        )
        (root / "LICENSE").write_text("Upstream MIT license\n", encoding="utf-8")
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:gz") as tar:
            tar.add(root, arcname="upstream")
        return archive.getvalue()


class ArtifactLabelsTests(unittest.TestCase):
    def test_adds_only_the_expected_kinds_and_preserves_imported_content(self) -> None:
        files = imported_files()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_skills(root, files)
            report = apply_artifact_labels(root)
            assignments = {entry["path"]: entry["kinds"] for entry in report}
            self.assertEqual(assignments["matt-to-spec/SKILL.md"], ["kind:spec"])
            self.assertEqual(assignments["matt-to-tickets/SKILL.md"], ["kind:ticket"])
            self.assertEqual(
                assignments["matt-wayfinder/SKILL.md"], ["kind:map", "kind:ticket"]
            )
            for relative, source in files.items():
                generated = (root / relative).read_text(encoding="utf-8")
                self.assertEqual(strip_artifact_labels(relative, generated), source)
            self.assertIn(
                "**Kind:** ticket\n\n**Status:** ready-for-agent",
                (root / "matt-to-tickets/SKILL.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                tuple(ARTIFACT_KINDS), ("kind:spec", "kind:ticket", "kind:map")
            )

    def test_reapplying_is_idempotent_and_check_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_skills(root, imported_files())
            report = apply_artifact_labels(root)
            before = snapshot(root)
            self.assertEqual(apply_artifact_labels(root), report)
            self.assertEqual(apply_artifact_labels(root, check=True), report)
            self.assertEqual(snapshot(root), before)

    def test_each_missing_insertion_point_stops_all_edits(self) -> None:
        for target in PATCHES:
            with (
                self.subTest(path=target.path, anchor=target.anchor),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                files = imported_files()
                files[target.path] = files[target.path].replace(
                    target.anchor, "Upstream changed this section.\n", 1
                )
                write_skills(root, files)
                before = snapshot(root)
                with self.assertRaises(ArtifactLabelError):
                    apply_artifact_labels(root)
                self.assertEqual(snapshot(root), before)

    def test_missing_skill_stops_all_edits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = imported_files()
            files.pop("matt-wayfinder/SKILL.md")
            write_skills(root, files)
            before = snapshot(root)
            with self.assertRaisesRegex(
                ArtifactLabelError, "required upstream file missing"
            ):
                apply_artifact_labels(root)
            self.assertEqual(snapshot(root), before)

    def test_ambiguous_insertion_point_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = imported_files()
            files[PATCHES[0].path] += PATCHES[0].anchor
            write_skills(root, files)
            with self.assertRaisesRegex(ArtifactLabelError, "found 2"):
                apply_artifact_labels(root)

    def test_upstream_kind_vocabulary_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = imported_files()
            files["matt-wayfinder/SKILL.md"] += "\nUse kind:decision for children.\n"
            write_skills(root, files)
            before = snapshot(root)
            with self.assertRaisesRegex(
                ArtifactLabelError, "upstream now defines kind labels"
            ):
                apply_artifact_labels(root)
            self.assertEqual(snapshot(root), before)

    def test_check_rejects_a_missing_adaptation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_skills(root, imported_files())
            apply_artifact_labels(root)
            target = root / PATCHES[0].path
            target.write_text(
                target.read_text(encoding="utf-8").replace(PATCHES[0].addition, ""),
                encoding="utf-8",
            )
            before = snapshot(root)
            with self.assertRaisesRegex(
                ArtifactLabelError, "missing or modified adaptation"
            ):
                apply_artifact_labels(root, check=True)
            self.assertEqual(snapshot(root), before)


class SyncStagingTests(unittest.TestCase):
    def prepare_package(self, root: Path) -> None:
        """Seed a previous bundle whose bytes must survive failed syncs."""
        (root / ".codex-plugin").mkdir()
        for relative in ("plugin.json", ".codex-plugin/plugin.json"):
            (root / relative).write_text(
                json.dumps({"version": "0.3.0+upstream.old"}), encoding="utf-8"
            )
        write_skills(root / "skills", {"old/SKILL.md": "Previously published skill\n"})
        (root / "LICENSE").write_text(
            "Previously published license\n", encoding="utf-8"
        )
        (root / "THIRD_PARTY_NOTICES.md").write_text(
            "Previously published notice\n", encoding="utf-8"
        )

    def run_sync(
        self, root: Path, files: dict[str, str], report: dict[str, object]
    ) -> str:
        """Run production sync against a fixture archive without network calls."""
        with (
            patch.object(sync_upstream, "PLUGIN_ROOT", root),
            patch.object(sync_upstream, "upstream_sha", return_value=SHA),
            patch.object(sync_upstream, "fetch", return_value=archive_with(files)),
        ):
            return sync_upstream.sync("main", report=report)

    def test_sync_survives_upstream_changes_and_repeated_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_package(root)
            files = imported_files()
            files["matt-to-spec/SKILL.md"] += (
                "\nA new upstream instruction that must survive import.\n"
            )
            files["unrelated/SKILL.md"] = (
                "---\nname: unrelated\ndescription: Unrelated skill\n---\nUnchanged workflow.\n"
            )
            report: dict[str, object] = {}
            self.assertEqual(self.run_sync(root, files, report), SHA)
            self.assertEqual(report["status"], "success")
            self.assertEqual(report["skill_count"], 5)
            self.assertFalse((root / "skills/old").exists())
            spec = (root / "skills/matt-to-spec/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("A new upstream instruction", spec)
            self.assertIn("kind:spec", spec)
            self.assertNotIn(
                "kind:",
                (root / "skills/matt-unrelated/SKILL.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                json.loads((root / "plugin.json").read_text(encoding="utf-8"))[
                    "version"
                ],
                f"0.3.0+upstream.{SHA[:8]}",
            )
            before = snapshot(root)
            repeated: dict[str, object] = {}
            self.run_sync(root, files, repeated)
            self.assertEqual(snapshot(root), before)
            self.assertEqual(repeated["changed_adaptation_sources"], [])

    def test_contract_failure_keeps_the_previous_package_intact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_package(root)
            files = imported_files()
            files.pop("matt-wayfinder/SKILL.md")
            before = snapshot(root)
            with self.assertRaises(ArtifactLabelError):
                self.run_sync(root, files, {})
            self.assertEqual(snapshot(root), before)

    def test_invalid_manifest_keeps_the_previous_package_intact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_package(root)
            (root / "plugin.json").write_text('{"version": null}', encoding="utf-8")
            before = snapshot(root)
            with self.assertRaisesRegex(RuntimeError, "manifest has no version"):
                self.run_sync(root, imported_files(), {})
            self.assertEqual(snapshot(root), before)

    def test_every_publication_replace_failure_restores_the_entire_package(
        self,
    ) -> None:
        real_replace = Path.replace
        for fail_at in range(6):
            for missing in ((), ("LICENSE", "THIRD_PARTY_NOTICES.md")):
                with (
                    self.subTest(fail_at=fail_at, missing=missing),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    root = Path(temporary)
                    self.prepare_package(root)
                    for relative in missing:
                        (root / relative).unlink()
                    before = snapshot(root)
                    calls = 0

                    def fail_one_replace(
                        path: Path, target: Path, fail_on: int = fail_at
                    ) -> Path:
                        nonlocal calls
                        current = calls
                        calls += 1
                        if current == fail_on:
                            raise OSError("injected publication failure")
                        return real_replace(path, target)

                    with (
                        patch.object(Path, "replace", fail_one_replace),
                        self.assertRaises(OSError),
                    ):
                        self.run_sync(root, imported_files(), {})
                    self.assertEqual(snapshot(root), before)
                    self.assertEqual(list(root.glob(".sync-backup-*")), [])

    def test_publication_failure_preserves_an_absent_skills_directory(self) -> None:
        real_replace = Path.replace
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_package(root)
            sync_upstream.shutil.rmtree(root / "skills")
            before = snapshot(root)

            def fail_manifest_replace(path: Path, target: Path) -> Path:
                if Path(target) == root / "plugin.json" and "generated" in path.parts:
                    raise OSError("injected metadata failure")
                return real_replace(path, target)

            with (
                patch.object(Path, "replace", fail_manifest_replace),
                self.assertRaises(OSError),
            ):
                self.run_sync(root, imported_files(), {})
            self.assertEqual(snapshot(root), before)

    def test_unicode_fixture_round_trip_matches_production(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = "Expand–contract → preserve café and 日本語.\n"
            write_skills(root, {"example/SKILL.md": source})
            target = root / "example/SKILL.md"
            self.assertEqual(target.read_bytes(), source.encode("utf-8"))
            self.assertEqual(target.read_text(encoding="utf-8"), source)

    def test_failed_rollback_keeps_recovery_backups_after_staging_cleanup(self) -> None:
        real_replace = Path.replace
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.prepare_package(root)
            before = snapshot(root)

            def fail_publication_and_restore(path: Path, target: Path) -> Path:
                if Path(target) == root / "plugin.json" and "generated" in path.parts:
                    raise OSError("injected publication failure")
                if path.name == "skills" and path.parent.name.startswith(
                    ".sync-backup-"
                ):
                    raise OSError("injected rollback failure")
                return real_replace(path, target)

            with (
                patch.object(Path, "replace", fail_publication_and_restore),
                self.assertRaisesRegex(RuntimeError, "rollback incomplete") as error,
            ):
                self.run_sync(root, imported_files(), {})
            backups = list(root.glob(".sync-backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertIn(str(backups[0]), str(error.exception))
            self.assertEqual(
                (backups[0] / "skills/old/SKILL.md").read_bytes(),
                before["skills/old/SKILL.md"],
            )
            for relative in sync_upstream.PACKAGE_FILES:
                self.assertEqual((root / relative).read_bytes(), before[relative])

    def test_cli_failure_produces_a_report_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path, summary_path = root / "report.json", root / "summary.md"
            with (
                patch.object(sync_upstream, "PLUGIN_ROOT", root),
                patch.object(
                    sync_upstream,
                    "upstream_sha",
                    side_effect=RuntimeError("network unavailable"),
                ),
                patch("sys.argv", ["sync_upstream.py", "--report", str(report_path)]),
                patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": str(summary_path)}),
                patch("sys.stderr", new=io.StringIO()),
                self.assertRaises(SystemExit) as error,
            ):
                sync_upstream.main()
            self.assertEqual(error.exception.code, 1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failure")
            self.assertEqual(report["stage"], "resolve upstream")
            self.assertEqual(report["error"], "network unavailable")
            self.assertIn(
                "network unavailable", summary_path.read_text(encoding="utf-8")
            )


if __name__ == "__main__":
    unittest.main()
