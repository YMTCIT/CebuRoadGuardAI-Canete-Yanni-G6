# Cebu RoadGuard AI — Project Development 2

This release **continues the existing Project Development 1 Django application** and implements all four features of the approved **1.3 Violation Management** WBS. Its normal database is the same **Supabase PostgreSQL** instance used for account management.

**Project repository:** https://github.com/YMTCIT/CebuRoadGuardAI-Canete-Yanni-G6

## Features at a glance

| WBS | Working end-to-end workflow |
| --- | --- |
| 1.3.1 Violation Detection | Manual sample entry or an explicitly simulated detection, capture details and evidence notes, save a pending incident, search and filter incidents, edit/delete own pending records. |
| 1.3.2 Violation Review | Administrator-only review queue with violation-type filtering, incident evidence, approve/reject with required reasons, permanent review fields, separate verified-violation record for approvals. |
| 1.3.3 Vehicle Record Management | Create, list, search, filter, view, edit and delete unlinked vehicle records. Each incident references a vehicle record. |
| 1.3.4 Alert Notification | New pending incidents notify active administrators; decisions notify incident creators. Authenticated recipients read/mark-read/delete their in-app notifications. |
| PD1 Account Management | Registration, login/logout, Administrator and Traffic Officer dashboards, user profiles, Django password hashing and ownership restrictions remain working. |

### Safety and prototype boundaries

- The application **does not run an AI model**, consume a live camera feed, detect real traffic offenses, measure speeds, or connect to LTO, police, traffic-camera networks, or payment systems.
- The **Run simulation** form creates explicitly labeled synthetic demo data. The **Record incident** form captures an officer's *manual sample observations*, not validated camera evidence.
- Approval means human verification **within the academic prototype**, never a legal citation, penalty, or official enforcement decision.
- Evidence is stored as text and, optionally, a user-provided **HTTPS URL** to externally hosted authorized sample material. It does not upload footage or use Supabase Storage.
- Notifications are **in-app only**. No email/SMS/push delivery is claimed.
- The road location is a free-text sample location. No GIS/geofencing or location verification is included yet. Additional SDD/ERD requirements can be reconciled when provided.

## Roles and permissions

| Action | Traffic Officer | Administrator |
| --- | --- | --- |
| Register publicly | Yes, Officer role only | Admin is created securely through `createsuperuser` |
| Access own dashboard/profile | Yes | Yes |
| Create vehicle and pending incident | Yes, owned records | Yes, owned records |
| View vehicle/incident records | Own only | All |
| Edit/delete pending incident | Own only | Own only |
| Edit/delete vehicle | Own only; deletion blocked if linked to any incident | Own only; same safeguards |
| Approve or reject incident | No | Yes, any pending incident |
| View verified incidents | Own only | All |
| View, mark read and delete alerts | Own alerts only | Own alerts only |

Reviewed incidents are locked to prevent changing or deleting the evidence after a decision. Verified rows remain stored separately. Privileges are checked on the server; hiding a navigation link is not the security boundary.

## Data model and persistence

`accounts.User` owns `VehicleRecord` and `ViolationIncident` rows via `created_by` ForeignKeys. `ViolationIncident.vehicle` links to its vehicle. Approving an incident creates one `VerifiedViolation` row (`OneToOneField`). `AlertNotification` has a recipient `User` ForeignKey and an incident ForeignKey. All records use the Django ORM and are stored in Supabase PostgreSQL when running normally. See [docs/PD2_IMPLEMENTATION.md](docs/PD2_IMPLEMENTATION.md).

## Requirements

- Windows PowerShell (commands below) and Python 3.11 or newer.
- `requirements.txt` containing Django 5.2 LTS, PostgreSQL driver, `dj-database-url`, and `python-dotenv`.
- The existing Supabase PostgreSQL project and its password (server-side, in `.env` only).
- A user account with the Administrator role (`python manage.py createsuperuser`) and at least one Traffic Officer account for the full demo.

## Continue your existing project (Windows PowerShell)

**Do not delete your existing `.env` or Supabase database. Do not recreate the custom user model.** Apply this PD2 source code to the existing repository via the complete-module feature-branch workflow, or copy the full project source into your local project **after making a backup**.

