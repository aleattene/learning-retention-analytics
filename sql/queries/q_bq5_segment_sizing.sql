-- q_bq5_segment_sizing — BQ5: Sizing the target segments for interventions
--
-- Quantifies the student segments that the top 3 interventions would target.
-- Each segment is defined by observable, actionable criteria (not demographics)
-- so that a platform operator can implement automated triggers.
--
-- The three segments correspond to the expected BQ5 recommendations:
--   1. "Ghost students" — enrolled but zero/minimal VLE activity in week 1-2
--   2. "Assessment non-submitters" — didn't submit the first assessment
--   3. "Early disengagers" — active initially but activity drops to zero by week 3-4
--
-- This query sizes each segment and computes their dropout rates to
-- estimate the impact of targeted interventions.
--
-- Uses LEFT JOINs with pre-aggregated subqueries instead of correlated
-- EXISTS for compatibility and performance.

WITH early_activity AS (
    -- Pre-aggregate: total VLE clicks in days 0-14
    -- Uses SUM(sum_click) for actual click volume, not COUNT(*) which
    -- would only count rows (one row = one student-resource-day pair)
    SELECT
        id_student, code_module, code_presentation,
        SUM(sum_click) AS total_clicks_0_14
    FROM studentVle
    WHERE date BETWEEN 0 AND 14
    GROUP BY id_student, code_module, code_presentation
),
late_activity AS (
    -- Pre-aggregate: total VLE clicks in days 15-28
    SELECT
        id_student, code_module, code_presentation,
        SUM(sum_click) AS total_clicks_15_28
    FROM studentVle
    WHERE date BETWEEN 15 AND 28
    GROUP BY id_student, code_module, code_presentation
),
early_assessments AS (
    -- Pre-aggregate: did the student submit any assessment due in first 28 days?
    SELECT DISTINCT
        sa.id_student,
        a.code_module,
        a.code_presentation
    FROM studentAssessment sa
    JOIN assessments a ON sa.id_assessment = a.id_assessment
    WHERE a.date <= 28
),
student_segments AS (
    SELECT
        se.id_student,
        se.code_module,
        se.code_presentation,
        se.completed,
        se.withdrew_explicit,

        -- Segment 1: Ghost students
        -- Zero or near-zero VLE activity in the first 14 days
        -- These students enrolled but never really started
        CASE
            WHEN COALESCE(ee.active_days_first_28, 0) <= 1
                 AND COALESCE(ee.total_clicks_first_28, 0) < 10
            THEN 1
            ELSE 0
        END AS is_ghost,

        -- Segment 2: Assessment non-submitters
        -- Didn't submit any assessment due in the first 28 days
        -- Missing the first deadline is a strong dropout predictor
        CASE
            WHEN ea.id_student IS NULL THEN 1
            ELSE 0
        END AS is_non_submitter,

        -- Segment 3: Early disengagers
        -- Had some activity in days 0-14 but zero activity in days 15-28
        -- These students started but lost momentum
        CASE
            WHEN early_act.total_clicks_0_14 IS NOT NULL
                 AND late_act.total_clicks_15_28 IS NULL
            THEN 1
            ELSE 0
        END AS is_early_disengager

    FROM v_student_enriched se

    LEFT JOIN v_engagement_early ee
        ON se.id_student = ee.id_student
        AND se.code_module = ee.code_module
        AND se.code_presentation = ee.code_presentation

    -- Join with pre-aggregated early assessment submissions
    LEFT JOIN early_assessments ea
        ON se.id_student = ea.id_student
        AND se.code_module = ea.code_module
        AND se.code_presentation = ea.code_presentation

    -- Join with pre-aggregated VLE activity for days 0-14
    LEFT JOIN early_activity early_act
        ON se.id_student = early_act.id_student
        AND se.code_module = early_act.code_module
        AND se.code_presentation = early_act.code_presentation

    -- Join with pre-aggregated VLE activity for days 15-28
    LEFT JOIN late_activity late_act
        ON se.id_student = late_act.id_student
        AND se.code_module = late_act.code_module
        AND se.code_presentation = late_act.code_presentation
)
SELECT
    -- Segment sizing and dropout rates
    COUNT(*) AS total_students,

    -- Segment 1: Ghost students
    SUM(is_ghost) AS n_ghost,
    ROUND(100.0 * SUM(is_ghost) / COUNT(*), 1) AS pct_ghost,
    ROUND(100.0 * SUM(CASE WHEN is_ghost = 1 AND completed = 0 THEN 1 ELSE 0 END)
        / NULLIF(SUM(is_ghost), 0), 1) AS ghost_non_completion_rate_pct,

    -- Segment 2: Assessment non-submitters
    SUM(is_non_submitter) AS n_non_submitter,
    ROUND(100.0 * SUM(is_non_submitter) / COUNT(*), 1) AS pct_non_submitter,
    ROUND(100.0 * SUM(CASE WHEN is_non_submitter = 1 AND completed = 0 THEN 1 ELSE 0 END)
        / NULLIF(SUM(is_non_submitter), 0), 1) AS non_submitter_non_completion_rate_pct,

    -- Segment 3: Early disengagers
    SUM(is_early_disengager) AS n_early_disengager,
    ROUND(100.0 * SUM(is_early_disengager) / COUNT(*), 1) AS pct_early_disengager,
    ROUND(100.0 * SUM(CASE WHEN is_early_disengager = 1 AND completed = 0 THEN 1 ELSE 0 END)
        / NULLIF(SUM(is_early_disengager), 0), 1) AS disengager_non_completion_rate_pct
FROM student_segments;
