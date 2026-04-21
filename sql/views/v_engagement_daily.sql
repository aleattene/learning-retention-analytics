-- v_engagement_daily — Daily engagement aggregates per student
--
-- Aggregates the raw clickstream (studentVle) to one row per student per day,
-- summing clicks across all VLE resources and counting distinct resource types.
--
-- This view is used directly in EDA notebooks and other analyses of temporal
-- engagement patterns at a per-student, per-day level.
--
-- The join with vle brings in activity_type, enabling analysis of which
-- resource types (forum, content, quiz) drive engagement.

CREATE OR REPLACE VIEW v_engagement_daily AS
SELECT
    sv.id_student,
    sv.code_module,
    sv.code_presentation,
    sv.date,

    -- Total clicks across all resources on this day
    SUM(sv.sum_click) AS total_clicks,

    -- How many distinct resources the student interacted with
    -- A student clicking 1 resource 50 times vs 10 resources 5 times each
    -- shows very different engagement patterns
    COUNT(DISTINCT sv.id_site) AS distinct_resources,

    -- How many different types of activities (forum, quiz, content, etc.)
    -- Diversity of activity types signals deeper course engagement
    COUNT(DISTINCT v.activity_type) AS distinct_activity_types

FROM studentVle sv
-- Join with vle metadata to get activity_type for each resource
LEFT JOIN vle v
    ON sv.id_site = v.id_site
    AND sv.code_module = v.code_module
    AND sv.code_presentation = v.code_presentation
GROUP BY
    sv.id_student,
    sv.code_module,
    sv.code_presentation,
    sv.date;
