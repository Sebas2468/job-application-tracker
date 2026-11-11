import json
import re

from flask import Flask, g, render_template, request, redirect, url_for
from mysql.connector import DatabaseError
from database import get_db_connection
app = Flask(__name__)


@app.teardown_request
def close_request_connections(error):
    for connection in g.pop('db_connections', []):
        connection.close()


@app.errorhandler(DatabaseError)
def invalid_database_input(error):
    if error.errno == 1451:
        return 'This record is still used by other records. Remove those first.', 409
    if error.errno in {1048, 1264, 1265, 1292, 1366, 1406, 1452, 3819}:
        return 'Invalid field value or related record. Please check your input.', 400
    raise error


@app.before_request
def validate_record_form():
    if request.method != 'POST':
        return None
    endpoint = request.endpoint or ''
    tables = {
        'company': ('companies', 'company_id'),
        'job': ('jobs', 'job_id'),
        'application': ('applications', 'application_id'),
        'contact': ('contacts', 'contact_id'),
    }
    action, _, record_type = endpoint.partition('_')
    if record_type not in tables or action not in {'add', 'edit', 'delete'}:
        return None
    if action in {'edit', 'delete'}:
        table, primary_key = tables[record_type]
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            f'SELECT {primary_key} FROM {table} WHERE {primary_key} = %s',
            (request.view_args[primary_key],)
        )
        exists = cursor.fetchone()
        cursor.close()
        connection.close()
        if not exists:
            return 'Record not found.', 404
    if action == 'delete':
        return None
    if record_type == 'job':
        job_type = request.form.get('job_type', '')
        if job_type and job_type not in {'Full-time', 'Part-time', 'Contract', 'Internship'}:
            return 'Invalid job type.', 400
        salaries = []
        for field in ['salary_min', 'salary_max']:
            value = request.form.get(field, '')
            if value:
                try:
                    salary = int(value)
                except ValueError:
                    return 'Salary must be a non-negative whole number.', 400
                if salary < 0 or salary > 2147483647:
                    return 'Salary is outside the supported range.', 400
                salaries.append(salary)
        if len(salaries) == 2 and salaries[0] > salaries[1]:
            return 'Minimum salary cannot exceed maximum salary.', 400
    if record_type == 'contact':
        email = request.form.get('email', '').strip()
        if email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            return 'Invalid email address.', 400
    return None


# Dashboard
@app.route('/')
def dashboard():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Total companies
    cursor.execute("SELECT COUNT(*) AS total FROM companies")
    total_companies = cursor.fetchone()['total']

    # Total jobs
    cursor.execute("SELECT COUNT(*) AS total FROM jobs")
    total_jobs = cursor.fetchone()['total']

    # Total applications
    cursor.execute("SELECT COUNT(*) AS total FROM applications")
    total_applications = cursor.fetchone()['total']

    # Total contacts
    cursor.execute("SELECT COUNT(*) AS total FROM contacts")
    total_contacts = cursor.fetchone()['total']

    # Applications grouped by status
    cursor.execute("""
        SELECT status, COUNT(*) AS total
        FROM applications
        GROUP BY status
    """)
    application_statuses = cursor.fetchall()

    # Five most recent applications
    cursor.execute("""
        SELECT
            applications.application_id,
            applications.application_date,
            applications.status,
            jobs.job_title,
            companies.company_name
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.job_id
        JOIN companies
            ON jobs.company_id = companies.company_id
        ORDER BY applications.application_date DESC,
                 applications.application_id DESC
        LIMIT 5
    """)
    recent_applications = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'dashboard.html',
        total_companies=total_companies,
        total_jobs=total_jobs,
        total_applications=total_applications,
        total_contacts=total_contacts,
        application_statuses=application_statuses,
        recent_applications=recent_applications
    )


# Display all companies
@app.route('/companies')
def companies():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM companies ORDER BY company_id DESC")
    all_companies = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('companies.html', companies=all_companies)


# Add a company
@app.route('/companies/add', methods=['POST'])
def add_company():
    company_name = request.form.get('company_name', '').strip()
    industry = request.form.get('industry', '').strip()
    website = request.form.get('website', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    notes = request.form.get('notes', '').strip()

    if not company_name:
        return "Company name is required.", 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO companies
        (company_name, industry, website, city, state, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (company_name, industry, website, city, state, notes))

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('companies'))


