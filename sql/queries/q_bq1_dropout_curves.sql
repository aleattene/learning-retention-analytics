-- q_bq1_dropout_curves — BQ1: Where and when do students drop out?
--
-- Computes cumulative dropout curves per course-presentation.
-- Each row represents a day when at least one dropout occurred,
-- with running totals and percentages relative to cohort size.
--
-- The cumulative window function (SUM OVER ... ROWS BETWEEN UNBOUNDED PRECEDING)
-- builds a survival-style curve: at any point in time, you can read
-- what percentage of the original cohort has already left.
--
-- Output is designed for direct visualization as step charts in notebooks
-- and the Looker Studio dashboard.

WITH dropout_events AS (
    -- Count how many students dropped out on each specific day
    SELECT
        code_module,
        code_presentation,
        dropout_day,
        COUNT(*) AS n_dropouts
    FROM v_student_enriched
    WHERE dropout_day IS NOT NULL
    GROUP BY code_module, code_presentation, dropout_day
),
cohort_size AS (
    -- Total enrolled students per course (denominator for percentages)
    SELECT
        code_module,
        code_presentation,
        COUNT(*) AS n_enrolled
    FROM v_student_enriched
    GROUP BY code_module, code_presentation
)
SELECT
    de.code_module,
    de.code_presentation,
    de.dropout_day,
    de.n_dropouts,

    -- Running total of dropouts up to this day
    -- ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW ensures we sum
    -- all previous days plus the current one (standard cumulative pattern)
    SUM(de.n_dropouts) OVER (
        PARTITION BY de.code_module, de.code_presentation
        ORDER BY de.dropout_day
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_dropouts,

    cs.n_enrolled,

    -- Cumulative dropout rate as a percentage of the original cohort
    -- This is the primary metric for the dropout curve visualization
    ROUND(
        100.0 * SUM(de.n_dropouts) OVER (
            PARTITION BY de.code_module, de.code_presentation
            ORDER BY de.dropout_day
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / cs.n_enrolled,
        2
    ) AS cumulative_dropout_rate_pct

FROM dropout_events de
JOIN cohort_size cs
    USING (code_module, code_presentation)
ORDER BY
    de.code_module,
    de.code_presentation,
    de.dropout_day;
