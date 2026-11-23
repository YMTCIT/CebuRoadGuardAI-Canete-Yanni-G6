# PD2 GitHub workflow: complete violation-management module plus follow-up filter

**Repository:** https://github.com/YMTCIT/CebuRoadGuardAI-Canete-Yanni-G6

The complete 1.3 Violation Management module was intentionally kept in **one feature branch and one implementation commit**, per the developer's preference. The second feature branch adds a small useful change within the same completed module (administrator review-queue filtering) without splitting the four original features into separate commits.

This guide does not claim the pull requests were created or merged. Record their actual links and statuses for the completion report.

## PR 1: Complete 1.3 Violation Management

1. Start from `develop` and make changes on `feature/violation-management`.
2. Commit the full violation-management module, preserve PD1 account features, and push the branch.
3. On GitHub open a PR with **base `develop`**, **compare `feature/violation-management`**.
4. Run `python manage.py check`, isolated test suite, and a manual Supabase smoke test. Review Files changed.
5. Merge PR 1 into `develop`. **Do not delete the feature branch.**

## PR 2: Additional administrator review-queue filter

From the existing Django project folder (same folder as `manage.py`), after PR 1 merges:

```powershell
git status
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c feature/review-queue-type-filter
```

Extract **`CebuRoadGuardAI-PD2-Review-Filter-PR2.zip`** into the project root, overwriting only its six listed files. This adds a select box for violation type on the admin review queue, server-side validation/filtering, an HTTP regression test, and accurate README/workflow notes. Check the diff before staging.

```powershell
python manage.py check
$env:ROADGUARD_TEST_SQLITE = "1"
python manage.py test accounts violations
Remove-Item Env:ROADGUARD_TEST_SQLITE
git status
git diff --check
git check-ignore -v .env
git ls-files .env
```

Stop if tests fail or if `git ls-files .env` prints a path. Never stage actual credentials.

```powershell
git add violations/views.py violations/tests.py templates/violations/review_queue.html README.md docs/PD2_GITHUB_WORKFLOW.md docs/PD2_REVIEW_FILTER_PR.md
git diff --cached --name-only
git diff --cached --check
git commit -m "feat: filter pending review queue by violation type"
git push -u origin feature/review-queue-type-filter
```

On GitHub open PR 2 with **base `develop`**, **compare `feature/review-queue-type-filter`**. Verify changes, merge, and keep the feature branch.

## Final integration PR

```powershell
git switch develop
git pull --ff-only origin develop
python manage.py check
$env:ROADGUARD_TEST_SQLITE = "1"
python manage.py test accounts violations
Remove-Item Env:ROADGUARD_TEST_SQLITE
```

Manually verify account registration, login/logout, role dashboards, profile, vehicle CRUD, incident creation/simulation, review decisions, alerts and search/filters against your actual Supabase PostgreSQL environment.

On GitHub create PR 3 with **base `main`**, **compare `develop`**. Review and merge to `main` only after checks pass. Do not delete merged feature branches.

Finally:

```powershell
git switch main
git pull --ff-only origin main
```

Commit the completion-report PDF under `docs/` via an appropriately reviewed feature branch and pull request once the official template and real PR URLs are available; do not commit directly to `main` or invent unverified report details.
