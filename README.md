# Cebu RoadGuard AI — Project Development 2 (Stage 1)

This stage extends the existing Django 5.2/Supabase PostgreSQL account application. The first feature branch adds **vehicle-record CRUD** and **manual/simulated suspected-violation CRUD**. The final stage integrates administrator review, verified records, and in-app alert notifications.

## Working modules in this stage
- Existing registration, login/logout, role dashboards, profile, hashed passwords.
- Vehicle records: add, list/search, inspect linked incidents, edit and delete unlinked records.
- Suspected violations: record manual sample or explicit simulation, list/filter/view, edit/delete own pending records.
- Each record has a `created_by` foreign key and is saved by the Django ORM to Supabase PostgreSQL, with actual server-side ownership checks.
- New pending incidents alert active administrators in the database; the alert inbox UI is introduced in stage 2.

**No real camera integration, AI inference, official tickets, LTO connection, driver portal, or legal fines.** Simulation is always labeled as fake test data.

## Windows setup

Continue using the `.env` from your existing local application (never commit it):

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8001
```

Or use `8000` if available. The production application uses Supabase PostgreSQL via `DATABASE_URL`, configured exactly as in the existing application. `.env.example` remains a public template with placeholders only.

Run the offline test suite using explicit SQLite test mode:

```powershell
$env:ROADGUARD_TEST_SQLITE="1"
python manage.py test accounts violations
python manage.py check
Remove-Item Env:ROADGUARD_TEST_SQLITE
```

## GitHub

Same public repository: `YMTCIT/CebuRoadGuardAI-Canete-Yanni-G6`. Branch `feature/violation-detection-vehicles` is created from `develop` and merged by pull request, never committed directly to `main`. See the complete workflow notes in the final-stage package.

Real Supabase connections and remote pull requests cannot be verified by this ZIP alone.
