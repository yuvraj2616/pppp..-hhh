# Git commands — everything is pushed manually

Pairs and identities: **Arnav → Rahul**, **Yuvraj → Hritik**, **Sheel → Pratham**.
Only Rahul's, Hritik's and Pratham's GitHub accounts ever push. No AI tool commits or pushes.
Requires `git` and the GitHub CLI `gh` (https://cli.github.com).

---

## A. Night before — Rahul (repo owner), once

```bash
# 1. Unzip the starter repo and fill in the three noreply emails + names
unzip student-assistant.zip && cd student-assistant
nano team/identities.env           # GitHub -> Settings -> Emails -> ID+username@users.noreply.github.com
nano .github/CODEOWNERS            # replace @rahul-gh / @hritik-gh / @pratham-gh with real usernames

# 2. First commit as Rahul
git init -b main
./scripts/setup-identity.sh rahul
git add -A
git commit -m "chore: project scaffold and frozen contracts"

# 3. Create the private repo and push main, then dev
gh auth login                       # log in as Rahul
gh repo create student-assistant --private --source . --push
git checkout -b dev
git push -u origin dev

# 4. Collaborators (Write access)
gh api -X PUT repos/RAHUL_USERNAME/student-assistant/collaborators/HRITIK_USERNAME -f permission=push
gh api -X PUT repos/RAHUL_USERNAME/student-assistant/collaborators/PRATHAM_USERNAME -f permission=push

# 5. Allowed authors for the CI author check (same three emails as team/identities.env)
gh variable set ALLOWED_AUTHORS --body "RAHUL_EMAIL,HRITIK_EMAIL,PRATHAM_EMAIL"
```

```bash
# 6. Branch protection. Needs a public repo OR GitHub Pro/Team on Rahul's account
#    (free private repos can't protect branches; the Student Developer Pack includes Pro).
#    Run AFTER the first PR so the check names exist: test (ci), authors (author-check), compose-smoke (docker).
gh api -X PUT repos/RAHUL_USERNAME/student-assistant/branches/dev/protection --input - <<'JSON'
{"required_status_checks":{"strict":false,"contexts":["test","authors"]},
 "enforce_admins":false,
 "required_pull_request_reviews":{"required_approving_review_count":0},
 "restrictions":null}
JSON

gh api -X PUT repos/RAHUL_USERNAME/student-assistant/branches/main/protection --input - <<'JSON'
{"required_status_checks":{"strict":true,"contexts":["test","authors","compose-smoke"]},
 "enforce_admins":false,
 "required_pull_request_reviews":{"required_approving_review_count":1},
 "restrictions":null}
JSON
```

Hritik and Pratham: accept the collaborator invite (GitHub notifications or email).

## B. Each participant — create the token for your pair

GitHub → Settings → Developer settings → Fine-grained tokens → Generate:
- Repository access: **only** `student-assistant`
- Permissions: Contents, Pull requests, Workflows = **Read and write**; Metadata = Read
- Expiration: 2 days

Share it privately with your helper only. Revoke it after the event.

## C. Every machine (all six people), once

```bash
gh auth login --with-token < token.txt     # token of YOUR participant (Arnav uses Rahul's, etc.)
gh auth setup-git                          # git uses the same token for push/pull
rm token.txt
gh repo clone RAHUL_USERNAME/student-assistant
cd student-assistant
git checkout dev

./scripts/setup-identity.sh rahul          # Rahul, Arnav
./scripts/setup-identity.sh hritik         # Hritik, Yuvraj
./scripts/setup-identity.sh pratham        # Pratham, Sheel

git config user.email                      # must print the participant's noreply email
```

Local test run (no model needed):
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-ci.txt
MOCK_LLM=true pytest -q
```

---

## D. The loop for every feature (everyone, all day)

```bash
# start from fresh dev
git checkout dev && git pull
git checkout -b feat/<your-branch>                 # names in the table below

# work, then commit small and often (every 20-30 min)
git status
git add <your files>
git commit -m "feat(<area>): <what changed>"       # Conventional Commits: feat / fix / test / docs / chore

# first push + draft PR within 15 minutes of starting
git push -u origin feat/<your-branch>
gh pr create --base dev --draft --title "F<n>: <feature name>" --fill

# keep pushing as you go
git push

# ready to merge (in your merge window)
git fetch origin
git rebase origin/dev                              # resolve conflicts if any, then: git rebase --continue
MOCK_LLM=true pytest -q
./scripts/check-authors.sh
git push --force-with-lease
gh pr ready
gh pr checks --watch                               # wait for ci + author-check to go green
gh pr merge --squash --delete-branch

# next feature
git checkout dev && git pull
```

### Branch names per person

| Person (commits as) | Branches, in order |
| --- | --- |
| Rahul (Rahul) | `feat/source-register` → `feat/precedence-policy` → `feat/api-audit` |
| Arnav (Rahul) | `feat/ingest-pipeline` → `feat/retrieval` → `feat/ocr-tables` |
| Hritik (Hritik) | `feat/tools-student` → `feat/rule-registry` → `feat/tools-eligibility` → `feat/rule-extraction` |
| Yuvraj (Hritik) | `feat/db-loader` → `feat/synthetic-data` → `docs/data-card` |
| Sheel (Pratham) | `feat/llm-client` → `feat/graph-workflow` → `feat/safety-guards` → `feat/answer-composer` |
| Pratham (Pratham) | `feat/eval-set` → `feat/streamlit-ui` → `chore/docker-ci` → `feat/eval-runner` → `docs/deliverables` |

Example — Arnav's first feature:
```bash
git checkout dev && git pull
git checkout -b feat/ingest-pipeline
git add app/ingest tests/test_ingest.py
git commit -m "feat(ingest): parse PDFs into section-aware chunks with page metadata"
git push -u origin feat/ingest-pipeline
gh pr create --base dev --draft --title "F4: ingestion pipeline" --fill
```

---

## E. After 3:00 PM freeze — fixes only

```bash
git checkout dev && git pull
git checkout -b fix/<what>
git commit -am "fix(<area>): <what>"
git push -u origin fix/<what>
gh pr create --base dev --title "fix: <what>" --fill
gh pr merge --squash --delete-branch
```

## F. 3:30 PM release — Pratham opens, Rahul approves

```bash
# Pratham
git checkout dev && git pull
./scripts/check-authors.sh main..dev
gh pr create --base main --head dev --title "Release: final submission" --body "Final build for judging."

# Rahul
gh pr review <PR_NUMBER> --approve
gh pr checks <PR_NUMBER> --watch                   # test + authors + compose-smoke green
gh pr merge <PR_NUMBER> --merge                    # merge commit keeps every member's history

# Rahul: tag it (deliverable: "Git repository, tagged final")
git checkout main && git pull
git tag -a final -m "Final submission"
git push origin final
```

---

## G. When something goes wrong

**Wrong author** (push blocked by the pre-push hook or CI):
```bash
git commit --amend --reset-author --no-edit                                   # last commit only
git rebase origin/dev --exec 'git commit --amend --reset-author --no-edit'     # every commit on the branch
git push --force-with-lease
```

**AI tool added a `Co-authored-by:` line:**
```bash
git commit --amend                                 # delete the Co-authored-by line in the editor, save
git push --force-with-lease
```

**Committed to `dev` by mistake (not pushed):**
```bash
git branch feat/<name>                             # keep your work on a new branch
git reset --hard origin/dev                        # put dev back
git checkout feat/<name>
```

**Rebase conflict:**
```bash
git status                                         # see conflicted files
# fix the files, then
git add <file> && git rebase --continue
# or give up and go back:
git rebase --abort
```

**Your partner pushed to the same branch** (same account, so GitHub shows one name):
```bash
git pull --rebase
```

**CI red on `dev`:** whoever merged last fixes it on a `fix/` branch before anyone else merges.
