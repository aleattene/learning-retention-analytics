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
    -- NULL when no matching v_engagement_early row (no VLE activity):
    -- no decile rank exists for inactive students. Downstream analysis
    -- treats this as a conditional feature (dropna, not zero).
    ee.engagement_decile_in_course,

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

-- Same first-assessment selection pattern as BQ2, but this query only
-- returns first_score (not first_submit_day) because BQ3 only needs the
-- first assessment score/submission signal. Uses subquery + WHERE rn = 1
-- instead of QUALIFY (non-ANSI), portable to engines that support
-- standard window functions such as ROW_NUMBER() (SQL:2003+)
-- (see q_bq2 for full rationale).
LEFT JOIN (
    SELECT
        id_student,
        code_module,
        code_presentation,
        first_score
    FROM (
        SELECT
            sa.id_student,
            a.code_module,
            a.code_presentation,
            -- On the rn = 1 row sa.score is already the first-submitted score,
            -- so direct column access replaces the redundant FIRST_VALUE window
            sa.score AS first_score,
            ROW_NUMBER() OVER (
                PARTITION BY sa.id_student, a.code_module, a.code_presentation
                ORDER BY sa.date_submitted
            ) AS rn
        FROM studentAssessment sa
        JOIN assessments a ON sa.id_assessment = a.id_assessment
        WHERE a.date <= 28
    ) ranked
    WHERE rn = 1
) first_assess
    ON se.id_student = first_assess.id_student
    AND se.code_module = first_assess.code_module
    AND se.code_presentation = first_assess.code_presentation

ORDER BY se.code_module, se.code_presentation, se.id_student;
