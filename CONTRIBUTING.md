# Work division — 3 people, 3 independent pages/apps

The project is split into three **separate Django apps**, one per person.
Each app has its own models, forms, views, urls, admin, and templates — so
each person owns a full vertical slice (frontend + backend + database) for
their pages, not just one layer. Nobody edits another person's files.

| Person | App folder | Pages they own | Templates |
|---|---|---|---|
| **A** | `accounts/` | Register, Login, Logout, Profile, dashboard router | `templates/accounts/*.html`, `templates/base.html` |
| **B** | `projects/` | Browse Projects, Project Detail, Post/Edit/Delete Project, Client Dashboard | `templates/projects/*.html` |
| **C** | `applications/` | Apply to Project, Applicants List, Student Dashboard, Admin Dashboard | `templates/applications/*.html` |

Shared, one-time-only files (`manage.py`, `jobportal/settings.py`,
`jobportal/urls.py`, `requirements.txt`, `static/vendor/`) are the initial
scaffold — commit these once as a "project setup" commit before the three
branches diverge (see workflow below), or assign them to whoever sets up
the repo.

## Why each person's slice is independent

- **A's app (`accounts`) has no dependency on B or C.** It only exposes a
  `User` model with a `role` field — the contract everyone else builds
  against. The only place A's code "reaches out" is `dashboard_view`,
  which redirects by **URL name only** (`'projects:client_dashboard'`,
  `'applications:student_dashboard'`, `'applications:admin_dashboard'`) —
  it never imports B's or C's Python code.
- **B's app (`projects`) depends only on A's contract** (`settings.AUTH_USER_MODEL`)
  — never imports `accounts/models.py` directly. It doesn't import C's app
  at all: it reads applicant counts through the `applications` **related
  name** (`project.applications.count()`), which is just a naming
  agreement, not a code import.
- **C's app (`applications`) depends on B's `Project` model** (an
  application can't exist without knowing which project it's for) and on
  A's `User` contract. This is the one real one-directional dependency:
  **B must exist before C can be fully tested**, but B never needs C.

So the build order is **A → B → C**, but each person still writes 100% of
their own models/views/templates without touching anyone else's files.

## Agreed contract (decide this first, before splitting up)

These are the only things that need to be settled *before* everyone starts
working independently — write them down and don't change them without
telling the other two:

1. `User.role` values: `'student'`, `'client'`, `'admin'` + helper
   properties `is_student`, `is_client`, `is_admin_role` (A defines these).
2. `Project` fields: `title`, `description`, `category`, `budget`,
   `deadline`, `status` (`'open'`/`'closed'`), `client` FK (B defines these).
3. URL names each app must expose (so the others can link to them):
   - A exposes: `accounts:login`, `accounts:register`, `accounts:dashboard`, `accounts:profile`
   - B exposes: `projects:project_list`, `projects:project_detail`, `projects:project_create`, `projects:client_dashboard`
   - C exposes: `applications:project_apply`, `applications:applicants_list`, `applications:student_dashboard`, `applications:admin_dashboard`
4. `Application.related_name='applications'` on its `project` FK (C defines
   this — B's dashboard code depends on the name staying `applications`).

## Git workflow

```bash
# one person sets up the repo first with the shared scaffold
git init
git add manage.py jobportal/ requirements.txt static/vendor .gitignore README.md CONTRIBUTING.md
git commit -m "Project scaffold: settings, urls, static vendor files"
git push origin main

# then each person branches off and adds ONLY their app
git checkout -b accounts-app        # Person A
git add accounts/ templates/accounts/ templates/base.html
git commit -m "Add accounts app: register, login, logout, profile, dashboard router"
git push origin accounts-app

git checkout -b projects-app        # Person B
git add projects/ templates/projects/
git commit -m "Add projects app: browse, post, edit, delete projects, client dashboard"
git push origin projects-app

git checkout -b applications-app    # Person C
git add applications/ templates/applications/
git commit -m "Add applications app: apply, applicant management, student & admin dashboards"
git push origin applications-app
```

Open a Pull Request from each branch into `main` with that person as the
PR author — merge in order **accounts-app → projects-app → applications-app**
(matches the dependency chain, though since the files never overlap there
won't be merge conflicts regardless of order). Each person's commits will
show up under their own GitHub account on the contribution graph.

## Running it after all three are merged

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
