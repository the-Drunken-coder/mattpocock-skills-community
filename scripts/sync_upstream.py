#!/usr/bin/env python3
"""Synchronize the promoted skills from Matt Pocock's upstream repository."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from urllib.request import Request, urlopen


REPOSITORY = "mattpocock/skills"
DEFAULT_REF = "main"
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
    payload = json.loads(
        fetch(f"https://api.github.com/repos/{REPOSITORY}/commits/{quote(ref, safe='')}")
    )
    sha = payload.get("sha")
    if not isinstance(sha, str) or len(sha) != 40:
        raise RuntimeError("GitHub did not return a full upstream commit SHA")
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


def promoted_skill_paths(manifest: dict[str, object]) -> list[str]:
    if manifest.get("license") != "MIT":
        raise RuntimeError("upstream plugin manifest is no longer MIT-licensed")
    raw_paths = manifest.get("skills")
    if not isinstance(raw_paths, list) or not all(isinstance(path, str) for path in raw_paths):
        raise RuntimeError("upstream plugin manifest has no valid skills list")

    paths = list(raw_paths)
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


def sync(ref: str) -> str:
    sha = upstream_sha(ref)
    archive = fetch(f"https://github.com/{REPOSITORY}/archive/refs/heads/{quote(ref, safe='')}.tar.gz")

    with tempfile.TemporaryDirectory(prefix="mattpocock-skills-") as temporary:
        upstream_root = extract_archive(archive, Path(temporary))
        manifest_path = upstream_root / ".claude-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        paths = promoted_skill_paths(manifest)

        skills_root = PLUGIN_ROOT / "skills"
        if skills_root.exists():
            shutil.rmtree(skills_root)
        skills_root.mkdir(parents=True)

        for raw_path in paths:
            source = upstream_root / PurePosixPath(raw_path.removeprefix("./"))
            if not (source / "SKILL.md").is_file():
                raise RuntimeError(f"promoted skill is missing SKILL.md: {raw_path}")
            destination = skills_root / source.name
            shutil.copytree(source, destination, symlinks=False)
            make_codex_compatible(destination)

        shutil.copy2(upstream_root / "LICENSE", PLUGIN_ROOT / "LICENSE")

    for manifest_path in (
        PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
        PLUGIN_ROOT / "plugin.json",
    ):
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        current_version = payload.get("version")
        if not isinstance(current_version, str):
            raise RuntimeError(f"manifest has no version: {manifest_path}")
        payload["version"] = version_for_sha(current_version, sha)
        write_json(manifest_path, payload)

    (PLUGIN_ROOT / "THIRD_PARTY_NOTICES.md").write_text(
        "# Third-party notices\n\n"
        "This package is an unofficial Codex adaptation of "
        "[Matt Pocock's skills repository](https://github.com/mattpocock/skills).\n\n"
        f"- Upstream ref: `{ref}`\n"
        f"- Upstream commit used for this build: `{sha}`\n"
        f"- Included content: the {len(paths)} skills listed by upstream's promoted Claude Code plugin manifest\n"
        "- Excluded content: upstream's `misc/`, `in-progress/`, and `deprecated/` buckets\n"
        "- Codex adaptation: Claude-only `disable-model-invocation: true` metadata is normalized to `false`\n"
        "- License: MIT, reproduced in [`LICENSE`](./LICENSE)\n\n"
        "The package is maintained independently. It is not affiliated with or endorsed by "
        "Matt Pocock, AI Hero, or OpenAI. Local metadata and synchronization code are "
        "provided by Lane Araujo under the MIT license.\n",
        encoding="utf-8",
    )
    return sha


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default=DEFAULT_REF, help="upstream branch name (default: main)")
    args = parser.parse_args()
    sha = sync(args.ref)
    print(f"Synchronized {REPOSITORY}@{args.ref} ({sha})")


if __name__ == "__main__":
    main()
