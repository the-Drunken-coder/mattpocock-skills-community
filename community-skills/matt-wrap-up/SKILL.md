---
name: matt-wrap-up
description: Close out a work session by verifying what it created, changed, or started across the repository, tracker, remote, and runtime environment. Use when the user wants to finish or nothing follows in the current session.
---

# Wrap up

Do not summarize from memory. Inspect the live state the session touched.

1. List branches, worktrees, files, processes, containers, issues, pull requests, comments, handoff files, and decisions created or changed by this session.
2. Check each against its intended end state on the filesystem, remote, tracker, and relevant service.
3. Sort each item as `landed`, `in flight`, `debris`, `decided but unrecorded`, or `out of scope`.
4. Report the evidence and propose one action per item. Do not delete, close, resolve, or rewrite anything without the user's confirmation.
5. End with one line that opens the next session and names the skill it should call, if another step remains.

Distinguish work waiting on another person or system from work the user still owns. Include the smallest useful command, link, or file path for each follow-up.
