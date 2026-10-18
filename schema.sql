CREATE DATABASE IF NOT EXISTS job_tracker;

USE job_tracker;

-- Table 1: Companies
CREATE TABLE IF NOT EXISTS companies (
    company_id INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry VARCHAR(50),
    website VARCHAR(200),
    city VARCHAR(50),
    state VARCHAR(50),
    notes TEXT
);

-- Table 2: Jobs
CREATE TABLE IF NOT EXISTS jobs (
    job_id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT,
    job_title VARCHAR(100) NOT NULL,
    job_type ENUM('Full-time', 'Part-time', 'Contract', 'Internship'),
    salary_min INT,
    salary_max INT,
    job_url VARCHAR(300),
    date_posted DATE,
    requirements JSON,

    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- Table 3: Applications
CREATE TABLE IF NOT EXISTS applications (
    application_id INT PRIMARY KEY AUTO_INCREMENT,
    job_id INT,
    application_date DATE NOT NULL,
    status ENUM(
        'Applied',
        'Screening',
        'Interview',
        'Offer',
        'Rejected',
        'Withdrawn'
    ),
    resume_version VARCHAR(50),
    cover_letter_sent BOOLEAN,
    interview_data JSON,

    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

-- Table 4: Contacts
CREATE TABLE IF NOT EXISTS contacts (
    contact_id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT,
    contact_name VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes TEXT,

    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);