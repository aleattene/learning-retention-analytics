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
SELECT
    c.code_module,
    c.code_presentation,
    c.module_presentation_length AS course_length_days,

    -- === Student outcome metrics ===

    -- Total enrolled students in this course-presentation
    COUNT(DISTINCT se.id_student) AS n_enrolled,

    -- Number and rate of students who completed (Pass + Distinction)
    SUM(se.completed) AS n_completed,
    -- NULLIF guards against division-by-zero when a LEFT JOIN produces
    -- a course-presentation with no matching students in v_student_enriched
    ROUND(100.0 * SUM(se.completed) / NULLIF(COUNT(DISTINCT se.id_student), 0), 1) AS completion_rate_pct,

    -- Number and rate of explicit withdrawals
    SUM(se.withdrew_explicit) AS n_withdrew,
    ROUND(100.0 * SUM(se.withdrew_explicit) / NULLIF(COUNT(DISTINCT se.id_student), 0), 1) AS withdrawal_rate_pct,

    -- === Assessment design metrics ===
    -- More frequent assessments may improve retention (regular feedback loop)
    -- or worsen it (overwhelming students)

    (SELECT COUNT(*)
     FROM assessments a
     WHERE a.code_module = c.code_module
       AND a.code_presentation = c.code_presentation
    ) AS n_assessments,

    -- Assessment density: assessments per 30 days of course
    -- Normalizes for course length so a 240-day course with 12 assessments
    -- is comparable to a 120-day course with 6
    ROUND(
        30.0 * (SELECT COUNT(*)
                FROM assessments a
                WHERE a.code_module = c.code_module
                  AND a.code_presentation = c.code_presentation)
        / c.module_presentation_length,
        2
    ) AS assessments_per_30_days,

    -- === VLE resource diversity ===
    -- Courses with more diverse resource types may engage students differently

    (SELECT COUNT(DISTINCT v.id_site)
     FROM vle v
     WHERE v.code_module = c.code_module
       AND v.code_presentation = c.code_presentation
    ) AS n_vle_resources,

    (SELECT COUNT(DISTINCT v.activity_type)
     FROM vle v
     WHERE v.code_module = c.code_module
       AND v.code_presentation = c.code_presentation
    ) AS n_activity_types

FROM courses c
LEFT JOIN v_student_enriched se
    ON c.code_module = se.code_module
    AND c.code_presentation = se.code_presentation
GROUP BY
    c.code_module,
    c.code_presentation,
    c.module_presentation_length;
