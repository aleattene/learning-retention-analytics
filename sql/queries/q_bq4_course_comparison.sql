-- q_bq4_course_comparison — BQ4: How do course characteristics affect retention?
--
-- Aggregates course-level metrics to compare retention across the 7 OULAD modules.
-- Each row represents one module (aggregated across all presentations) with:
--   - Enrollment and completion statistics
--   - Course design features (assessment density, VLE diversity)
--   - Engagement intensity metrics
--
-- Aggregating by code_module (not code_module + code_presentation) gives a
-- stable per-course view. Individual presentations can vary, but the module
-- design (assessments, resources) is the controllable variable.

SELECT
    cp.code_module,

    -- === Scale ===
    COUNT(*) AS n_presentations,
    SUM(cp.n_enrolled) AS total_enrolled,
    SUM(cp.n_completed) AS total_completed,

    -- === Outcome metrics (averaged across presentations) ===
    ROUND(AVG(cp.completion_rate_pct), 1) AS avg_completion_rate_pct,
    ROUND(AVG(cp.withdrawal_rate_pct), 1) AS avg_withdrawal_rate_pct,

    -- === Course design features ===
    -- These are characteristics that a course designer can influence
    ROUND(AVG(cp.course_length_days), 0) AS avg_course_length_days,
    ROUND(AVG(cp.n_assessments), 1) AS avg_n_assessments,
    ROUND(AVG(cp.assessments_per_30_days), 2) AS avg_assessment_density,
    ROUND(AVG(cp.n_vle_resources), 0) AS avg_n_vle_resources,
    ROUND(AVG(cp.n_activity_types), 1) AS avg_n_activity_types,

    -- === Engagement intensity (from clickstream) ===
    -- Average VLE clicks per student-day from the daily engagement view
    -- Each row in v_engagement_daily is one student-day, so AVG gives
    -- the typical daily engagement intensity, not a per-student total
    (
        SELECT ROUND(AVG(ed.total_clicks), 1)
        FROM v_engagement_daily ed
        WHERE ed.code_module = cp.code_module
    ) AS avg_clicks_per_student_day,

    -- Median engagement in the first 28 days (from early engagement view)
    -- Median is more robust than mean for skewed click distributions
    (
        SELECT ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ee.total_clicks_first_28), 0)
        FROM v_engagement_early ee
        WHERE ee.code_module = cp.code_module
    ) AS median_early_clicks

FROM v_course_profile cp
GROUP BY cp.code_module
ORDER BY avg_completion_rate_pct DESC;
