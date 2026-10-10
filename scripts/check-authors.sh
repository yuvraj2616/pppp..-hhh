#!/usr/bin/env bash
# Fails if any commit author or Co-authored-by email is not one of the three participant identities.
#
# Usage: scripts/check-authors.sh [git-log revision args]     (default: origin/dev..HEAD)
#   scripts/check-authors.sh                    # your branch vs dev
#   scripts/check-authors.sh main..dev          # what a release PR would bring
# Allowed emails come from $ALLOWED_AUTHORS (CI repo variable) or
# `git config hackathon.allowedAuthors` (set by scripts/setup-identity.sh).
set -uo pipefail

allowed="${ALLOWED_AUTHORS:-$(git config --get hackathon.allowedAuthors 2>/dev/null || true)}"
if [ -z "$allowed" ]; then
  echo "check-authors: no allowed authors set. In CI set the ALLOWED_AUTHORS repo variable;"
  echo "locally run scripts/setup-identity.sh <rahul|hritik|pratham>."
  exit 1
fi
if [ $# -eq 0 ]; then set -- origin/dev..HEAD; fi

norm() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]'; }
allowed_list=",$(norm "$allowed"),"
is_allowed() { case "$allowed_list" in *",$(norm "$1"),"*) return 0 ;; *) return 1 ;; esac; }

bad=0
count=0
while IFS='|' read -r sha email; do
  [ -z "$sha" ] && continue
  count=$((count + 1))
  if ! is_allowed "$email"; then
    echo "BLOCKED ${sha:0:8}: author <$email> is not a participant identity"
    bad=1
  fi
  while IFS= read -r line; do
    co="$(printf '%s' "$line" | sed -n 's/.*<\([^>]*\)>.*/\1/p')"
    [ -z "$co" ] && continue
    if ! is_allowed "$co"; then
      echo "BLOCKED ${sha:0:8}: co-author <$co> is not a participant identity"
      bad=1
    fi
  done < <(git log -1 --format=%B "$sha" | grep -i '^co-authored-by:' || true)
done < <(git log --format='%H|%ae' "$@")

if [ "$bad" -ne 0 ]; then
  echo
  echo "Fix before pushing (see team/GIT_COMMANDS.md, 'Wrong author'):"
  echo "  last commit only : git commit --amend --reset-author --no-edit"
  echo "  whole branch     : git rebase origin/dev --exec 'git commit --amend --reset-author --no-edit'"
  echo "  AI co-author line: remove the Co-authored-by line with git commit --amend"
  exit 1
fi
echo "check-authors: $count commit(s) OK"
