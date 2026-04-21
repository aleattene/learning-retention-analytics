-- q_bq3_demographics_vs_behavior — BQ3: Demographics vs behavior as outcome predictors
--
-- Combines demographic features from studentInfo with behavioral features
-- from early engagement to create a dataset for comparative analysis.
--
-- Python-side code will run:
--   - Chi-square tests on demographic categories vs completion (Cramér's V)
--   - t-tests on behavioral metrics vs completion (Cohen's d)
--   - Comparison of effect sizes to answer: "what predicts outcome more,
--     who the student IS or what they DO?"
--
-- This distinction matters ethically: if behavior is a stronger signal than
-- demographics, platform interventions should focus on engagement support
-- rather than demographic profiling.

SELECT
    se.id_student,
    se.code_module,
    se.code_presentation,
    se.completed,

    -- === Demographic features (categorical) ===
    -- These will be tested with chi-square + Cramér's V
    se.gender,
    se.age_band,
    se.highest_education,
    se.imd_band,
    se.disability,
    se.num_of_prev_attempts,
    se.studied_credits,
    se.region,

    -- === Behavioral features (continuous) ===
    -- These will be tested with t-test + Cohen's d
    COALESCE(ee.active_days_first_28, 0) AS active_days_first_28,
    COALESCE(ee.total_clicks_first_28, 0) AS total_clicks_first_28,
    COALESCE(ee.avg_clicks_per_active_day, 0) AS avg_clicks_per_active_day,
    COALESCE(ee.engagement_decile_in_course, 1) AS engagement_decile_in_course,

    -- Assessment engagement: did the student submit the first assessment?
    -- A binary behavioral signal that's easy to act on
    CASE
        WHEN first_assess.first_score IS NOT NULL THEN 1
        ELSE 0
    END AS submitted_first_assessment,
    first_assess.first_score

FROM v_student_enriched se

LEFT JOIN v_engagement_early ee
    ON se.id_student = ee.id_student
    AND se.code_module = ee.code_module
    AND se.code_presentation = ee.code_presentation

-- Same first-assessment subquery as BQ2
LEFT JOIN (
    SELECT
        sa.id_student,
        a.code_module,
        a.code_presentation,
        FIRST_VALUE(sa.score) OVER (
            PARTITION BY sa.id_student, a.code_module, a.code_presentation
            ORDER BY sa.date_submitted
        ) AS first_score
    FROM studentAssessment sa
    JOIN assessments a ON sa.id_assessment = a.id_assessment
    WHERE a.date <= 28
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY sa.id_student, a.code_module, a.code_presentation
        ORDER BY sa.date_submitted
    ) = 1
) first_assess
    ON se.id_student = first_assess.id_student
    AND se.code_module = first_assess.code_module
    AND se.code_presentation = first_assess.code_presentation

ORDER BY se.code_module, se.code_presentation, se.id_student;
