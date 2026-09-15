# Matt Pocock skills for Codex

This is an unofficial Codex package containing the 25 engineering and productivity skills selected by Matt Pocock's upstream Claude Code plugin manifest. It is not affiliated with or endorsed by Matt Pocock, AI Hero, or OpenAI.

Every skill is namespaced with the `matt-` prefix, for example `/matt-code-review`, so these skills do not collide with other Codex skills.

The included skill files and `LICENSE` are copied from [mattpocock/skills](https://github.com/mattpocock/skills) under its MIT license. The package keeps its own Codex metadata and synchronization code so the upstream content can be reviewed separately.

Codex's plugin ingestion contract does not accept Claude Code's `disable-model-invocation: true` flag. The sync normalizes that flag to `false` and records the adaptation in `THIRD_PARTY_NOTICES.md`.

## Install locally

Place this directory in `~/plugins/mattpocock-skills-community`, add it to your personal marketplace, and install `mattpocock-skills-community`. The Codex plugin cache is a snapshot, so restart Codex after upgrading the marketplace entry or reinstalling the plugin.

## Update manually

From this directory, run:

```sh
python3 scripts/sync_upstream.py --ref main
```

The script reads the current upstream commit, copies only the promoted skills, updates both manifests with the short commit SHA, and records the full SHA in `THIRD_PARTY_NOTICES.md`.

The included GitHub Actions workflow runs this sync at 00:05 America/New_York each night and commits changes to the package's default branch. GitHub may delay scheduled jobs, and scheduled workflows only run when the repository's default branch is active.

## Scope

The package deliberately excludes upstream's `misc/`, `in-progress/`, and `deprecated/` buckets. Review upstream changes before enabling the nightly workflow on a public fork.
