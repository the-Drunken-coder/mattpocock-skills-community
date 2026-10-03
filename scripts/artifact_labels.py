"""Maintain the community's artifact-kind instructions after an upstream import."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

ARTIFACT_KINDS = ("kind:spec", "kind:ticket", "kind:map")
SETUP = "matt-setup-matt-pocock-skills"
TRACKER_KINDS = """## Artifact kinds

Apply exactly one artifact-kind label to each new artifact:

| Artifact | Label |
| --- | --- |
| Specification | `kind:spec` |
| Individual implementation or decision ticket | `kind:ticket` |
| Wayfinder planning map | `kind:map` |

Keep triage, category, and `wayfinder:*` labels alongside the artifact kind. Create a missing kind label using the tracker's native tools before publishing, then verify the label on the published artifact. If label creation is unavailable, report the missing label. Creating child tickets does not change their parent's kind.

For local Markdown, record `**Kind:** spec`, `**Kind:** ticket`, or `**Kind:** map` near the top of the corresponding file; retain its existing `Status:` and `Type:` fields.

"""


@dataclass(frozen=True)
class LabelPatch:
    path: str
    anchor: str
    addition: str
    kinds: tuple[str, ...]
    required: tuple[str, ...] = ()


PATCHES = (
    LabelPatch(
        "matt-to-spec/SKILL.md",
        "<spec-template>\n",
        """### Artifact kind

Publish the spec with `kind:spec` alongside its triage label. Create the kind label if missing on the configured tracker, then verify it on the published spec. For local Markdown, add `**Kind:** spec` near the top of the spec file.

""",
        ("kind:spec",),
        ("publish it to the project issue tracker", "</spec-template>"),
    ),
    LabelPatch(
        "matt-to-tickets/SKILL.md",
        "<local-ticket-template>\n",
        """### Artifact kind

Publish each ticket with `kind:ticket` alongside its triage label. Create the kind label if missing on the configured tracker, then verify it on each published ticket. Keep the parent's existing kind and other labels. For local Markdown, use the Kind field in the ticket template below.

""",
        ("kind:ticket",),
        ("### 5. Publish the tickets to the configured tracker", "</issue-template>"),
    ),
    LabelPatch(
        "matt-to-tickets/SKILL.md",
        "**Status:** ready-for-agent\n",
        "**Kind:** ticket\n\n",
        ("kind:ticket",),
    ),
    LabelPatch(
        "matt-wayfinder/SKILL.md",
        "### The map body\n",
        """### Artifact kinds

Publish the map with `kind:map` and every child decision ticket with `kind:ticket`. Retain `wayfinder:map`, `wayfinder:<type>`, and other existing labels. Create missing kind labels using the configured tracker's native tools, then verify them on each new artifact. Creating tickets does not change their parent's kind.

For local Markdown, add `**Kind:** map` near the top of the map file and `**Kind:** ticket` near the top of each child file, retaining existing Type and Status fields.

""",
        ("kind:map", "kind:ticket"),
        ("### Tickets", "wayfinder:<type>", "### Chart the map"),
    ),
    LabelPatch(
        f"{SETUP}/SKILL.md",
        "### 3. Confirm and edit\n",
        """### Artifact-kind configuration

Include the artifact-kind conventions from the tracker seed template in `docs/agents/issue-tracker.md`. For an "other" tracker, include the same three kinds: `kind:spec` for specifications, `kind:ticket` for individual implementation or decision tickets, and `kind:map` for Wayfinder maps. Keep the existing triage vocabulary. Local Markdown records the equivalent `**Kind:** spec`, `**Kind:** ticket`, or `**Kind:** map` field. Include these conventions in the draft shown in step 3.

""",
        ARTIFACT_KINDS,
        ("docs/agents/issue-tracker.md", "### 4. Write"),
    ),
    *(
        LabelPatch(
            f"{SETUP}/issue-tracker-{tracker}.md",
            "## Conventions\n",
            TRACKER_KINDS,
            ARTIFACT_KINDS,
            ("## Wayfinding operations",),
        )
        for tracker in ("github", "gitlab", "local")
    ),
)


class ArtifactLabelError(RuntimeError):
    pass


def strip_artifact_labels(path: str, contents: str) -> str:
    """Recover the imported text, also detecting duplicated adaptations."""
    for patch in PATCHES:
        if patch.path != path:
            continue
        count = contents.count(patch.addition)
        if count > 1:
            raise ArtifactLabelError(f"artifact labels: duplicated addition in {path}")
        if count:
            contents = contents.replace(patch.addition, "", 1)
    return contents


def apply_artifact_labels(
    skills_root: Path, *, check: bool = False
) -> list[dict[str, object]]:
    """Preflight every contract before writing; check mode is read-only."""
    planned: dict[str, str] = {}
    report: list[dict[str, object]] = []
    for relative in dict.fromkeys(patch.path for patch in PATCHES):
        path = skills_root / relative
        if not path.is_file():
            raise ArtifactLabelError(
                f"artifact labels: required upstream file missing: {relative}"
            )
        contents = path.read_text(encoding="utf-8")
        source = strip_artifact_labels(relative, contents)
        if re.search(r"\bkind:[a-z][a-z-]*\b", source):
            raise ArtifactLabelError(
                f"artifact labels: upstream now defines kind labels in {relative}; review the adaptation"
            )
        generated = source
        kinds: set[str] = set()
        for patch in PATCHES:
            if patch.path != relative:
                continue
            count = source.count(patch.anchor)
            if count != 1:
                raise ArtifactLabelError(
                    f"artifact labels: expected one insertion point {patch.anchor.strip()!r} "
                    f"in {relative}, found {count}; review upstream changes"
                )
            for required in patch.required:
                if required not in source:
                    raise ArtifactLabelError(
                        f"artifact labels: required upstream contract {required!r} missing in {relative}"
                    )
            generated = generated.replace(
                patch.anchor, patch.addition + patch.anchor, 1
            )
            kinds.update(patch.kinds)
        if check and generated != contents:
            raise ArtifactLabelError(
                f"artifact labels: missing or modified adaptation in {relative}"
            )
        if generated != contents:
            planned[relative] = generated
        report.append(
            {
                "path": relative,
                "kinds": sorted(kinds),
                "imported_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "generated_sha256": hashlib.sha256(generated.encode()).hexdigest(),
            }
        )

    for relative, contents in planned.items():
        (skills_root / relative).write_text(contents, encoding="utf-8")
    return report
