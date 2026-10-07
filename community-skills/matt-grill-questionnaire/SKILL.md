---
name: matt-grill-questionnaire
description: Turn a set of independent decisions into a local HTML questionnaire with recommendations and a Markdown answer export. Use when the user wants to answer several known planning questions in one pass.
---

# Grill questionnaire

Use this as a batch interaction mode for decisions that are already visible and mostly independent. It does not replace `matt-grilling`: dependent decisions still need a normal grilling round after their prerequisites are answered.

## Procedure

1. Identify the current decision frontier. Include only questions the agent cannot answer from available evidence and that the user must decide.
2. For each question, write a short explanation, two to five concrete options, one recommended option with its reason, and an `Other` choice. Do not invent downstream questions whose answers depend on an earlier choice.
3. Create a standalone file named `grill-questionnaire-<slug>.html` in the workspace. It must work from `file://` with no server, account, analytics, or network request.
4. Give each question a choice control and optional rationale field. Include a clear “use recommendation” choice and a button that downloads `grill-questionnaire-<slug>-answers.md`.
5. Report both file paths and explain that the Markdown answer file is the durable input for the next planning step.

Keep the form accessible and readable. Preserve the recommendation and the user's selected answer in the export. If answers unlock new dependent decisions, return to ordinary grilling rather than guessing the whole future tree.
