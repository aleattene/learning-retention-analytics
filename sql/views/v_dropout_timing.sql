-- v_dropout_timing — When students drop out relative to course timeline
--
-- Enriches each withdrawal event with course context (total duration,
-- percentage through the course) to answer BQ1: "where and when do
-- students drop out?"
--
-- Only includes students who explicitly withdrew (date_unregistration IS NOT NULL).
-- Students who failed but never withdrew are excluded — they represent
-- a different phenomenon (academic failure vs. active departure).
--
-- The dropout_pct field normalizes timing across courses of different lengths,
-- making it possible to compare a 240-day course with a 270-day course
-- on the same scale (0-100%).

CREATE OR REPLACE VIEW v_dropout_timing AS
SELECT
    se.id_student,
    se.code_module,
    se.code_presentation,
    se.dropout_day,

    -- Course total duration in days (from courses table)
    c.module_presentation_length AS course_length,

    -- How far through the course the student was when they withdrew
    -- Expressed as a percentage: 0% = withdrew at course start, 100% = withdrew at end
    -- Negative values are intentional: they represent pre-course withdrawals
    -- (student unregistered before day 0), which is a distinct attrition signal
    -- Values > 100% are possible if unregistration happened after official end date
    ROUND(
        100.0 * se.dropout_day / c.module_presentation_length,
        1
    ) AS dropout_pct,

    -- Demographic context for segmentation analysis
    se.gender,
    se.age_band,
    se.highest_education,
    se.imd_band,
    se.disability,
    se.num_of_prev_attempts,
    se.studied_credits

FROM v_student_enriched se
-- Join with courses to get the total course duration
JOIN courses c
    ON se.code_module = c.code_module
    AND se.code_presentation = c.code_presentation
-- Only students who explicitly withdrew
WHERE se.dropout_day IS NOT NULL;
