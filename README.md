# Job Application Tracker

A Flask and MySQL application for managing companies, job openings, applications,
contacts, and skill-based job matches.

## Features

- Dashboard with company, job, application, and contact totals, application counts
  by status, and the five most recent applications.
- Create, view, edit, and delete companies, jobs, applications, and contacts.
- Store job requirements as a JSON array and interview details as a JSON object.
- Track application status, resume version, whether a cover letter was sent,
  and interview dates and notes.
- Compare comma-separated skills against saved job requirements on Job Match.
- Responsive navigation, forms, tables, and status badges.

## Requirements

- Python 3.9 or newer, with pip and virtual environment support.
- A running MySQL server with JSON support (MySQL 8.x is recommended).
- A MySQL account allowed to create the database and tables during setup, and
  an application account with SELECT, INSERT, UPDATE, and DELETE permissions
  on `job_tracker`.

Python dependencies are pinned in `requirements.txt`, including Flask,
mysql-connector-python, python-dotenv, and Flask's supporting packages.

## Installation and database setup

Run these commands from the project folder on macOS or Linux:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
mysql -u YOUR_SETUP_USER -p < schema.sql
```

On Windows, activate the environment with `venv\Scripts\activate` in Command
Prompt. You can also open and execute `schema.sql` in MySQL Workbench instead
of importing it from the terminal.

Create a local `.env` file in the project folder:

```dotenv
DB_HOST=localhost
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=job_tracker
```

Replace the example values with your local credentials. `database.py` loads
these settings with python-dotenv. Keep `.env` out of version control.

The schema creates the `job_tracker` database and four empty tables. It does
not create a database user or insert sample records. `IF NOT EXISTS` avoids
recreating existing tables; it does not migrate an older table definition.

## Run locally

With MySQL running and the virtual environment active:

```bash
python app.py
```

Open <http://127.0.0.1:5000>. The application starts Flask's development server
with debug mode enabled. It has no sign-in system and is intended for local
development and demonstration; do not expose this server publicly.

## Using the tracker

1. Add a company on Companies.
2. Add a job linked to that company on Jobs. Enter requirements such as
   `Python, SQL, Flask` as comma-separated skills.
3. Add an application linked to the job on Applications. Available statuses
   are Applied, Screening, Interview, Offer, Rejected, and Withdrawn.
4. Add a contact linked to a company on Contacts.
5. Use the Edit and Delete controls to maintain records, and view Dashboard
   totals after making changes.
6. Enter your skills on Job Match to see matched skills, missing skills,
   and a percentage for each saved job.

Job Match trims whitespace, ignores letter case, and removes duplicate skills.
It uses exact skill names, not semantic or AI matching. The percentage is
`round(matched required skills / total unique required skills * 100)`.
For a job requiring `Python, SQL, Flask`, entering `Python, SQL` returns 67%.
Jobs without requirements display `N/A - No requirements` and appear last;
other jobs are sorted by highest match first. User skills are not saved.

## Database design

| Table | Primary key | Relationship and stored details |
| --- | --- | --- |
| `companies` | `company_id` | Company name, industry, website, location, notes |
| `jobs` | `job_id` | References `companies.company_id`; title, type, salary range, URL, date, requirements JSON |
| `applications` | `application_id` | References `jobs.job_id`; date, status, resume version, cover letter flag, interview JSON |
| `contacts` | `contact_id` | References `companies.company_id`; name, title, email, phone, LinkedIn URL, notes |

One company can have many jobs and contacts; one job can have many applications.
The forms require these related records, although the foreign key columns in
the schema allow NULL. Foreign keys do not cascade deletes. Delete applications
before their job, and delete a company's jobs and contacts before that company.
A deletion blocked by related records returns HTTP 409 with an explanation.

## Project files

```text
app.py                       Flask routes, validation, SQL operations, Job Match
database.py                  MySQL connection and environment configuration
schema.sql                   Database and table creation
requirements.txt             Pinned Python dependencies
templates/base.html          Shared layout and navigation
templates/                   Dashboard, list/add, edit, and Job Match pages
static/style.css             Responsive application styling
AI_USAGE.md                  AI assistance disclosure
.gitignore                   Local credentials and generated file exclusions
```

## Styling

All pages extend `templates/base.html`, which provides the navigation, page header,
and stylesheet link. Each page sets `page_title`, `page_description`, and
`active_page`, then places its content in the `content` block.

`static/style.css` defines the sidebar, dashboard cards, forms, status badges,
and tables. On smaller screens navigation moves above the content, forms use one
column, and wide tables scroll horizontally. No external fonts, scripts, or CSS
libraries are required.

The application edit template is `templates/edit_application.html`, matching the
filename used by the existing Flask route.

## Manual verification

Use disposable records to check create, view, edit, and delete in all four
sections, following the relationship order above. Check dashboard counts and
statuses, the 67% Job Match example, blank requirements, missing required fields,
invalid salaries and emails, and deletion of referenced records. Resize the
browser to check navigation, forms, and horizontal table scrolling.

These are verification instructions, not a claim that this documentation update
reran the full application against a live database. The repository does not
currently contain an automated test suite.

## Troubleshooting

- Connection or access errors: confirm MySQL is running, the `.env` values are
  correct, and the application account has permission to use `job_tracker`.
- Unknown database or missing table: run `schema.sql` on the same MySQL server
  configured by `DB_HOST`.
- Missing Python package: activate the virtual environment and install
  `requirements.txt` with that environment's Python.
- A blocked delete: remove dependent applications, jobs, or contacts first.
- Port 5000 already in use: stop the other local server or run
  `flask --app app run --port 5001` and open <http://127.0.0.1:5001>.
