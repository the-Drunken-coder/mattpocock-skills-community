# Third-party notices

This package is an unofficial Codex adaptation of [Matt Pocock's skills repository](https://github.com/mattpocock/skills).

- Upstream ref: `main`
- Upstream commit used for this build: `2237a047bd95abfd1427df94f65165c39e24d3c1`
- Included content: 34 promoted and in-progress upstream skills
- Excluded content: upstream's `misc/` and `deprecated/` buckets
- Codex skill namespace: every included skill is prefixed with `matt-`
- Codex adaptation: Claude-only `disable-model-invocation: true` metadata is normalized to `false`
- Community adaptation: specs, tickets, and Wayfinder maps receive `kind:spec`, `kind:ticket`, and `kind:map` respectively; local Markdown records an equivalent Kind field
- License: MIT, reproduced in [`LICENSE`](./LICENSE)

The package is maintained independently. It is not affiliated with or endorsed by Matt Pocock, AI Hero, or OpenAI. Local metadata and synchronization code are provided by Lane Araujo under the MIT license.
