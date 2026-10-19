import json

from flask import Flask, render_template, request, redirect, url_for
from database import get_db_connection
app = Flask(__name__)


# Dashboard
@app.route('/')
def dashboard():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM companies")
    result = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        'dashboard.html',
        total_companies=result['total']
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

if __name__ == '__main__':
    app.run(debug=True)