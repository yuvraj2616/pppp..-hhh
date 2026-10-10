-- FROZEN CONTRACT (Annex C). Owner: Yuvraj (pair B). Do not rename or remove required columns:
-- judges load their own test students in exactly this schema.
-- Extra tables (sources, audit_log) and extra columns are allowed.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    student_id        TEXT PRIMARY KEY CHECK (student_id GLOB 'S[0-9][0-9][0-9][0-9]'),
    full_name         TEXT NOT NULL,
    programme         TEXT NOT NULL,
    batch_year        INTEGER NOT NULL,
    current_semester  INTEGER NOT NULL CHECK (current_semester BETWEEN 1 AND 10),
    cgpa              REAL NOT NULL CHECK (cgpa BETWEEN 0 AND 10),
    active_backlogs   INTEGER NOT NULL CHECK (active_backlogs >= 0)
);

CREATE TABLE IF NOT EXISTS courses (
    course_code  TEXT PRIMARY KEY,
    course_name  TEXT NOT NULL,
    programme    TEXT NOT NULL,
    semester     INTEGER NOT NULL,
    credits      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    student_id        TEXT NOT NULL REFERENCES students(student_id),
    course_code       TEXT NOT NULL REFERENCES courses(course_code),
    classes_held      INTEGER NOT NULL CHECK (classes_held > 0),
    classes_attended  INTEGER NOT NULL CHECK (classes_attended >= 0 AND classes_attended <= classes_held),
    PRIMARY KEY (student_id, course_code)
);
-- Attendance % is computed by tools, never stored.

CREATE TABLE IF NOT EXISTS results (
    student_id      TEXT NOT NULL REFERENCES students(student_id),
    course_code     TEXT NOT NULL REFERENCES courses(course_code),
    exam_session    TEXT NOT NULL,
    exam_type       TEXT NOT NULL CHECK (exam_type IN ('REGULAR', 'SUPPLEMENTARY')),
    internal_marks  INTEGER,
    external_marks  INTEGER,
    total_marks     INTEGER,
    max_marks       INTEGER NOT NULL,
    result          TEXT NOT NULL CHECK (result IN ('PASS', 'FAIL', 'ABSENT', 'DETAINED')),
    PRIMARY KEY (student_id, course_code, exam_session, exam_type)
);

CREATE TABLE IF NOT EXISTS rule_registry (
    rule_id           TEXT PRIMARY KEY,
    description       TEXT NOT NULL,
    parameter         TEXT NOT NULL,
    operator          TEXT NOT NULL,
    value             TEXT NOT NULL,
    scope_programmes  TEXT NOT NULL DEFAULT 'ALL',
    scope_batches     TEXT NOT NULL DEFAULT 'ALL',
    effective_from    TEXT NOT NULL,
    effective_to      TEXT,
    source_doc_id     TEXT NOT NULL,
    source_section    TEXT NOT NULL
);

-- Extra table: the Source Register (Annex B), filled from data/source_register.csv and POST /ingest.
CREATE TABLE IF NOT EXISTS sources (
    doc_id            TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    issuer            TEXT NOT NULL,
    authority_level   INTEGER NOT NULL CHECK (authority_level BETWEEN 1 AND 5),
    doc_type          TEXT NOT NULL,
    version           TEXT,
    effective_from    TEXT NOT NULL,
    effective_to      TEXT,
    supersedes        TEXT,
    scope_programmes  TEXT NOT NULL DEFAULT 'ALL',
    scope_batches     TEXT NOT NULL DEFAULT 'ALL',
    provenance        TEXT,
    retrieved_on      TEXT,
    synthetic         TEXT NOT NULL DEFAULT 'N',
    file_path         TEXT,
    chunks_indexed    INTEGER DEFAULT 0,
    ingested_at       TEXT
);

-- Extra table: one audit record per /ask response (Annex D). Stores no question text (R7).
CREATE TABLE IF NOT EXISTS audit_log (
    trace_id    TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    student_id  TEXT,
    record_json TEXT NOT NULL
);
