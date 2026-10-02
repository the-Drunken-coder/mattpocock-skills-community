#!/usr/bin/env python3
"""Synchronize promoted and in-progress skills from Matt Pocock's repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

if __package__:
    from .artifact_labels import apply_artifact_labels, strip_artifact_labels
else:
    from artifact_labels import apply_artifact_labels, strip_artifact_labels


REPOSITORY = "mattpocock/skills"
DEFAULT_REF = "main"
SKILL_PREFIX = "matt-"
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DISABLE_INVOCATION_RE = re.compile(
    r"^(?P<indent>\s*)disable[-_]model[-_]invocation:\s*true\s*$"
)


def fetch(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "mattpocock-skills-community-sync",
        },
    )
    with urlopen(request, timeout=60) as response:
        return response.read()


def upstream_sha(ref: str) -> str:
    command = [
        "git",
        "ls-remote",
        f"https://github.com/{REPOSITORY}.git",
        f"refs/heads/{ref}",
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"timed out resolving upstream ref: {ref}") from error

    expected_ref = f"refs/heads/{ref}"
    matches = []
    for line in result.stdout.splitlines():
        sha, separator, returned_ref = line.partition("\t")
        if separator and returned_ref == expected_ref:
            matches.append(sha)
    if len(matches) != 1:
        raise RuntimeError(f"upstream ref is not uniquely resolved: {ref}")

    sha = matches[0]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError(f"invalid upstream SHA: {sha}")
    return sha


def extract_archive(archive: bytes, destination: Path) -> Path:
    archive_path = destination / "upstream.tar.gz"
    archive_path.write_bytes(archive)
    with tarfile.open(archive_path, mode="r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            member_path = PurePosixPath(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"unsafe archive member: {member.name}")
            if member.issym() or member.islnk():
                link_target = PurePosixPath(member.linkname)
                if link_target.is_absolute() or ".." in link_target.parts:
                    raise RuntimeError(f"unsafe archive link: {member.name} -> {member.linkname}")
        tar.extractall(destination)

    roots = [path for path in destination.iterdir() if path != archive_path]
    if len(roots) != 1 or not roots[0].is_dir():
        raise RuntimeError("upstream archive did not contain one repository directory")
    return roots[0]


def selected_skill_paths(
    upstream_root: Path, manifest: dict[str, object]
) -> list[str]:
    if manifest.get("license") != "MIT":
        raise RuntimeError("upstream plugin manifest is no longer MIT-licensed")
    raw_paths = manifest.get("skills")
    if not isinstance(raw_paths, list) or not all(isinstance(path, str) for path in raw_paths):
        raise RuntimeError("upstream plugin manifest has no valid skills list")

    paths = list(raw_paths)
    in_progress_root = upstream_root / "skills" / "in-progress"
    if not in_progress_root.is_dir():
        raise RuntimeError("upstream repository has no skills/in-progress directory")
    paths.extend(
        f"./{path.relative_to(upstream_root).as_posix()}"
        for path in sorted(in_progress_root.iterdir())
        if path.is_dir() and (path / "SKILL.md").is_file()
    )

    names: set[str] = set()
    for raw_path in paths:
        path = PurePosixPath(raw_path)
        if not raw_path.startswith("./skills/") or ".." in path.parts:
            raise RuntimeError(f"unsupported upstream skill path: {raw_path}")
        name = path.name
        if not name or name in names:
            raise RuntimeError(f"duplicate upstream skill directory: {name}")
        names.add(name)
    return paths


def version_for_sha(current: str, sha: str) -> str:
    base = current.split("+", maxsplit=1)[0]
    return f"{base}+upstream.{sha[:8]}"


def prefixed_skill_name(name: str) -> str:
    return name if name.startswith(SKILL_PREFIX) else f"{SKILL_PREFIX}{name}"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_codex_compatible(skill_root: Path) -> None:
    """Adapt Claude-only invocation metadata to the Codex ingestion contract."""
    skill_md = skill_root / "SKILL.md"
    contents = skill_md.read_text(encoding="utf-8")
    normalized = "\n".join(
        DISABLE_INVOCATION_RE.sub(
            r"\g<indent>disable-model-invocation: false", line
        )
        for line in contents.split("\n")
    )
    if normalized != contents:
        skill_md.write_text(normalized, encoding="utf-8")


def namespace_skill_tree(skill_root: Path, names: dict[str, str]) -> None:
    """Give every copied skill a stable Matt-prefixed Codex name and references."""
    for path in skill_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lines: list[str] = []
        for line in contents.split("\n"):
            if path.name == "SKILL.md":
                for source_name, namespaced_name in names.items():
                    line = re.sub(
                        rf"^(\s*name:\s*){re.escape(source_name)}(\s*)$",
                        rf"\g<1>{namespaced_name}\g<2>",
                        line,
                    )
            if path.name == "openai.yaml" and line.lstrip().startswith("display_name:"):
                prefix, value = line.split(":", maxsplit=1)
                if not value.strip().startswith('"Matt:'):
                    line = f'{prefix}: "Matt: {value.strip().strip(chr(34))}"'
            for source_name, namespaced_name in names.items():
                line = re.sub(
                    rf"(?<![A-Za-z0-9_-])/{re.escape(source_name)}(?![A-Za-z0-9_-])",
                    f"/{namespaced_name}",
                    line,
                )
                line = line.replace(f"skills/{source_name}", f"skills/{namespaced_name}")
                if "Skill tool" in line:
                    line = line.replace(f'"{source_name}"', f'"{namespaced_name}"')
                if "skill" in line.lower():
                    line = line.replace(f"`{source_name}`", f"`{namespaced_name}`")
            lines.append(line)

        normalized = "\n".join(lines)
        if normalized != contents:
            path.write_text(normalized, encoding="utf-8")


def recorded_sha(root: Path) -> str | None:
    notice = root / "THIRD_PARTY_NOTICES.md"
    if not notice.is_file():
        return None
    match = re.search(
        r"Upstream commit used for this build: `([0-9a-f]{40})`",
        notice.read_text(encoding="utf-8"),
    )
    return match.group(1) if match else None


def sync(ref: str, *, report: dict[str, object] | None = None) -> str:
    state = report if report is not None else {}
    state.update(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        upstream_ref=ref,
        previous_upstream_commit=recorded_sha(PLUGIN_ROOT),
        stage="resolve upstream",
    )
    sha = upstream_sha(ref)
    state.update(upstream_commit=sha, stage="download upstream")
    archive = fetch(f"https://github.com/{REPOSITORY}/archive/{sha}.tar.gz")

    # Stage on the same filesystem so the validated skill tree can be renamed.
    with tempfile.TemporaryDirectory(prefix=".sync-", dir=PLUGIN_ROOT) as temporary:
        state["stage"] = "generate package"
        upstream_root = extract_archive(archive, Path(temporary))
        manifest_path = upstream_root / ".claude-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        paths = selected_skill_paths(upstream_root, manifest)
        names = {
            PurePosixPath(raw_path).name: prefixed_skill_name(PurePosixPath(raw_path).name)
            for raw_path in paths
        }

        generated_root = Path(temporary) / "generated"
        skills_root = generated_root / "skills"
        skills_root.mkdir(parents=True)

        for raw_path in paths:
            source = upstream_root / PurePosixPath(raw_path.removeprefix("./"))
            if not (source / "SKILL.md").is_file():
                raise RuntimeError(f"selected skill is missing SKILL.md: {raw_path}")
            destination = skills_root / names[source.name]
            shutil.copytree(source, destination, symlinks=False)
            make_codex_compatible(destination)
            namespace_skill_tree(destination, names)

        state.update(stage="validate artifact labels", skill_count=len(paths))
        adaptations = apply_artifact_labels(skills_root)
        apply_artifact_labels(skills_root, check=True)
        state["adaptations"] = adaptations
        changed_sources = []
        for adaptation in adaptations:
            relative = str(adaptation["path"])
            previous = PLUGIN_ROOT / "skills" / relative
            if not previous.is_file() or strip_artifact_labels(
                relative, previous.read_text(encoding="utf-8")
            ) != strip_artifact_labels(
                relative, (skills_root / relative).read_text(encoding="utf-8")
            ):
                changed_sources.append(relative)
        state["changed_adaptation_sources"] = changed_sources

        shutil.copy2(upstream_root / "LICENSE", generated_root / "LICENSE")
        for relative in (".codex-plugin/plugin.json", "plugin.json"):
            manifest_path = PLUGIN_ROOT / relative
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            current_version = payload.get("version")
            if not isinstance(current_version, str):
                raise RuntimeError(f"manifest has no version: {manifest_path}")
            payload["version"] = version_for_sha(current_version, sha)
            destination = generated_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            write_json(destination, payload)

        (generated_root / "THIRD_PARTY_NOTICES.md").write_text(
            "# Third-party notices\n\n"
            "This package is an unofficial Codex adaptation of "
            "[Matt Pocock's skills repository](https://github.com/mattpocock/skills).\n\n"
            f"- Upstream ref: `{ref}`\n"
            f"- Upstream commit used for this build: `{sha}`\n"
            f"- Included content: {len(paths)} promoted and in-progress upstream skills\n"
            "- Excluded content: upstream's `misc/` and `deprecated/` buckets\n"
            f"- Codex skill namespace: every included skill is prefixed with `{SKILL_PREFIX}`\n"
            "- Codex adaptation: Claude-only `disable-model-invocation: true` metadata is normalized to `false`\n"
            "- Community adaptation: specs, tickets, and Wayfinder maps receive `kind:spec`, `kind:ticket`, and `kind:map` respectively; local Markdown records an equivalent Kind field\n"
            "- License: MIT, reproduced in [`LICENSE`](./LICENSE)\n\n"
            "The package is maintained independently. It is not affiliated with or endorsed by "
            "Matt Pocock, AI Hero, or OpenAI. Local metadata and synchronization code are "
            "provided by Lane Araujo under the MIT license.\n",
            encoding="utf-8",
        )

        state["stage"] = "publish generated package"
        installed_skills = PLUGIN_ROOT / "skills"
        backup = Path(temporary) / "previous-skills"
        if installed_skills.exists():
            installed_skills.replace(backup)
        try:
            skills_root.replace(installed_skills)
        except OSError:
            if backup.exists():
                backup.replace(installed_skills)
            raise
        for relative in (".codex-plugin/plugin.json", "plugin.json", "LICENSE", "THIRD_PARTY_NOTICES.md"):
            (generated_root / relative).replace(PLUGIN_ROOT / relative)

    state.update(status="success", stage="complete", finished_at=datetime.now(timezone.utc).isoformat())
    return sha


def write_report(report: dict[str, object], path: Path | None) -> None:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, report)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [
            "## Upstream skill sync",
            "",
            f"- Status: **{report['status']}**",
            f"- Stage: {report.get('stage', 'unknown')}",
            f"- Previous upstream commit: `{report.get('previous_upstream_commit') or 'none'}`",
            f"- Checked upstream commit: `{report.get('upstream_commit') or 'unresolved'}`",
            f"- Included skills: {report.get('skill_count', 'unknown')}",
        ]
        if report.get("error"):
            lines.extend(["", "```text", str(report["error"]), "```"])
        adaptations = report.get("adaptations", [])
        if adaptations:
            lines.extend(["", "| Validated file | Artifact kinds |", "| --- | --- |"])
            for entry in adaptations:
                lines.append(f"| `{entry['path']}` | {', '.join(entry['kinds'])} |")
        changed = report.get("changed_adaptation_sources", [])
        if changed:
            lines.extend(["", "Upstream content changed in adapted files:", ""])
            lines.extend(f"- `{relative}`" for relative in changed)
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default=DEFAULT_REF, help="upstream branch name (default: main)")
    parser.add_argument("--report", type=Path, help="write a JSON health report, including on failure")
    parser.add_argument("--check", action="store_true", help="validate the bundled artifact-label adaptations without syncing")
    args = parser.parse_args()
    if args.check:
        apply_artifact_labels(PLUGIN_ROOT / "skills", check=True)
        print("Artifact-label adaptations are valid.")
        return
    report: dict[str, object] = {}
    try:
        sha = sync(args.ref, report=report)
    except Exception as error:
        report.update(status="failure", error=str(error), finished_at=datetime.now(timezone.utc).isoformat())
        write_report(report, args.report)
        print(f"Sync failed during {report.get('stage', 'startup')}: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    write_report(report, args.report)
    print(f"Synchronized {REPOSITORY}@{args.ref} ({sha})")


if __name__ == "__main__":
    main()