# Edit a company
@app.route('/companies/edit/<int:company_id>', methods=['GET', 'POST'])
def edit_company(company_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        industry = request.form.get('industry', '').strip()
        website = request.form.get('website', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        notes = request.form.get('notes', '').strip()

        if not company_name:
            cursor.close()
            connection.close()
            return "Company name is required.", 400

        cursor.execute("""
            UPDATE companies
            SET company_name = %s,
                industry = %s,
                website = %s,
                city = %s,
                state = %s,
                notes = %s
            WHERE company_id = %s
        """, (
            company_name, industry, website,
            city, state, notes, company_id
        ))

        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('companies'))

    cursor.execute(
        "SELECT * FROM companies WHERE company_id = %s",
        (company_id,)
    )
    company = cursor.fetchone()

    cursor.close()
    connection.close()

    if company is None:
        return "Company not found.", 404

    return render_template('edit_company.html', company=company)


# Delete a company
@app.route('/companies/delete/<int:company_id>', methods=['POST'])
def delete_company(company_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM companies WHERE company_id = %s",
        (company_id,)
    )

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('companies'))

# Display all jobs
@app.route('/jobs')
def jobs():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT jobs.*, companies.company_name
        FROM jobs
        LEFT JOIN companies
        ON jobs.company_id = companies.company_id
        ORDER BY jobs.job_id DESC
    """)

    all_jobs = cursor.fetchall()

    cursor.execute("""
        SELECT company_id, company_name
        FROM companies
        ORDER BY company_name
    """)

    all_companies = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'jobs.html',
        jobs=all_jobs,
        companies=all_companies
    )


# Add a new job
@app.route('/jobs/add', methods=['POST'])
def add_job():
    company_id = request.form.get('company_id')
    job_title = request.form.get('job_title', '').strip()
    job_type = request.form.get('job_type') or None
    salary_min = request.form.get('salary_min') or None
    salary_max = request.form.get('salary_max') or None
    job_url = request.form.get('job_url', '').strip()
    date_posted = request.form.get('date_posted') or None
    requirements = request.form.get('requirements', '')

    if not company_id or not job_title:
        return "Company and job title are required.", 400

    # Convert comma-separated skills into a JSON array
    skills = [
        skill.strip()
        for skill in requirements.split(',')
        if skill.strip()
    ]

    requirements_json = json.dumps(skills)

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO jobs
        (company_id, job_title, job_type, salary_min,
         salary_max, job_url, date_posted, requirements)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        company_id, job_title, job_type, salary_min,
        salary_max, job_url, date_posted, requirements_json
    ))

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('jobs'))


# Edit an existing job
@app.route('/jobs/edit/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        company_id = request.form.get('company_id')
        job_title = request.form.get('job_title', '').strip()
        job_type = request.form.get('job_type') or None
        salary_min = request.form.get('salary_min') or None
        salary_max = request.form.get('salary_max') or None
        job_url = request.form.get('job_url', '').strip()
        date_posted = request.form.get('date_posted') or None
        requirements = request.form.get('requirements', '')

        if not company_id or not job_title:
            cursor.close()
            connection.close()
            return "Company and job title are required.", 400

        skills = [
            skill.strip()
            for skill in requirements.split(',')
            if skill.strip()
        ]

        cursor.execute("""
            UPDATE jobs
            SET company_id = %s,
                job_title = %s,
                job_type = %s,
                salary_min = %s,
                salary_max = %s,
                job_url = %s,
                date_posted = %s,
                requirements = %s
            WHERE job_id = %s
        """, (
            company_id, job_title, job_type,
            salary_min, salary_max, job_url,
            date_posted, json.dumps(skills), job_id
        ))

        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('jobs'))

    cursor.execute(
        "SELECT * FROM jobs WHERE job_id = %s",
        (job_id,)
    )
    job = cursor.fetchone()

    if job is None:
        cursor.close()
        connection.close()
        return "Job not found.", 404

    cursor.execute("""
        SELECT company_id, company_name
        FROM companies
        ORDER BY company_name
    """)
    all_companies = cursor.fetchall()

    cursor.close()
    connection.close()

    # Convert stored JSON back into a comma-separated string
    requirements = job['requirements']

    if isinstance(requirements, str):
        requirements = json.loads(requirements)

    job['requirements_text'] = ', '.join(requirements or [])

    return render_template(
        'edit_job.html',
        job=job,
        companies=all_companies
    )


# Delete a job
@app.route('/jobs/delete/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM jobs WHERE job_id = %s",
        (job_id,)
    )

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('jobs'))

# Display all applications
@app.route('/applications')
def applications():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            applications.*,
            jobs.job_title,
            companies.company_name
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.job_id
        JOIN companies
            ON jobs.company_id = companies.company_id
        ORDER BY applications.application_date DESC
    """)

    all_applications = cursor.fetchall()

    cursor.execute("""
        SELECT
            jobs.job_id,
            jobs.job_title,
            companies.company_name
        FROM jobs
        JOIN companies
            ON jobs.company_id = companies.company_id
        ORDER BY companies.company_name, jobs.job_title
    """)

    all_jobs = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'applications.html',
        applications=all_applications,
        jobs=all_jobs
    )


