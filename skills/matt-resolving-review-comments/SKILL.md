---
name: matt-resolving-review-comments
description: Evaluate pull-request review comments against the code, specification, and standards, then work only the comments that are justified. Use when handling feedback on a pull request you authored.
---

# Resolving review comments

A review comment is a claim, not an instruction. Verify it before changing the code.

## Workflow

1. Fetch every review surface, including inline threads, review summaries, automated findings, and general comments.
2. Read the originating ticket, specification, ADRs, coding standards, and affected code.
3. Collapse repeated comments into one claim and classify each as `fix`, `reject`, `defer`, or `ask`.
4. Present the verdicts before making changes when the decision affects behavior or the relationship with a reviewer.
5. Implement justified fixes in focused commits, preserving the original intent. Add or update regression coverage.
6. Run the relevant checks, reply to every comment with the result, and resolve only threads that were actually addressed.

The agent may verify claims and implement approved fixes. The user owns overruling a reviewer, accepting a behavior change, or speaking for the team. Never turn a correct diff into a larger, less correct one merely to satisfy an unverified suggestion.
