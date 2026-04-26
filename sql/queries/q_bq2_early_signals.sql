-- q_bq2_early_signals — BQ2: Which early behavioral signals predict drop-out?
--
-- Joins early engagement metrics (first 28 days) with student outcomes
-- to create a dataset ready for statistical testing in Python.
--
-- The output has one row per student with both their early engagement
-- profile AND their final outcome. Python-side code (src/stats/tests.py)
-- then runs t-tests comparing completed=1 vs completed=0 groups on each
-- engagement metric, with effect sizes and multiple comparison correction.
--
-- This query intentionally does NOT perform the statistical tests in SQL —
-- those require scipy/statsmodels and are better handled in Python.
-- SQL's role here is to prepare the clean, joined dataset.

SELECT
    se.id_student,
    se.code_module,
    se.code_presentation,
    se.final_result,
    se.completed,

    -- Early engagement signals from the first 28 days
    COALESCE(ee.active_days_first_28, 0) AS active_days_first_28,
    COALESCE(ee.total_clicks_first_28, 0) AS total_clicks_first_28,
    COALESCE(ee.avg_clicks_per_active_day, 0) AS avg_clicks_per_active_day,
    ee.last_active_day_in_window,
    COALESCE(ee.engagement_decile_in_course, 1) AS engagement_decile_in_course,

    -- Early assessment performance (first assessment only)
    -- Students who submit early and score well are less likely to drop out
    first_assess.first_score,
    first_assess.first_submit_day,

    -- Registration timing: early registrants may be more committed
    se.date_registration

FROM v_student_enriched se

-- LEFT JOIN because some students may have zero VLE activity in the first 28 days
-- (they enrolled but never clicked anything — a strong dropout signal itself)
LEFT JOIN v_engagement_early ee
    ON se.id_student = ee.id_student
    AND se.code_module = ee.code_module
    AND se.code_presentation = ee.code_presentation

-- Subquery: get the score and submission day of each student's first assessment
-- Uses subquery + WHERE rn = 1 instead of QUALIFY (non-ANSI).
-- QUALIFY is supported by DuckDB/BigQuery/Snowflake but not by PostgreSQL,
-- MySQL, or SQL Server. This pattern is portable to all ANSI-compliant engines.
LEFT JOIN (
    SELECT
        id_student,
        code_module,
        code_presentation,
        first_score,
        first_submit_day
    FROM (
        SELECT
            sa.id_student,
            a.code_module,
            a.code_presentation,
            -- On the rn = 1 row these are already the first-submitted values,
            -- so direct column access replaces the redundant FIRST_VALUE windows
            sa.score AS first_score,
            sa.date_submitted AS first_submit_day,
            ROW_NUMBER() OVER (
                PARTITION BY sa.id_student, a.code_module, a.code_presentation
                ORDER BY sa.date_submitted
            ) AS rn
        FROM studentAssessment sa
        JOIN assessments a ON sa.id_assessment = a.id_assessment
        -- Only assessments due within the first 28 days
        WHERE a.date <= 28
    ) ranked
    WHERE rn = 1
) first_assess
    ON se.id_student = first_assess.id_student
    AND se.code_module = first_assess.code_module
    AND se.code_presentation = first_assess.code_presentation

ORDER BY se.code_module, se.code_presentation, se.id_student;
