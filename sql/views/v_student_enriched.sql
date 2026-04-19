-- v_student_enriched — Core student-level view with enriched outcome data
--
-- Combines studentInfo (demographics + final result) with studentRegistration
-- (enrollment/withdrawal dates) to create a single row per student-module
-- that includes:
--   - All demographic fields
--   - Binarized completion outcome (1 = Pass/Distinction, 0 = Fail/Withdrawn)
--   - Explicit withdrawal day (NULL if student didn't withdraw)
--   - Flag indicating whether student explicitly withdrew
--
-- This is the foundation view referenced by most downstream queries.

CREATE OR REPLACE VIEW v_student_enriched AS
WITH registration AS (
    -- Extract registration and unregistration dates per student-module
    SELECT
        id_student,
        code_module,
        code_presentation,
        date_registration,
        date_unregistration
    FROM studentRegistration
)
SELECT
    si.id_student,
    si.code_module,
    si.code_presentation,
    si.gender,
    si.region,
    si.highest_education,
    si.imd_band,
    si.age_band,
    si.disability,
    si.num_of_prev_attempts,
    si.studied_credits,
    si.final_result,

    -- Binarized outcome: 1 = completed (Pass or Distinction), 0 = not completed
    -- This is the primary target for all retention analyses (BQ1-BQ5)
    CASE
        WHEN si.final_result IN ('Pass', 'Distinction') THEN 1
        ELSE 0
    END AS completed,

    -- Day relative to course start when the student withdrew
    -- NULL means the student stayed enrolled until the end (pass, fail, or distinction)
    r.date_unregistration AS dropout_day,

    -- Registration day (can be negative = early registration before course start)
    r.date_registration,

    -- Binary flag: 1 = student explicitly withdrew, 0 = stayed until end
    -- Useful for distinguishing active failures (stayed but failed) from withdrawals
    CASE
        WHEN r.date_unregistration IS NOT NULL THEN 1
        ELSE 0
    END AS withdrew_explicit

FROM studentInfo si
LEFT JOIN registration r
    USING (id_student, code_module, code_presentation);
