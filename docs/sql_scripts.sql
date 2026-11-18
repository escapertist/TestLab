-- =========================================================
-- ENUM-типы
-- =========================================================
CREATE TYPE user_role AS ENUM ('teacher', 'student', 'admin');
CREATE TYPE test_status AS ENUM ('draft', 'published', 'archived');
CREATE TYPE question_type AS ENUM ('open', 'closed');
CREATE TYPE question_source AS ENUM ('llm', 'manual');
CREATE TYPE assignment_status AS ENUM ('assigned', 'in_progress', 'submitted', 'graded');
CREATE TYPE result_status AS ENUM ('in_progress', 'submitted', 'auto_checked', 'graded');

-- =========================================================
-- users
-- =========================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(64)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            user_role    NOT NULL DEFAULT 'student',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_username ON users (username);

-- =========================================================
-- materials
-- =========================================================
CREATE TABLE materials (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id   UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title        VARCHAR(255) NOT NULL,
    file_path    VARCHAR(512) NOT NULL,
    filename     VARCHAR(255) NOT NULL,
    is_uploaded  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_materials_teacher ON materials (teacher_id);

-- =========================================================
-- tests
-- =========================================================
CREATE TABLE tests (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id        UUID         NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    teacher_id         UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title              VARCHAR(255) NOT NULL,
    status             test_status  NOT NULL DEFAULT 'draft',
    generation_params  JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_tests_material ON tests (material_id);
CREATE INDEX idx_tests_teacher  ON tests (teacher_id);
CREATE INDEX idx_tests_status   ON tests (status);

-- =========================================================
-- questions
-- =========================================================
CREATE TABLE questions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id      UUID          NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    type         question_type NOT NULL,
    order_index  INTEGER       NOT NULL,
    text         TEXT          NOT NULL,
    points       NUMERIC(6,2)  NOT NULL DEFAULT 1,
    source       question_source NOT NULL DEFAULT 'manual',
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_questions_test_order UNIQUE (test_id, order_index),
    CONSTRAINT chk_questions_points CHECK (points >= 0)
);

CREATE INDEX idx_questions_test ON questions (test_id, order_index);

-- =========================================================
-- closed_question_options
-- =========================================================
CREATE TABLE closed_question_options (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id  UUID    NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
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
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id       UUID NOT NULL UNIQUE REFERENCES questions(id) ON DELETE CASCADE,
    criteria_text     TEXT NOT NULL,
    reference_answer  TEXT NOT NULL
);

-- =========================================================
-- assignments
-- =========================================================
CREATE TABLE assignments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id      UUID              NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    student_id   UUID              NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by  UUID              NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status       assignment_status NOT NULL DEFAULT 'assigned',
    created_at   TIMESTAMPTZ       NOT NULL DEFAULT now(),
    CONSTRAINT uq_assignments_test_student UNIQUE (test_id, student_id)
);

CREATE INDEX idx_assignments_student ON assignments (student_id, status);
CREATE INDEX idx_assignments_test    ON assignments (test_id);

-- =========================================================
-- results
-- =========================================================
CREATE TABLE results (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id  UUID          NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
    test_version   INTEGER       NOT NULL DEFAULT 1,
    status         result_status NOT NULL DEFAULT 'in_progress',
    auto_score     NUMERIC(8,2),
    final_score    NUMERIC(8,2),
    graded_by      UUID          REFERENCES users(id) ON DELETE SET NULL,
    graded_at      TIMESTAMPTZ
);

CREATE INDEX idx_results_assignment ON results (assignment_id);
CREATE INDEX idx_results_status     ON results (status);

-- =========================================================
-- answers
-- =========================================================
CREATE TABLE answers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id           UUID          NOT NULL REFERENCES results(id) ON DELETE CASCADE,
    question_id         UUID          NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    answer_text         TEXT,
    selected_option_id  UUID          REFERENCES closed_question_options(id) ON DELETE SET NULL,
    is_correct_auto     BOOLEAN,
    llm_score           NUMERIC(6,2),
    llm_feedback        TEXT,
    teacher_score       NUMERIC(6,2),
    teacher_comment     TEXT,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_answers_result_question UNIQUE (result_id, question_id),
    CONSTRAINT chk_answers_payload CHECK (
        (answer_text IS NOT NULL) OR (selected_option_id IS NOT NULL)
    )
);

CREATE INDEX idx_answers_result   ON answers (result_id);
CREATE INDEX idx_answers_question ON answers (question_id);