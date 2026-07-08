# Skill: Safe Git Worktree Operations

## When to Use

Before any `git merge`, `git rebase`, `git checkout`, or `git pull` in a multi-worktree repository.

## Core Rule

Always know which branch you are on before merging.

```
git branch -v       # Shows + for worktree branches
git worktree list   # Shows current worktree location
git status          # Check for MERGE_HEAD
```

## Pre-Merge Checklist

Before `git merge <branch>`:

1. `git branch -v` - Confirm current branch
2. `git worktree list` - Confirm no MERGE_HEAD exists
3. `git status --short` - Confirm working tree is clean

If MERGE_HEAD exists: resolve or `git merge --abort` first.

## Why This Matters

In git worktree setups, the main branch (e.g., `master`) cannot be checked out from the main worktree directory - it IS that branch. Merging from a worktree merges into the worktree branch, not master.

Consequences of wrong-branch merge:
- Merge commits land on feature branches instead of master
- AGENT_LOG.md gets add/add conflicts when branches are merged into master
- Untracked files in the main directory may be accidentally deleted

## AGENT_LOG.md Conflicts

Both T02 and T03 subagents modified AGENT_LOG.md. Merging both into master creates a conflict in the "current status" and "todo" sections.

Prevention: Do not write task logs directly to AGENT_LOG.md in subagent worktrees. Let the parent agent append after both merges.

Resolution: Keep both task log sections, remove conflict markers, merge status/todo at bottom.

## Shared File Conflicts (add/add)

If two branches both modify the same file (e.g., src/phycode/errors.py), git creates an add/add conflict.

Prevention: Design shared files first. Tasks that define exceptions should add subclasses rather than modifying existing code.

## Untracked Files and Merge

Untracked files are NOT protected by git merge. A deleted untracked file that was never committed is permanently lost.

Prevention: Before destructive operations, verify:
```
git ls-files --stage <path>   # Nothing = untracked
```

## Recovery Procedures

Merged in wrong branch (committed):
```
git reset --hard <previous-commit>
git checkout <correct-branch>
git merge <branch>
```

Merged in wrong branch (not committed):
```
git merge --abort
```

Deleted untracked file (was in a commit):
```
git show <commit>:<path> > <path>
```

AGENT_LOG.md conflict: Keep both task log sections, remove markers, merge status/todo at bottom.
