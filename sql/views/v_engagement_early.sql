-- v_engagement_early — Engagement metrics for the first 28 days (0-28)
--
-- Aggregates clickstream data from the first 4 weeks of each course
-- to create early behavioral signals per student. This is the key view
-- for BQ2 ("which early signals predict drop-out?").
--
-- The 28-day window is chosen because:
--   - It captures the critical "onboarding" period
--   - It's early enough to allow intervention before most drop-out events
--   - It aligns with typical monthly review cycles in platform operations
--
-- The NTILE(10) window function ranks each student's engagement relative
-- to their peers in the same course-presentation, creating deciles that
-- normalize for differences in course design and cohort size.

CREATE OR REPLACE VIEW v_engagement_early AS
SELECT
    sv.id_student,
    sv.code_module,
    sv.code_presentation,

    -- Number of distinct days with at least one click in the first 28 days
    -- Low active_days + high total_clicks = binge pattern (cramming)
    -- High active_days + moderate clicks = steady engagement (healthier)
    COUNT(DISTINCT sv.date) AS active_days_first_28,

    -- Total clicks across all resources in the first 28 days
    SUM(sv.sum_click) AS total_clicks_first_28,

    -- Average clicks per active day (intensity of engagement when present)
    -- High avg with low active_days may indicate surface-level cramming
    -- AVG(sv.sum_click) would average per row (student × resource × day),
    -- not per distinct active day. SUM / COUNT(DISTINCT date) gives the
    -- true daily intensity regardless of how many resources were accessed.
    SUM(sv.sum_click) / NULLIF(COUNT(DISTINCT sv.date), 0) AS avg_clicks_per_active_day,

    -- Last day of activity within the window
    -- A student whose last active day is day 5 (out of 28) is likely already disengaged
    MAX(sv.date) AS last_active_day_in_window,

    -- Engagement decile within the same course-presentation
    -- NTILE(10) splits students into 10 equal-sized groups ordered by total clicks
    -- This normalizes across courses: decile 1 in a hard course ≠ decile 1 in an easy one
    NTILE(10) OVER (
        PARTITION BY sv.code_module, sv.code_presentation
        ORDER BY SUM(sv.sum_click)
    ) AS engagement_decile_in_course

FROM studentVle sv
-- Only include activity from the first 28 days of the course
WHERE sv.date BETWEEN 0 AND 28
GROUP BY
    sv.id_student,
    sv.code_module,
    sv.code_presentation;