# Add a new application
@app.route('/applications/add', methods=['POST'])
def add_application():
    job_id = request.form.get('job_id')
    application_date = request.form.get('application_date')
    status = request.form.get('status')
    resume_version = request.form.get('resume_version', '').strip()

    cover_letter_sent = 1 if request.form.get('cover_letter_sent') else 0

    interview_date = request.form.get('interview_date', '').strip()
    interview_notes = request.form.get('interview_notes', '').strip()

    if not job_id or not application_date:
        return "Job and application date are required.", 400

    valid_statuses = [
        'Applied', 'Screening', 'Interview',
        'Offer', 'Rejected', 'Withdrawn'
    ]

    if status not in valid_statuses:
        return "Invalid application status.", 400

    # Store interview details as JSON
    interview_data = json.dumps({
        "interview_date": interview_date,
        "notes": interview_notes
    })

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO applications
        (job_id, application_date, status,
         resume_version, cover_letter_sent, interview_data)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        job_id,
        application_date,
        status,
        resume_version,
        cover_letter_sent,
        interview_data
    ))

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('applications'))


# Edit an existing application
@app.route('/applications/edit/<int:application_id>', methods=['GET', 'POST'])
def edit_application(application_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        job_id = request.form.get('job_id')
        application_date = request.form.get('application_date')
        status = request.form.get('status')
        resume_version = request.form.get('resume_version', '').strip()

        cover_letter_sent = 1 if request.form.get('cover_letter_sent') else 0

        interview_date = request.form.get('interview_date', '').strip()
        interview_notes = request.form.get('interview_notes', '').strip()

        if not job_id or not application_date:
            cursor.close()
            connection.close()
            return "Job and application date are required.", 400

        valid_statuses = [
            'Applied', 'Screening', 'Interview',
            'Offer', 'Rejected', 'Withdrawn'
        ]

        if status not in valid_statuses:
            cursor.close()
            connection.close()
            return "Invalid application status.", 400

        interview_data = json.dumps({
            "interview_date": interview_date,
            "notes": interview_notes
        })

        cursor.execute("""
            UPDATE applications
            SET job_id = %s,
                application_date = %s,
                status = %s,
                resume_version = %s,
                cover_letter_sent = %s,
                interview_data = %s
            WHERE application_id = %s
        """, (
            job_id,
            application_date,
            status,
            resume_version,
            cover_letter_sent,
            interview_data,
            application_id
        ))

        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('applications'))

    cursor.execute("""
        SELECT *
        FROM applications
        WHERE application_id = %s
    """, (application_id,))

    application = cursor.fetchone()

    if application is None:
        cursor.close()
        connection.close()
        return "Application not found.", 404

    cursor.execute("""
        SELECT
            jobs.job_id,
            jobs.job_title,
            companies.company_name
        FROM jobs
        JOIN companies
            ON jobs.company_id = companies.company_id
        ORDER BY companies.company_name, jobs.job_title
    """)

    all_jobs = cursor.fetchall()

    cursor.close()
    connection.close()

    # Convert JSON into Python dictionary
    interview_data = application['interview_data']

    if isinstance(interview_data, str):
        interview_data = json.loads(interview_data)

    application['interview_date'] = (
        interview_data.get('interview_date', '')
        if isinstance(interview_data, dict) else ''
    )

    application['interview_notes'] = (
        interview_data.get('notes', '')
        if isinstance(interview_data, dict) else ''
    )

    return render_template(
        'edit_application.html',
        application=application,
        jobs=all_jobs
    )


# Delete an application
@app.route('/applications/delete/<int:application_id>', methods=['POST'])
def delete_application(application_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM applications
        WHERE application_id = %s
    """, (application_id,))

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('applications'))

# Display all contacts
@app.route('/contacts')
def contacts():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            contacts.*,
            companies.company_name
        FROM contacts
        LEFT JOIN companies
            ON contacts.company_id = companies.company_id
        ORDER BY contacts.contact_id DESC
    """)

    all_contacts = cursor.fetchall()

    cursor.execute("""
        SELECT company_id, company_name
        FROM companies
        ORDER BY company_name
    """)

    all_companies = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'contacts.html',
        contacts=all_contacts,
        companies=all_companies
    )


# Add a new contact
@app.route('/contacts/add', methods=['POST'])
def add_contact():
    company_id = request.form.get('company_id')
    contact_name = request.form.get('contact_name', '').strip()
    title = request.form.get('title', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    linkedin_url = request.form.get('linkedin_url', '').strip()
    notes = request.form.get('notes', '').strip()

    if not company_id or not contact_name:
        return "Company and contact name are required.", 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO contacts
        (company_id, contact_name, title, email,
         phone, linkedin_url, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        company_id, contact_name, title,
        email, phone, linkedin_url, notes
    ))

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('contacts'))


