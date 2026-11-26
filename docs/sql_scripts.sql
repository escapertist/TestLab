-- Справочный DDL, соответствующий моделям SQLAlchemy (SQLite).
-- Рабочая схема создаётся автоматически: `testlab-init-db [--reset]`
-- (SQLAlchemy create_all). Значения created_at проставляет приложение
-- (UTC), поэтому DEFAULT CURRENT_TIMESTAMP здесь не используется.
--
-- Внешние ключи в SQLite работают только при `PRAGMA foreign_keys=ON`;
-- его выставляет database.create_engine на каждом соединении.

-- =========================================================
-- users
-- =========================================================
CREATE TABLE users (
    id              VARCHAR(36) PRIMARY KEY,
    username        VARCHAR(64)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'student',
    created_at      DATETIME     NOT NULL
);

CREATE INDEX ix_users_username ON users (username);

-- =========================================================
-- materials
-- =========================================================
CREATE TABLE materials (
    id           VARCHAR(36)  PRIMARY KEY,
    teacher_id   VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title        VARCHAR(255) NOT NULL,
    file_path    VARCHAR(512) NOT NULL,
    filename     VARCHAR(255) NOT NULL,
    is_uploaded  BOOLEAN      NOT NULL DEFAULT 1,
    created_at   DATETIME     NOT NULL
);

CREATE INDEX ix_materials_teacher_id ON materials (teacher_id);

-- =========================================================
-- tests
-- =========================================================
CREATE TABLE tests (
    id                 VARCHAR(36)  PRIMARY KEY,
    material_id        VARCHAR(36)  NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
    teacher_id         VARCHAR(36)  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title              VARCHAR(255) NOT NULL,
    status             VARCHAR(20)  NOT NULL DEFAULT 'draft',
    generation_params  JSON         NOT NULL,
    created_at         DATETIME     NOT NULL
);

CREATE INDEX ix_tests_material_id ON tests (material_id);
CREATE INDEX ix_tests_teacher_id  ON tests (teacher_id);

-- =========================================================
-- questions
-- =========================================================
CREATE TABLE questions (
    id           VARCHAR(36) PRIMARY KEY,
    test_id      VARCHAR(36) NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    type         VARCHAR(20) NOT NULL,
    order_index  INTEGER     NOT NULL,
    text         TEXT        NOT NULL,
    points       FLOAT       NOT NULL DEFAULT 1,
    source       VARCHAR(20) NOT NULL DEFAULT 'manual',
    created_at   DATETIME    NOT NULL
);

CREATE INDEX ix_questions_test_id ON questions (test_id);

-- =========================================================
-- closed_question_options
-- =========================================================
CREATE TABLE closed_question_options (
    id           VARCHAR(36) PRIMARY KEY,
    question_id  VARCHAR(36) NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    text         TEXT        NOT NULL,
    is_correct   BOOLEAN     NOT NULL DEFAULT 0,
    order_index  INTEGER     NOT NULL
);

CREATE INDEX ix_closed_question_options_question_id ON closed_question_options (question_id);

-- =========================================================
-- open_question_rubrics  (1:1 к открытому вопросу)
-- =========================================================
CREATE TABLE open_question_rubrics (
    id                VARCHAR(36) PRIMARY KEY,
    question_id       VARCHAR(36) NOT NULL UNIQUE REFERENCES questions(id) ON DELETE CASCADE,
    criteria_text     TEXT        NOT NULL,
    reference_answer  TEXT        NOT NULL
);

-- Таблицы assignments, results и answers пока не реализованы:
-- они описаны только в docs/er.md как план следующих этапов.
