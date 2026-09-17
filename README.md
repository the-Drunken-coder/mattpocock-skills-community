# Matt Pocock skills for Codex

This is an unofficial Codex package containing the engineering and productivity skills selected by Matt Pocock's upstream Claude Code plugin manifest, plus every skill in upstream's `skills/in-progress/` directory. It is not affiliated with or endorsed by Matt Pocock, AI Hero, or OpenAI.

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

The script reads the current upstream commit, copies the promoted and in-progress skills, updates both manifests with the short commit SHA, and records the full SHA in `THIRD_PARTY_NOTICES.md`.

GitHub cannot directly trigger this repository's workflow when another repository changes. The included workflow therefore polls Matt Pocock's `main` branch every 15 minutes and commits changes when its generated package differs. GitHub may delay scheduled jobs, and scheduled workflows only run when the repository's default branch is active.

## Scope

The package deliberately excludes upstream's `misc/` and `deprecated/` buckets. In-progress skills can change or disappear without notice, so review automated updates on the package's default branch.
