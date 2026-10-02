# Matt Pocock skills for Codex

[![Sync upstream skills](https://github.com/the-Drunken-coder/mattpocock-skills-community/actions/workflows/sync-upstream.yml/badge.svg)](https://github.com/the-Drunken-coder/mattpocock-skills-community/actions/workflows/sync-upstream.yml)
[![Monitor upstream sync](https://github.com/the-Drunken-coder/mattpocock-skills-community/actions/workflows/monitor-sync.yml/badge.svg)](https://github.com/the-Drunken-coder/mattpocock-skills-community/actions/workflows/monitor-sync.yml)
[![Validate plugin](https://github.com/the-Drunken-coder/mattpocock-skills-community/actions/workflows/validate.yml/badge.svg)](https://github.com/the-Drunken-coder/mattpocock-skills-community/actions/workflows/validate.yml)

This is an unofficial Codex package containing the engineering and productivity skills selected by Matt Pocock's upstream Claude Code plugin manifest, plus every skill in upstream's `skills/in-progress/` directory. It is not affiliated with or endorsed by Matt Pocock, AI Hero, or OpenAI.

Every skill is namespaced with the `matt-` prefix, for example `/matt-code-review`, so these skills do not collide with other Codex skills.

The included skill files and `LICENSE` are copied from [mattpocock/skills](https://github.com/mattpocock/skills) under its MIT license. The package keeps its own Codex metadata, synchronization code, and artifact-label adaptation so the upstream content and community changes can be reviewed separately.

Codex's plugin ingestion contract does not accept Claude Code's `disable-model-invocation: true` flag. The sync normalizes that flag to `false` and records the adaptation in `THIRD_PARTY_NOTICES.md`.

## Install locally

Place this directory in `~/plugins/mattpocock-skills-community`, add it to your personal marketplace, and install `mattpocock-skills-community`. The Codex plugin cache is a snapshot, so restart Codex after upgrading the marketplace entry or reinstalling the plugin.

## Update manually

From this directory, run:

```sh
python3 scripts/sync_upstream.py --ref main --report .sync-report.json
```

The script reads the current upstream commit, copies the promoted and in-progress skills, updates both manifests with the short commit SHA, and records the full SHA in `THIRD_PARTY_NOTICES.md`.

GitHub cannot directly trigger this repository's workflow when another repository changes. The included workflow therefore polls Matt Pocock's `main` branch every 15 minutes and commits changes when its generated package differs. GitHub may delay scheduled jobs, and scheduled workflows only run when the repository's default branch is active.

## Artifact kinds

The community adaptation adds one label identifying what each new issue represents:

| Label | Artifact |
| --- | --- |
| `kind:spec` | Specification published by `/matt-to-spec` |
| `kind:ticket` | Individual ticket published by `/matt-to-tickets` or Wayfinder |
| `kind:map` | Parent planning map published by `/matt-wayfinder` |

These labels accompany the existing triage, category, and `wayfinder:*` labels. Local Markdown uses an equivalent `**Kind:** spec`, `**Kind:** ticket`, or `**Kind:** map` field. Setup includes these conventions in the tracker configuration; the publishing instructions also work for repos configured before this adaptation. Publishing skills create missing kind labels and verify the kind on newly created artifacts. Existing parent issues are not relabeled when creating children.

[`scripts/artifact_labels.py`](./scripts/artifact_labels.py) owns the additions. Each sync imports upstream afresh, applies Codex metadata and namespacing, then reapplies this adaptation. Upstream instructions are retained around the additions. Do not edit generated files under `skills/` to maintain a customization; a later sync replaces them.

## Sync monitoring

Each sync stages and validates the complete package before replacing the bundled skills. A removed skill, missing or ambiguous insertion point, changed publishing contract, or new upstream `kind:` vocabulary stops the sync before publication. Generation and validation failures preserve the previous package. Publication errors roll back both the skills tree and all metadata files, including restoring the absence of files that did not previously exist. If rollback itself fails, the failure report identifies retained recovery backups.

The sync run summary and downloadable `upstream-sync-report` artifact include the previous and checked upstream commits, skill count, validated kind assignments, hashes of imported and adapted files, and any changed upstream content in the adapted files. Failures include the stage and error. Reports are retained for 14 days, and the run summary also records the publication result.

`Monitor upstream sync` checks hourly. It fails if the latest completed default-branch sync failed or was cancelled, the sync workflow is disabled, no successful sync is available, or the last success is more than two hours old. It retains an `upstream-sync-health` report with links to the last successful and latest completed runs. Both schedules depend on GitHub Actions; this watchdog cannot detect a complete Actions scheduling outage while it is also stopped.

For notifications, watch this repository and enable GitHub Actions notifications, optionally selecting **Only notify for failed workflows**, in your [GitHub notification settings](https://github.com/settings/notifications). See [GitHub's Actions notification instructions](https://docs.github.com/en/subscriptions-and-notifications/how-tos/managing-github-actions-notifications). Notification delivery depends on your personal settings; the workflows always expose failures and reports in Actions.

Pull requests and pushes to `main` also validate the bundled adaptation and run the sync and monitoring tests. To check locally without downloading upstream:

```sh
python3 scripts/sync_upstream.py --check
python3 -m unittest discover -s tests -v
```

## Scope

The package deliberately excludes upstream's `misc/` and `deprecated/` buckets. In-progress skills can change or disappear without notice, so review automated updates on the package's default branch.
