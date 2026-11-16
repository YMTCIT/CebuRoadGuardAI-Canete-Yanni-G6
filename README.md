# Cebu RoadGuard AI - Account Feature

A Django account-management prototype for **Cebu RoadGuard AI**, intended for authorized traffic personnel monitoring selected roads in Cebu. This release implements only the required **Account Feature**: registration, login/logout, role-based dashboards, and personal profile management. Camera monitoring, simulated violation detection, vehicle incident records, human review, alerts, and reporting are **planned modules, not working features in this release**.

## Implemented features

| Requirement | Implementation |
| --- | --- |
| Registration | Required first/last name, username, unique email, contact number, password and matching confirmation; success/error messages. |
| Secure passwords | Django's built-in `UserCreationForm` and hashing system; no plaintext passwords stored. |
| Login and logout | Django authentication and sessions, invalid-login errors, POST-only logout with CSRF protection. |
| Role dashboards | `Administrator` and `Traffic Officer`, with separate pages and server-side authorization (403 on cross-role access). |
| Profile | Authenticated user can view/edit **only their own** name, email, and contact number. |
| Database | Supabase **PostgreSQL** with Django ORM; `.env` holds the server-only connection URL. |

**Role policy:** Public self-registration is **Traffic Officer only** and cannot assign staff or administrator privileges. Administrator accounts are created using `python manage.py createsuperuser`. The Administrator dashboard additionally requires `is_staff=True`.

> This prototype does not issue legal citations, implement fine payments or a driver portal, or connect to LTO/police databases. No traffic incidents are generated or invented by its dashboards.

## Technology

- Python 3.11+ and Django 5.2 LTS
- Supabase-hosted PostgreSQL for actual application storage
- Django session-based authentication, built-in password hashing, CSRF protection
- HTML and CSS templates; no third-party front-end framework required

Django handles sign-in and stores its Django auth/session tables in Supabase PostgreSQL. **Supabase Auth and Supabase public/secret API keys are not used or required** for this server-side configuration.

## Setup (Windows PowerShell)

1. Create a free/appropriate **Supabase** project and save its database password.
2. In your Supabase project, click **Connect** and copy the **Session pooler** PostgreSQL URL (normally port `5432`). This option works on IPv4-only networks. The URL must be copied from *your own* dashboard because the pooler host and username vary by project. `sslmode=require` is enabled by default.
3. Open the extracted project folder in Visual Studio Code and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

4. Open `.env` locally and replace `DJANGO_SECRET_KEY` with a long random string. You can generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

5. In `.env`, replace the **entire** sample `DATABASE_URL` with your real Supabase PostgreSQL connection string. **Do not paste your `.env` or database password into GitHub or public chats.** Percent-encode URL-special characters in a password if needed.
6. Create the tables in Supabase and create the initial administrator:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

7. Open `http://127.0.0.1:8000/`.

- `http://127.0.0.1:8000/register/` - new officer registration
- `http://127.0.0.1:8000/login/` - login for both roles
- `http://127.0.0.1:8000/dashboard/` - role-based redirect
- `http://127.0.0.1:8000/dashboard/officer/` - officer only
- `http://127.0.0.1:8000/dashboard/admin/` - administrator only
- `http://127.0.0.1:8000/profile/` - personal profile
- `http://127.0.0.1:8000/admin/` - Django administration (staff only)

**Important:** Run migrations before creating accounts. The custom user model is defined in the **initial migration**. Do not switch `AUTH_USER_MODEL` after data has been created.

## Supabase notes

- The `DATABASE_URL` is a **server-side PostgreSQL password**. Do not expose it in HTML, JavaScript or Git commits.
- Session pooler is preferred for local IPv4 networks; use direct PostgreSQL if your deployment supports IPv6 and direct access.
- The DB driver requires encrypted connections (`sslmode=require`); for deployments where you configure certificate verification, follow Supabase's `verify-full` guidance.
- For production deployment, set `DJANGO_DEBUG=False`, configure `DJANGO_ALLOWED_HOSTS` and HTTPS, and secure the reverse proxy. `DJANGO_TRUSTED_PROXY_SSL=1` should only be used if your own trusted proxy sets the forwarded protocol header.

Official references:
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://docs.djangoproject.com/en/5.2/topics/auth/default/
- https://docs.djangoproject.com/en/5.2/topics/auth/customizing/

## Automated tests (no live Supabase credentials needed)

The test suite runs against temporary SQLite only when an explicit test flag is enabled. **This flag is for automated tests, not the actual app configuration.**

```powershell
$env:ROADGUARD_TEST_SQLITE="1"
python manage.py test accounts
python manage.py check
Remove-Item Env:ROADGUARD_TEST_SQLITE
```

The tests cover password hashing, required fields, unique usernames/emails, password confirmation, invalid credentials, protected routes, access denial between roles, POST-only logout, and editing only the signed-in user's profile.

## GitHub repository requirements

**Requested public repository name:**

`CebuRoadGuardAI-Canete-Yanni-G5`

This uses the project's documented section **G5** and ASCII rendering of the surname **Canete** for a GitHub-friendly repository name. Change the suffix if your instructor requires a different section format.

1. Create a **Public** repository on GitHub with the exact name above (without initializing a second README).
2. Check `.gitignore` before committing: `.env`, `.env.*` (except `.env.example`), `.venv/`, `venv/`, and `__pycache__/` are excluded.
3. Commit changes at meaningful development milestones and push **regularly as work continues**. Do not manufacture earlier dates or claim work was committed when it was not.
4. Example to publish your current baseline from inside the extracted project folder:

```powershell
git init
git branch -M main
git add .
git status
git commit -m "Implement RoadGuard account feature with Django and Supabase"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/CebuRoadGuardAI-Canete-Yanni-G5.git
git push -u origin main
```

5. For **future genuine changes**, commit and push each milestone separately, for example:

```powershell
git add accounts/ templates/ static/
git commit -m "Improve officer registration and dashboard validation"
git push
```

Your public GitHub repository, remote permissions, and commit history require **your own GitHub account**. This ZIP does not create or publish a repository on your behalf.

## Project structure

```text
CebuRoadGuardAI-Canete-Yanni-G5/
|-- manage.py
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- README.md
|-- roadguard/               # settings, project URLs, WSGI/ASGI
|-- accounts/                # custom user, forms, views, guards, tests, migrations
|-- templates/               # auth forms, role dashboards, profile, 403 page
`-- static/css/styles.css
```

## Submission checklist

- [ ] Registered officer account validates inputs, stores a hashed password, and logs in successfully.
- [ ] Administrator created via `createsuperuser` sees a separate admin dashboard.
- [ ] Both roles are blocked from the other's dashboard URL (403).
- [ ] Login-only routes redirect unauthenticated visitors to login.
- [ ] Profile edits affect only the signed-in user.
- [ ] The app uses your actual Supabase PostgreSQL database when not in test mode.
- [ ] `.env` and virtual environments are not present in your GitHub commits.
- [ ] `requirements.txt` is present; the GitHub repository is Public.
- [ ] Commit and push continued work in meaningful increments.
