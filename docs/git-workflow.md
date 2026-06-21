# Git workflow & survival guide

A practical, repo-specific reference for working in `monitoring`. Written for someone who can
copy/paste `add`/`commit`/`push` but wants to actually understand branches, undo mistakes, and read
history. Examples use this repo's real files.

> **Golden rule:** git almost never *loses* committed work. Once you've `commit`-ed something, it's
> recoverable (see [Undo cheatsheet](#undo-cheatsheet)). So: **commit early, commit often.** A commit
> is a save point, not a publication.

---

## 1. The mental model — three places your work lives

```
   working tree            staging area (the "index")        repository (history)
   the files you edit  ──►  what the next commit will save ──►  permanent save points
        (messy)                  (you choose what goes in)          (recoverable)

      git add <file>  ───────────►   git commit -m "..."  ───────────►
```

- **Working tree** — your actual files on disk, as you edit them.
- **Staging area** — a holding pen. `git add` puts a file's current state into it. This lets you
  commit *some* changes and not others.
- **Repository** — the chain of commits (history). `git commit` takes whatever is staged and writes
  it as one permanent (recoverable) save point.
- **Remote** (`origin` on GitHub) — a copy of the history on a server. `git push` sends your commits
  up; `git pull` brings others' commits down.

A **commit** = a snapshot + a message + a parent (the commit before it). The chain of parents *is* the
history.

A **branch** = just a movable label pointing at a commit. `main` is one label; `chore/restructure-safety`
is another. "Switching branches" moves your working tree to whatever that label points at. Branches are
cheap — they're how you keep risky work away from `main` until it's proven.

---

## 2. The daily loop

```bash
git status                      # what's changed? what's staged? what branch am I on?
git diff                        # show the unstaged changes (what you'd lose if you discarded)
git add path/to/file.py         # stage a specific file (preferred over `git add .`)
git diff --staged               # review exactly what the commit will contain
git commit -m "feat(unde): ..." # save it
git push                        # send commits to GitHub (only when you want to share)
```

Run `git status` constantly. It's free and it tells you exactly where you are. When unsure, `status`.

### Commit message convention (already used in this repo)

`<type>(<scope>): <imperative summary>` — look at `git log --oneline` to see the house style:

```
feat(unde): header-driven invoice loader + May candidate-list generator
docs(unde): outstanding-flags register + May accountant handoff
chore: delete exposed _archive dump; ignore _archive/ wholesale
```

- **type**: `feat` (new capability), `fix` (bug), `docs`, `chore` (housekeeping), `test`, `skill`.
- **scope**: the client or area (`unde`, `farada`, `model`, `restructure`).
- **summary**: imperative ("add", not "added"), one line, no full stop.

**One logical change per commit.** Tracking the `unde` client and tracking some `farada` scratch
scripts are two different stories → two commits, even if both are happening today.

---

## 3. Branches — why we're on `chore/restructure-safety`

We do structural/risky work on a branch *off* `main`, never directly on `main`. That way `main` always
stays green and shippable, and the branch can be reviewed (or thrown away) as a unit.

```bash
git branch                          # list local branches; * marks the current one
git switch main                     # move to main
git switch -c chore/my-thing        # create a new branch AND switch to it (off current branch)
git switch chore/restructure-safety # hop back
```

**Branch naming** (house style): `<type>/<short-dash-name>` — `chore/restructure-safety`,
`feat/farada-onboarding-f1-f2`, `cupffee-march-text`.

When a branch's work is done and green, it merges back to `main` (via a PR on GitHub, or a local
`git switch main && git merge chore/...`). Until then, it's a safe sandbox.

---

## 4. Undo cheatsheet

The four mistakes you'll actually hit, and the exact recovery. Match the situation to the row.

| Situation | What you want | Command |
|---|---|---|
| Staged a file you didn't mean to | Unstage it (keep the edits) | `git restore --staged path` |
| Edited a file, want to throw the edit away | Discard working-tree changes | `git restore path`  ⚠️ *this loses uncommitted edits* |
| Just committed, message is wrong/typo'd | Reword the last commit | `git commit --amend -m "better message"` |
| Just committed, forgot to include a file | Add it into the last commit | `git add forgotten.py && git commit --amend --no-edit` |
| Committed something wrong, already pushed | Make a *new* commit that undoes it | `git revert <commit-hash>` |
| "I think I lost a commit / branch" | Find it — git remembers everything | `git reflog`  (then `git switch -c rescue <hash>`) |

⚠️ **The only commands that can lose work** are `git restore <path>` (discards *uncommitted* edits) and
`git reset --hard` (avoid it while learning). Anything already committed is safe — `git reflog` lists
every commit your HEAD has pointed at, even "deleted" ones, for ~90 days.

**`amend` vs `revert`:** `amend` *rewrites* the last commit — only safe **before** you've pushed it.
Once pushed and shared, don't rewrite; use `revert` to add an undo commit on top.

---

## 5. Reading history — "what changed and why?"

```bash
git log --oneline -15              # compact recent history (hash + summary)
git log --oneline -- clients/unde  # history of just one path
git show <hash>                    # full diff + message of one commit
git show <hash> --stat             # just the files a commit touched
git diff main...HEAD --stat        # everything this branch changed vs main
git blame path/to/file.py          # who last changed each line, and in which commit
```

Workflow when a number/line looks wrong: `git log --oneline -- <file>` to find the commit that touched
it → `git show <hash>` to read the change and its message. The message is *why*; the diff is *what*.

---

## 6. Our collaboration contract (you + Claude)

- **You drive git during the Phase-0 learning reps** (R1–R3). Run commands via `! <cmd>` in the prompt
  so the output appears here and Claude can coach the next step.
- **Claude does the file work** (writing tests/docs, deleting ghosts) and tells you when a logical
  chunk is ready to commit, suggesting the message — but you run the commit.
- **Branch per workstream.** Phase-0 lives on `chore/restructure-safety`.
- **Commit cadence:** one logical change per commit; commit when a step is green (`uv run pytest -q`),
  not at the end of the day.
- After the learning reps, Claude may commit routine changes directly; anything risky still gets a
  branch + your review.

---

## Quick reference card

```
status / diff           where am I, what changed
add <path>              stage a specific file
diff --staged           review what the commit will save
commit -m "type(scope): summary"
push                    share to GitHub
switch <branch> / switch -c <new>
restore --staged <p>    unstage (keep edits)
restore <p>             discard edits   ⚠ loses uncommitted work
commit --amend          fix the last commit (only before push)
revert <hash>           undo a pushed commit (safe)
reflog                  find "lost" commits
log --oneline / show <hash> / blame <p>
```
