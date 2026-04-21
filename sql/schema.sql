-- schema.sql — DDL for OULAD raw tables
--
-- Defines the 7 raw tables that mirror the OULAD CSV structure.
-- All types are kept generic (VARCHAR, INTEGER, DOUBLE) for ANSI compliance.
-- DROP IF EXISTS ensures idempotent re-runs (safe to execute multiple times).
--
-- Table relationships:
--   courses ←── assessments (via code_module + code_presentation)
--   courses ←── vle (via code_module + code_presentation)
--   courses ←── studentInfo (via code_module + code_presentation)
--   studentInfo ←── studentRegistration (via id_student + code_module + code_presentation)
--   studentInfo ←── studentVle (via id_student, linked through vle.id_site)
--   studentInfo ←── studentAssessment (via id_student, linked through assessments.id_assessment)

-- Course metadata: one row per module-presentation combination
-- module_presentation_length = duration of the course in days
DROP TABLE IF EXISTS courses;
CREATE TABLE courses (
    code_module         VARCHAR,
    code_presentation   VARCHAR,
    module_presentation_length INTEGER
);

-- Assessment metadata: defines all assessments across courses
-- assessment_type: TMA (tutor-marked), CMA (computer-marked), Exam
-- date: days relative to course start when assessment is due
-- weight: percentage contribution to final grade (0-100)
DROP TABLE IF EXISTS assessments;
CREATE TABLE assessments (
    code_module         VARCHAR,
    code_presentation   VARCHAR,
    id_assessment       INTEGER,
    assessment_type     VARCHAR,
    date                INTEGER,
    weight              DOUBLE
);

-- VLE resource metadata: describes each learning resource
-- activity_type: e.g. 'oucontent', 'forumng', 'quiz', 'resource'
-- week_from / week_to: course weeks during which the resource is available
-- Each id_site is unique within a module-presentation
DROP TABLE IF EXISTS vle;
CREATE TABLE vle (
    id_site             INTEGER,
    code_module         VARCHAR,
    code_presentation   VARCHAR,
    activity_type       VARCHAR,
    week_from           INTEGER,
    week_to             INTEGER
);

-- Student demographics and final outcome
-- final_result: Pass, Distinction, Fail, Withdrawn
-- num_of_prev_attempts: how many times the student previously attempted this module
-- studied_credits: total credit load the student is taking this presentation
DROP TABLE IF EXISTS studentInfo;
CREATE TABLE studentInfo (
    code_module         VARCHAR,
    code_presentation   VARCHAR,
    id_student          INTEGER,
    gender              VARCHAR,
    region              VARCHAR,
    highest_education   VARCHAR,
    imd_band            VARCHAR,
    age_band            VARCHAR,
    num_of_prev_attempts INTEGER,
    studied_credits     INTEGER,
    disability          VARCHAR,
    final_result        VARCHAR
);

-- Student registration dates
-- date_registration: days relative to course start (can be negative = early registration)
-- date_unregistration: days relative to course start when student withdrew (NULL if didn't withdraw)
DROP TABLE IF EXISTS studentRegistration;
CREATE TABLE studentRegistration (
    code_module         VARCHAR,
    code_presentation   VARCHAR,
    id_student          INTEGER,
    date_registration   INTEGER,
    date_unregistration INTEGER
);

-- Student assessment submissions and scores
-- date_submitted: days relative to course start when the student submitted
-- score: grade received (0-100)
-- is_banked: whether the score was transferred from a previous attempt
DROP TABLE IF EXISTS studentAssessment;
CREATE TABLE studentAssessment (
    id_assessment       INTEGER,
    id_student          INTEGER,
    date_submitted      INTEGER,
    is_banked           INTEGER,
    score               DOUBLE
);

-- Student clickstream: daily aggregated interactions with VLE resources
-- date: days relative to course start
-- sum_click: total number of clicks on that resource on that day
-- This is the largest table (~10M rows in full OULAD) and the main
-- source of behavioral engagement signals
DROP TABLE IF EXISTS studentVle;
CREATE TABLE studentVle (
    code_module         VARCHAR,
    code_presentation   VARCHAR,
    id_student          INTEGER,
    id_site             INTEGER,
    date                INTEGER,
    sum_click           INTEGER
);
