# Third-party notices

This package is an unofficial Codex adaptation of [Matt Pocock's skills repository](https://github.com/mattpocock/skills).

- Upstream ref: `main`
- Upstream commit used for this build: `f3fc5632f401156837ee3872f14fe33ccf1024ea`
- Included content: 34 promoted and in-progress upstream skills plus 9 community skills
- Excluded content: upstream's `misc/` and `deprecated/` buckets
- Codex skill namespace: every included skill is prefixed with `matt-`
- Codex adaptation: Claude-only `disable-model-invocation: true` metadata is normalized to `false`
- Community adaptation: specs, tickets, and Wayfinder maps receive `kind:spec`, `kind:ticket`, and `kind:map` respectively; local Markdown records an equivalent Kind field
- License: MIT, reproduced in [`LICENSE`](./LICENSE)

The package is maintained independently. It is not affiliated with or endorsed by Matt Pocock, AI Hero, or OpenAI. Local metadata and synchronization code are provided by Lane Araujo under the MIT license.
