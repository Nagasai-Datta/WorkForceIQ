-- ============================================================
-- WorkForceIQ — MySQL Schema
-- Run once: mysql -u root -p workforceiq < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS workforceiq CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE workforceiq;

-- ----------------------------------------------------------
-- USERS (auth)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(80)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('admin','hr','project_manager','employee') NOT NULL DEFAULT 'employee',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- EMPLOYEES (profile)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    employee_id        INT AUTO_INCREMENT PRIMARY KEY,
    user_id            INT NOT NULL UNIQUE,
    name               VARCHAR(120) NOT NULL,
    email              VARCHAR(120),
    department         VARCHAR(80),
    designation        VARCHAR(80),
    years_experience   INT DEFAULT 0,
    satisfaction_score DECIMAL(3,1) DEFAULT 3.0,
    monthly_hours      INT DEFAULT 160,
    show_contact       TINYINT(1) DEFAULT 0,
    resume_path        VARCHAR(255),           -- path to uploaded PDF
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ----------------------------------------------------------
-- SKILLS (master list)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    skill_id    INT AUTO_INCREMENT PRIMARY KEY,
    skill_name  VARCHAR(80) NOT NULL UNIQUE,
    category    VARCHAR(60)
);

-- ----------------------------------------------------------
-- EMPLOYEE_SKILLS (approved skills only)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS employee_skills (
    es_id            INT AUTO_INCREMENT PRIMARY KEY,
    employee_id      INT NOT NULL,
    skill_id         INT NOT NULL,
    proficiency_level TINYINT DEFAULT 3,
    added_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_emp_skill (employee_id, skill_id),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id)    REFERENCES skills(skill_id)        ON DELETE CASCADE
);

-- ----------------------------------------------------------
-- PENDING_SKILLS  (HR approval queue)  ← NEW
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS pending_skills (
    pending_id        INT AUTO_INCREMENT PRIMARY KEY,
    employee_id       INT NOT NULL,
    skill_id          INT NOT NULL,
    proficiency_level TINYINT DEFAULT 3,
    status            ENUM('pending','approved','rejected') DEFAULT 'pending',
    submitted_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by       INT,           -- HR user_id
    reviewed_at       TIMESTAMP NULL,
    review_note       VARCHAR(255),
    UNIQUE KEY uq_pending (employee_id, skill_id, status),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id)    REFERENCES skills(skill_id)        ON DELETE CASCADE
);

-- ----------------------------------------------------------
-- PROJECTS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    project_id   INT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(120) NOT NULL,
    description  TEXT,
    status       ENUM('Draft','Validating','Active','Paused','Completed') DEFAULT 'Draft',
    start_date   DATE,
    end_date     DATE,
    created_by   INT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- ----------------------------------------------------------
-- ASSIGNMENTS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS assignments (
    assignment_id         INT AUTO_INCREMENT PRIMARY KEY,
    project_id            INT NOT NULL,
    employee_id           INT NOT NULL,
    allocation_percentage INT DEFAULT 0,
    hours_logged          INT DEFAULT 0,
    start_date            DATE,
    end_date              DATE,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_assign (project_id, employee_id),
    FOREIGN KEY (project_id)  REFERENCES projects(project_id)   ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ----------------------------------------------------------
-- UTILIZATION REPORTS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS utilization_reports (
    report_id   INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    report_date DATE NOT NULL,
    total_alloc INT DEFAULT 0,
    notes       TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

-- ----------------------------------------------------------
-- SEED: default skills
-- ----------------------------------------------------------
INSERT IGNORE INTO skills (skill_name, category) VALUES
('Python',            'Programming'),
('JavaScript',        'Programming'),
('Java',              'Programming'),
('TypeScript',        'Programming'),
('React',             'Frontend'),
('Node.js',           'Backend'),
('Django',            'Backend'),
('Flask',             'Backend'),
('SQL',               'Database'),
('PostgreSQL',        'Database'),
('MySQL',             'Database'),
('MongoDB',           'Database'),
('AWS',               'Cloud'),
('Docker',            'DevOps'),
('Kubernetes',        'DevOps'),
('Git',               'DevOps'),
('Machine Learning',  'AI/ML'),
('TensorFlow',        'AI/ML'),
('Data Analysis',     'Analytics'),
('Tableau',           'Analytics'),
('UI/UX Design',      'Design'),
('Project Management','Soft Skills'),
('Agile / Scrum',     'Soft Skills'),
('Communication',     'Soft Skills');

-- ----------------------------------------------------------
-- SEED: default admin user  (password: admin123)
-- Change this immediately after first login!
-- ----------------------------------------------------------
INSERT IGNORE INTO users (username, password_hash, role) VALUES
('admin',
 'pbkdf2:sha256:600000$rQFxLz7T$e86e4f3d621fe9c67c9d83ec5f2c85f3af5b13cd5a3d1e5a2eecb1e0cc1a1234',
 'admin');
-- Note: generate your own hash with:
-- python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))"
