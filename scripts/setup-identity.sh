#!/usr/bin/env bash
# Run once per machine, inside the cloned repo:  ./scripts/setup-identity.sh rahul|hritik|pratham
# Sets this clone's commit identity (repo-local only, your other projects are untouched),
# turns on the pre-push author check and rebase-on-pull.
set -euo pipefail

who="${1:-}"
case "$who" in
  rahul | hritik | pratham) ;;
  *) echo "Usage: $0 rahul|hritik|pratham   (Arnav -> rahul, Yuvraj -> hritik, Sheel -> pratham)"; exit 1 ;;
esac

root="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091
source "$root/team/identities.env"

for e in "$RAHUL_EMAIL" "$HRITIK_EMAIL" "$PRATHAM_EMAIL"; do
  if [[ "$e" == 00000000+* ]]; then
    echo "team/identities.env still has placeholder emails. Fill in all three first."
    exit 1
  fi
done

upper="$(echo "$who" | tr '[:lower:]' '[:upper:]')"
name_var="${upper}_NAME"
email_var="${upper}_EMAIL"

git config --local user.name "${!name_var}"
git config --local user.email "${!email_var}"
git config --local core.hooksPath .githooks
git config --local hackathon.allowedAuthors "$RAHUL_EMAIL,$HRITIK_EMAIL,$PRATHAM_EMAIL"
git config --local pull.rebase true
chmod +x "$root/.githooks/pre-push" "$root/scripts/check-authors.sh" "$root/scripts/setup-identity.sh"

echo "This clone now commits as: $(git config user.name) <$(git config user.email)>"
echo "Pre-push author check: on"
