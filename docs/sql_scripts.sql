-- =========================================================
-- users
-- =========================================================
CREATE TABLE users (
    id              TEXT PRIMARY KEY,
    username        VARCHAR(64)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'student' CHECK (role IN ('teacher', 'student', 'admin')),
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users (username);

-- =========================================================
-- materials
-- =========================================================
CREATE TABLE materials (
    id           TEXT PRIMARY KEY,
    teacher_id   TEXT         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title        VARCHAR(255) NOT NULL,
    file_path    VARCHAR(512) NOT NULL,
    filename     VARCHAR(255) NOT NULL,
    is_uploaded  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_materials_teacher ON materials (teacher_id);

-- =========================================================
-- tests
-- =========================================================
CREATE TABLE tests (
    id                 TEXT PRIMARY KEY,
    material_id        TEXT         NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    teacher_id         TEXT         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title              VARCHAR(255) NOT NULL,
    status             VARCHAR(20)  NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    generation_params  JSON         NOT NULL DEFAULT '{}',
    created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tests_material ON tests (material_id);
CREATE INDEX idx_tests_teacher  ON tests (teacher_id);
CREATE INDEX idx_tests_status   ON tests (status);

-- =========================================================
-- questions
-- =========================================================
CREATE TABLE questions (
    id           TEXT PRIMARY KEY,
    test_id      TEXT          NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    type         VARCHAR(20)   NOT NULL CHECK (type IN ('open', 'closed')),
    order_index  INTEGER       NOT NULL,
    text         TEXT          NOT NULL,
    points       NUMERIC(6,2)  NOT NULL DEFAULT 1,
    source       VARCHAR(20)   NOT NULL DEFAULT 'manual' CHECK (source IN ('llm', 'manual')),
    created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_questions_test_order UNIQUE (test_id, order_index),
    CONSTRAINT chk_questions_points CHECK (points >= 0)
);

CREATE INDEX idx_questions_test ON questions (test_id, order_index);

-- =========================================================
-- closed_question_options
-- =========================================================
CREATE TABLE closed_question_options (
    id           TEXT PRIMARY KEY,
    question_id  TEXT    NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    text         TEXT    NOT NULL,
    is_correct   BOOLEAN NOT NULL DEFAULT FALSE,
    order_index  INTEGER NOT NULL,
    CONSTRAINT uq_options_question_order UNIQUE (question_id, order_index)
);

CREATE INDEX idx_options_question ON closed_question_options (question_id);

-- =========================================================
-- open_question_rubrics  (1:1 к открытому вопросу)
-- =========================================================
CREATE TABLE open_question_rubrics (
    id                TEXT PRIMARY KEY,
    question_id       TEXT NOT NULL UNIQUE REFERENCES questions(id) ON DELETE CASCADE,
    criteria_text     TEXT NOT NULL,
    reference_answer  TEXT NOT NULL
);

-- =========================================================
-- assignments
-- =========================================================
CREATE TABLE assignments (
    id           TEXT PRIMARY KEY,
    test_id      TEXT              NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    student_id   TEXT              NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by  TEXT              NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status       VARCHAR(20)       NOT NULL DEFAULT 'assigned' CHECK (status IN ('assigned', 'in_progress', 'submitted', 'graded')),
    created_at   DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_assignments_test_student UNIQUE (test_id, student_id)
);

CREATE INDEX idx_assignments_student ON assignments (student_id, status);
CREATE INDEX idx_assignments_test    ON assignments (test_id);

-- =========================================================
-- results
-- =========================================================
CREATE TABLE results (
    id             TEXT PRIMARY KEY,
    assignment_id  TEXT          NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    test_version   INTEGER       NOT NULL DEFAULT 1,
    status         VARCHAR(20)   NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'submitted', 'auto_checked', 'graded')),
    auto_score     NUMERIC(8,2),
    final_score    NUMERIC(8,2),
    graded_by      TEXT          REFERENCES users(id) ON DELETE SET NULL,
    graded_at      DATETIME
);

CREATE INDEX idx_results_assignment ON results (assignment_id);
CREATE INDEX idx_results_status     ON results (status);

-- =========================================================
-- answers
-- =========================================================
CREATE TABLE answers (
    id                  TEXT PRIMARY KEY,
    result_id           TEXT          NOT NULL REFERENCES results(id) ON DELETE CASCADE,
    question_id         TEXT          NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    answer_text         TEXT,
    selected_option_id  TEXT          REFERENCES closed_question_options(id) ON DELETE SET NULL,
    is_correct_auto     BOOLEAN,
    llm_score           NUMERIC(6,2),
    llm_feedback        TEXT,
    teacher_score       NUMERIC(6,2),
    teacher_comment     TEXT,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_answers_result_question UNIQUE (result_id, question_id),
    CONSTRAINT chk_answers_payload CHECK (
        (answer_text IS NOT NULL) OR (selected_option_id IS NOT NULL)
    )
);

CREATE INDEX idx_answers_result   ON answers (result_id);
CREATE INDEX idx_answers_question ON answers (question_id);