# Edit an existing contact
@app.route('/contacts/edit/<int:contact_id>', methods=['GET', 'POST'])
def edit_contact(contact_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        company_id = request.form.get('company_id')
        contact_name = request.form.get('contact_name', '').strip()
        title = request.form.get('title', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()
        notes = request.form.get('notes', '').strip()

        if not company_id or not contact_name:
            cursor.close()
            connection.close()
            return "Company and contact name are required.", 400

        cursor.execute("""
            UPDATE contacts
            SET company_id = %s,
                contact_name = %s,
                title = %s,
                email = %s,
                phone = %s,
                linkedin_url = %s,
                notes = %s
            WHERE contact_id = %s
        """, (
            company_id, contact_name, title,
            email, phone, linkedin_url, notes,
            contact_id
        ))

        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('contacts'))

    cursor.execute("""
        SELECT *
        FROM contacts
        WHERE contact_id = %s
    """, (contact_id,))

    contact = cursor.fetchone()

    if contact is None:
        cursor.close()
        connection.close()
        return "Contact not found.", 404

    cursor.execute("""
        SELECT company_id, company_name
        FROM companies
        ORDER BY company_name
    """)

    all_companies = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        'edit_contact.html',
        contact=contact,
        companies=all_companies
    )


# Delete a contact
@app.route('/contacts/delete/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM contacts
        WHERE contact_id = %s
    """, (contact_id,))

    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('contacts'))

# Calculate how well a user's skills match a job
def calculate_job_match(user_skills, required_skills):

    # Convert skills to lowercase and remove extra spaces
    user_skills_set = {
        skill.strip().lower()
        for skill in user_skills
        if isinstance(skill, str) and skill.strip()
    }

    required_skills_set = {
        skill.strip().lower()
        for skill in required_skills
        if isinstance(skill, str) and skill.strip()
    }

    # Avoid division by zero
    if not required_skills_set:
        return {
            'percentage': None,
            'matched_skills': [],
            'missing_skills': [],
            'matched_count': 0,
            'total_skills': 0
        }

    # Find matching and missing skills
    matched_skills = user_skills_set.intersection(required_skills_set)

    missing_skills = required_skills_set.difference(user_skills_set)

    # Calculate percentage
    percentage = round(
        (len(matched_skills) / len(required_skills_set)) * 100
    )

    return {
        'percentage': percentage,
        'matched_skills': sorted(matched_skills),
        'missing_skills': sorted(missing_skills),
        'matched_count': len(matched_skills),
        'total_skills': len(required_skills_set)
    }


# Job Match page
@app.route('/job-match', methods=['GET', 'POST'])
def job_match():

    results = []
    user_skills_text = ''

    if request.method == 'POST':

        user_skills_text = request.form.get(
            'user_skills', ''
        ).strip()

        # Convert comma-separated skills into a list
        user_skills = [
            skill.strip()
            for skill in user_skills_text.split(',')
            if skill.strip()
        ]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get all jobs and their company names
        cursor.execute("""
            SELECT
                jobs.job_id,
                jobs.job_title,
                jobs.requirements,
                companies.company_name
            FROM jobs
            LEFT JOIN companies
                ON jobs.company_id = companies.company_id
        """)

        all_jobs = cursor.fetchall()

        cursor.close()
        connection.close()

        for job in all_jobs:

            requirements = job['requirements']

            # MySQL JSON may be returned as a string
            if isinstance(requirements, str):
                try:
                    requirements = json.loads(requirements)
                except json.JSONDecodeError:
                    requirements = []

            # Handle jobs without requirements
            if not isinstance(requirements, list):
                requirements = []

            # Calculate the match
            match = calculate_job_match(
                user_skills,
                requirements
            )

            results.append({
                'job_id': job['job_id'],
                'job_title': job['job_title'],
                'company_name': job['company_name'],
                'percentage': match['percentage'],
                'matched_skills': match['matched_skills'],
                'missing_skills': match['missing_skills'],
                'matched_count': match['matched_count'],
                'total_skills': match['total_skills']
            })

        # Sort highest percentage first.
        # Jobs without requirements appear last.
        results.sort(
            key=lambda job: (
                job['percentage'] is not None,
                job['percentage'] if job['percentage'] is not None else -1
            ),
            reverse=True
        )

    return render_template(
        'job_match.html',
        results=results,
        user_skills_text=user_skills_text
    )

if __name__ == '__main__':
    app.run(debug=True)
