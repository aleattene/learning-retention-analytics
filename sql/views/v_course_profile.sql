-- v_course_profile — Course-level characteristics and retention metrics
--
-- One row per course-presentation with aggregated metrics that characterize
-- the course design and student outcomes. Used in BQ4 ("how do course
-- characteristics affect retention?") to identify which course features
-- correlate with better or worse retention.
--
-- Combines data from courses, assessments, vle, and v_student_enriched
-- to build a comprehensive course profile.

CREATE OR REPLACE VIEW v_course_profile AS

-- Pre-aggregate assessment counts per course-presentation to avoid
-- correlated subqueries (better performance, especially on BigQuery)
WITH assessment_stats AS (
    SELECT
        code_module,
        code_presentation,
        COUNT(*) AS n_assessments
    FROM assessments
    GROUP BY code_module, code_presentation
),

-- Pre-aggregate VLE resource counts per course-presentation
vle_stats AS (
    SELECT
        code_module,
        code_presentation,
        COUNT(DISTINCT id_site)      AS n_vle_resources,
        COUNT(DISTINCT activity_type) AS n_activity_types
    FROM vle
    GROUP BY code_module, code_presentation
)

SELECT
    c.code_module,
    c.code_presentation,
    c.module_presentation_length AS course_length_days,

    -- === Student outcome metrics ===

    -- Total enrolled students in this course-presentation
    COUNT(DISTINCT se.id_student) AS n_enrolled,

    -- Number and rate of students who completed (Pass + Distinction)
    COALESCE(SUM(se.completed), 0) AS n_completed,
    -- NULLIF guards against division-by-zero when a LEFT JOIN produces
    -- a course-presentation with no matching students in v_student_enriched
    ROUND(100.0 * COALESCE(SUM(se.completed), 0) / NULLIF(COUNT(DISTINCT se.id_student), 0), 1) AS completion_rate_pct,

    -- Number and rate of explicit withdrawals
    COALESCE(SUM(se.withdrew_explicit), 0) AS n_withdrew,
    ROUND(100.0 * COALESCE(SUM(se.withdrew_explicit), 0) / NULLIF(COUNT(DISTINCT se.id_student), 0), 1) AS withdrawal_rate_pct,

    -- === Assessment design metrics ===
    -- More frequent assessments may improve retention (regular feedback loop)
    -- or worsen it (overwhelming students)

    COALESCE(ast.n_assessments, 0) AS n_assessments,

    -- Assessment density: assessments per 30 days of course
    -- Normalizes for course length so a 240-day course with 12 assessments
    -- is comparable to a 120-day course with 6
    ROUND(
        30.0 * COALESCE(ast.n_assessments, 0)
        / c.module_presentation_length,
        2
    ) AS assessments_per_30_days,

    -- === VLE resource diversity ===
    -- Courses with more diverse resource types may engage students differently

    COALESCE(vs.n_vle_resources, 0) AS n_vle_resources,
    COALESCE(vs.n_activity_types, 0) AS n_activity_types

FROM courses c
LEFT JOIN v_student_enriched se
    ON c.code_module = se.code_module
    AND c.code_presentation = se.code_presentation
LEFT JOIN assessment_stats ast
    ON c.code_module = ast.code_module
    AND c.code_presentation = ast.code_presentation
LEFT JOIN vle_stats vs
    ON c.code_module = vs.code_module
    AND c.code_presentation = vs.code_presentation
GROUP BY
    c.code_module,
    c.code_presentation,
    c.module_presentation_length,
    ast.n_assessments,
    vs.n_vle_resources,
    vs.n_activity_types;
