# CRAFT — Campus Resource And Freelance Talent

**CRAFT** (Campus Resource And Freelance Talent) is a campus-exclusive freelance, talent, and project collaboration marketplace designed for students and campus organizations at Rajshahi University of Engineering & Technology (RUET).

The central concept is:
> A trusted campus platform where students can discover skills, offer services, find project opportunities, collaborate with peers, and build a verified professional reputation within the university community.

---

## Key Features

- **Public Landing Page** (`/`): Welcoming guest visitors with platform highlights, skill categories, and latest open opportunities.
- **Role-Based Authentication** (`accounts/`): Clean registration with dynamic role switching (Student vs. Client/Club Organizer), login, and profile management with skill tags.
- **Services Marketplace** (`services/`): Students offer freelance skills and technical services (embedded prototypes, poster design, web apps, CAD modeling) with turnaround times and price estimates.
- **Campus Projects Marketplace** (`projects/`): Full CRUD for projects, keyword search filtering, category tags, budget/deadline metadata, and client ownership enforcement.
- **Application & Review Workflow** (`applications/`): Proposal submissions by students, applicant review tables for project owners with Accept/Reject status controls, and application withdrawal.
- **CRAFT Design System**: Consistent CSS design tokens, custom components, responsive navigation shell, alerts, and interactive vanilla JavaScript enhancements.

---

## 3-Person Team Architecture

Built as modular Django apps to support three distinct vertical feature areas:

- **Shared UI Foundation**: Global design tokens (`static/css/base.css`, `static/css/components.css`), responsive shell (`templates/base.html`), landing page (`templates/home.html`), and client utilities (`static/js/main.js`).
- **Contributor 1 (`services/`)**: Campus service offerings, marketplace cards, category filters, and service CRUD.
- **Contributor 2 (`projects/`, `applications/`)**: Project marketplace, required skills, application workflows, and applicant review management.
- **Contributor 3 (`accounts/`)**: Authentication UX, public student portfolio showcase, Talent Discovery directory, and role-based dashboard router.

---

## Setup & Running Locally

```bash
# 1. Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# or standard:
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. Seed demo services (optional)
python manage.py seed_services

# 5. Run automated test suite
python manage.py test

# 6. Start development server
python manage.py runserver
```

Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) to explore the platform.

A demo superuser is already included in `db.sqlite3`:
- **Username:** `admin`
- **Password:** `AdminPass123!`

---

## Quality & Integrity Guarantees

- **Ownership Protection**: Server-side authorization checks ensure users can only edit or delete their own projects and services, and review applicants for their own listings.
- **Responsive Design**: Validated across mobile (375px+), tablet, and desktop viewports without horizontal overflow.
- **Zero Framework Bloat**: Pure Django templates with custom modern CSS and vanilla JavaScript.
