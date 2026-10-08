---
name: commit-review
description: Review the exact pending Git changes, summarize what changed and flag concrete possible bugs before creating a Conventional Commit. Use this skill whenever the user asks to commit, make a commit, prepare a commit message, or review changes before committing. Report in Ukrainian; create the commit only after presenting the report and receiving explicit approval.
allowed-tools: "Read, Grep, Glob, Agent, Bash(git status:*), Bash(git diff:*), Bash(git branch:*), Bash(git rev-parse:*), Bash(git log:*), Bash(git ls-files:*), Bash(git check-ignore:*), Bash(git show:*), Bash(git add:*), Bash(git commit:*), Bash(uv run pytest:*), Bash(pytest:*)"
disable-model-invocation: true
---

# Review changes and create a commit

Use this skill when a user wants a Git commit or asks for a commit message. The point is to summarize and review only the change that would enter this commit, then let the user decide before the repository is changed by the commit.

## Git safety protocol

Apply these safeguards throughout the workflow; when in doubt, stop and ask rather than risk losing or exposing work.

1. **Disallow dangerous Git operations.** Never run `git push`, `git reset`, `git clean`, `git rebase`, `git commit --amend`, or commands that switch branches or discard/rewrite work. Do not run them as part of this skill even if requested; explain that the operation is outside its scope. The skill may create only a new local commit after approval.
2. **Require approval for the exact commit.** Before staging or committing, show the review, exact file scope, and exact commit message, then ask for explicit approval. A general request to “commit” is not approval of the reviewed result. If the scope, message, or working tree changes, present the updated proposal and ask again.
3. **Inspect and constrain the staging scope.** Review `git status`, staged and unstaged diffs, and the contents of untracked files before deciding the scope. Include only the approved files; never stage blindly with `git add -A`. Do not include ignored files or changes outside this repository and the approved scope.
4. **Protect secrets and local data.** Do not stage likely credentials, tokens, private keys, `.env` files, local databases, or generated/local-only data. Do not print secret values. If a candidate file may contain sensitive data, exclude it and ask the user before proceeding.
5. **Stop on unsafe or ambiguous repository state.** Do not stage or commit when conflicts exist, a merge/rebase/cherry-pick is in progress, `HEAD` is missing, or the branch/repository state is unclear. Do not resolve conflicts, discard changes, or try to repair the state automatically; explain the issue and ask the user what to do.

## Workflow

1. **Inspect the repository state before acting.** Run `git status --short`, check the current branch, and inspect staged and unstaged diffs. Compare against `HEAD` and inspect relevant untracked, non-ignored files; do not assume the staged diff is the full change. Never include ignored files. You need this diff for the documentation gate below, so gather it first.
2. **Documentation freshness gate — always do this next, before the full commit review.** Dispatch the `docs-sync-updater` subagent (Agent tool, `subagent_type: docs-sync-updater`) in audit mode, giving it the diff/untracked files gathered in step 1 (changed code and configuration, and the names of any documentation files touched in the same diff). It reads the current doc/implementation text itself and returns findings as exact, re-appliable edits (file, old text, new text, reason) or reports that documentation is current. Do not start the full change review, run tests, prepare the commit report, or stage anything until this gate is resolved.
   - If the subagent reports a material mismatch, pause and ask the user in Ukrainian whether they want the affected documentation updated. Name the mismatch and document(s) from its findings, but do not continue the commit-review workflow until they answer. Collect all documentation changes to avoid interrupting the user several times.
   - If they say yes, dispatch `docs-sync-updater` again in apply mode with exactly the approved findings (passed verbatim, including `old_string`/`new_string`), then re-run step 1's inspection since the tree changed. Their approval to update docs is **not** approval to commit; the final commit scope/message still needs the separate approval below. Re-establish the full scope and review it afresh against the new diff.
   - If they say no, continue only after recording the stale docs and explaining that they will remain outdated; do not edit them. If the subagent reports documentation is current, or no documentation is affected by the code/config changes, proceed without asking an unnecessary question.

   The subagent carries its own documentation-dependency map for this repository (`.claude/agents/docs-sync-updater.md`) and falls back to discovering a repo's docs itself if that map doesn't apply.
3. **Establish the exact commit scope.** By default, include all current non-ignored changes in the working tree, including untracked files. If there is no `HEAD`, a merge/rebase/cherry-pick is in progress, conflicts exist, or the requested scope is ambiguous, stop and ask how to proceed. Do not include likely secrets, credentials, local environment files, generated databases, or other clearly sensitive/local-only data; identify these and ask the user rather than staging them. If the user explicitly narrows the scope, follow that instead.
4. **Review only the proposed change.** Read the changed code and nearby context needed to understand it. Look for concrete correctness regressions, edge cases, unsafe assumptions, and missing/error-handling paths introduced by this change. Separate confirmed defects from risks that need verification. Do not report unrelated pre-existing issues or invent speculative bugs. For each finding, state the affected file/area, scenario, and likely impact; if no concrete issue is found, say so.
5. **Run relevant checks when practical.** Follow repository instructions (such as `CLAUDE.md`) and choose targeted tests or checks based on the changed files. Avoid expensive or unrelated checks. Report exactly what was run and whether it passed, failed, or was skipped; do not imply tests passed if they were not run. A failed check is not a reason to hide the result or to create a commit without the user's decision.
6. **Prepare the report and message before any commit-side effect.** Use the format below. Write a concise Conventional Commit message in English (`type(scope): imperative summary` when a useful scope is clear; otherwise `type: imperative summary`). Choose `feat`, `fix`, `refactor`, `test`, `docs`, `build`, `ci`, `perf`, or `chore` according to the primary change. Do not claim the code is bug-free.
7. **Ask for explicit approval.** Present the report, exact file scope, and exact commit message, then ask whether to create the commit. Do not run `git add`, `git commit`, amend a commit, or otherwise change the index before the user approves. The user's initial request to “commit” is not approval of the reviewed result. Approval to update documentation at step 2 is not commit approval.
8. **After approval only, commit the stated scope.** Re-check `git status` and the diff so changes made since the report are not silently included. If the working tree changed, including because documentation was updated, revise the review/report and ask for approval again. Stage only the approved scope; for the default all-changes scope use `git add -A` only after checking the candidate files for sensitive/local-only data. Then create a new commit with the proposed message. Never amend, rebase, push, or discard changes. Do not push under any circumstances as part of this skill; publishing the commit is outside its scope. Verify the result with `git status --short` and `git log -1 --oneline`, then report the commit hash/message and outcome. If commit creation fails, report the failure and leave the changes intact.

## Report format

Respond in Ukrainian, briefly:

```text
Зміни: <1–3 bullets describing only this proposed change>
Можливі баги: <concrete change-related findings, or “Конкретних проблем не виявлено”>
Перевірки: <commands and outcomes, or “Не запускались: <reason>”>
Обсяг: <files/categories to be committed; mention excluded sensitive/local-only files>
Commit message: `<proposed message>`
Створити коміт із цим обсягом і повідомленням?
```

Keep the summary short and useful. Do not pad it with generic praise or a long code walkthrough. If there are high-severity findings or failing checks, make them prominent; still ask the user what they want to do instead of silently committing.
