---
name: matt-to-story-map
description: Turn a product vision into a durable story map with a north star, protagonist, journey backbone, thin slices, exemplars, and placement rules. Use when a team needs to ensure it is building the right thing.
---

# To story map

Create a stable product-level map before the backlog and technical plan become the only description of the work. This is about outcome and user journey, not implementation mechanism.

## Resolve the shape

Clarify the protagonist, the north-star outcome, the measurable signals, the journey backbone, the slicing direction, durable versus generated information, placement mechanics, and the rule that keeps the map honest. Ask one decision-critical question at a time when needed.

## Write the map

Create one durable Markdown artifact containing:

- A falsifiable north star with measures.
- One primary protagonist and any secondary personas.
- The protagonist's journey as ordered backbone columns.
- Thin end-to-end slices across the backbone.
- Named exemplars with executable or otherwise checkable twins where practical.
- Rules for placing future requests and keeping mechanism in ADRs, status in the tracker, and stories in issues.

Use the map as a placement test during triage. A request that fits nowhere may be off-mission or may reveal a missing part of the backbone. Do not turn the map into a second tracker, a specification, or a copy of the ADRs. Recommend `matt-to-spec` for a concrete feature once its place in the journey is clear.
