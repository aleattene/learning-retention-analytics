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

WITH student_segments AS (
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
            WHEN NOT EXISTS (
                SELECT 1
                FROM studentAssessment sa
                JOIN assessments a ON sa.id_assessment = a.id_assessment
                WHERE sa.id_student = se.id_student
                  AND a.code_module = se.code_module
                  AND a.code_presentation = se.code_presentation
                  AND a.date <= 28
            )
            THEN 1
            ELSE 0
        END AS is_non_submitter,

        -- Segment 3: Early disengagers
        -- Had some activity in days 0-14 but zero activity in days 15-28
        -- These students started but lost momentum
        CASE
            WHEN EXISTS (
                SELECT 1 FROM studentVle sv2
                WHERE sv2.id_student = se.id_student
                  AND sv2.code_module = se.code_module
                  AND sv2.code_presentation = se.code_presentation
                  AND sv2.date BETWEEN 0 AND 14
            )
            AND NOT EXISTS (
                SELECT 1 FROM studentVle sv3
                WHERE sv3.id_student = se.id_student
                  AND sv3.code_module = se.code_module
                  AND sv3.code_presentation = se.code_presentation
                  AND sv3.date BETWEEN 15 AND 28
            )
            THEN 1
            ELSE 0
        END AS is_early_disengager

    FROM v_student_enriched se
    LEFT JOIN v_engagement_early ee
        ON se.id_student = ee.id_student
        AND se.code_module = ee.code_module
        AND se.code_presentation = ee.code_presentation
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
        / NULLIF(SUM(is_early_disengager), 0), 1) AS disengager_non_completion_rate_pct;