From the Django project directory containing `manage.py`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
```

Use port `8001` since Windows previously blocked port `8000` on this machine. Open `http://127.0.0.1:8001/`. Migration `violations.0001_initial` creates the new tables in the existing PostgreSQL database without deleting PD1 account data. Do not use `flush`, `reset`, or `migrate zero`.

For a brand-new local clone that lacks `.env`, make the sample copy and **fill your own values locally** (not GitHub):

```powershell
Copy-Item .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=True`, `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`, and `DATABASE_URL` using **Supabase > Connect > Session pooler > URI**. URL-encode special password characters. SSL is required by the Django database settings. Keep `.env` private.

If you already created a superuser for PD1, you **do not need another one**. Otherwise run `python manage.py createsuperuser` after migrations.

### Primary pages

- `/register/`, `/login/`, `/dashboard/`, `/profile/` — original Account Management.
- `/violations/vehicles/` — vehicle records and filters.
- `/violations/vehicles/add/` — new vehicle record.
- `/violations/incidents/` — possible incidents with type/status/search filters.
- `/violations/incidents/add/` — manual sample entry.
- `/violations/incidents/simulate/` — test-only simulated detection.
- `/violations/review/` — Administrator review queue (officers receive HTTP 403).
- `/violations/verified/` — stored verified violations.
- `/violations/alerts/` — private alert inbox.

### End-to-end demo

1. Log in as a **Traffic Officer**, open **Vehicles**, add a sample plate identifier (for example, `ABC 1234`).
2. Choose **Run simulation** or **Record incident**, select your saved vehicle, select one of the three supported violation types, enter a Cebu road, set a past time, and submit. A **Pending** row is saved in Supabase PostgreSQL.
3. Log out and log in as an **Administrator**. Open **My alerts** (a new pending incident alert appears), then **Review queue**. Read the sample evidence and approve or reject with a written reason.
4. Approved incidents appear in **Verified violations**. A rejection has a saved decision but no verified row.
5. Log back in as the **Traffic Officer**, open **My alerts** to see the decision, then **My incidents** to see the locked reviewed record. Verify another officer cannot view your private records.
6. Use the list/search/filter pages and test editing/deleting an **unreviewed** record. Reviewed records and linked vehicle rows cannot be deleted.

## Automated tests

Run without real Supabase credentials by explicitly using SQLite **only for automated tests**:

```powershell
$env:ROADGUARD_TEST_SQLITE="1"
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test accounts violations
Remove-Item Env:ROADGUARD_TEST_SQLITE
```

The tests cover existing account flows and new validation, ownership, CRUD, role restrictions, simulation labeling, approvals/rejections, verified records, notification recipients, POST-only controls, and CSRF handling. **Actual Supabase execution must still be tested locally using your private `.env`.** The isolated test mode does not change the normal Supabase connection.

## GitHub and submission requirements

Use the same **Public** repository: `YMTCIT/CebuRoadGuardAI-Canete-Yanni-G6`.

- `main` contains stable code only. **Do not commit directly to main.**
- Create `develop` from the existing `main`.
- Merge `feature/violation-management` (all four WBS 1.3 features together) into `develop` by PR #1.
- Merge `feature/review-queue-type-filter` (an additive administrator filter plus test) into `develop` by PR #2.
- After integration and local checks, merge `develop` into `main` via a third PR.
- Keep both feature branches after merge. Use meaningful commits during each feature branch.
- `.gitignore` excludes `.env`, other local environments and caches, and generated databases. Check with `git check-ignore -v .env`. `.env.example` uses placeholders only. Never commit secrets or your `venv/`/`.venv/` folder.
- Updated commands for the **complete-module branch followed by the review-filter improvement branch** are in [docs/PD2_GITHUB_WORKFLOW.md](docs/PD2_GITHUB_WORKFLOW.md).

**No GitHub PRs are claimed to have been opened or merged by this downloadable source ZIP.** You must execute this workflow in your existing GitHub account.

## PD2 completion report

The requested `PD-Completion-Report-Template.docx` and any additional approval/SDD/ERD documents may be provided later as planned. The final PDF should be named `CebuRoadGuardAI-Canete-Yanni-G6-PD2.pdf` and committed to `docs/` **after actual PR URLs, issues, and test accounts are recorded**. Do not invent completed branches/PRs or account passwords. See [docs/PD2_REPORT_INPUTS.md](docs/PD2_REPORT_INPUTS.md).
