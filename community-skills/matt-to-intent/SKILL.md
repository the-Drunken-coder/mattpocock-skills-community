---
name: matt-to-intent
description: Clarify the outcome, user, motivation, and success signal behind an idea before turning it into a specification. Use when a request is vague, solution-led, or may be solving the wrong problem.
---

# To intent

Turn a raw idea into a compact statement of the problem worth solving. This is a product-level on-ramp, not a technical design exercise.

## Work through these questions

- Who has the problem, and in what situation?
- What are they trying to accomplish?
- What happens today, and what is painful or expensive about it?
- What outcome would count as meaningfully better?
- How would we observe or measure that outcome?
- What is explicitly out of scope?
- Which assumptions would make the idea unnecessary or change its shape?

Use evidence already present in the conversation. Ask one decision-critical question at a time when the answer cannot be inferred. Attach a recommended answer when a sensible default exists, and let the user correct it.

## Output

End with an intent brief containing: the person, situation, problem, desired outcome, success signal, constraints, non-goals, and unresolved risks. Do not turn it into a feature list or implementation plan. When the intent is stable, recommend `matt-to-spec` as the next step.
