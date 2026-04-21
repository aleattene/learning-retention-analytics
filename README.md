# Learning Retention Analytics 🇬🇧 [🇮🇹](README_IT.md)

[![Test & Coverage](https://github.com/aleattene/learning-retention-analytics/actions/workflows/test.yml/badge.svg)](https://github.com/aleattene/learning-retention-analytics/actions/workflows/test.yml)
[![Lint & Format](https://github.com/aleattene/learning-retention-analytics/actions/workflows/lint.yml/badge.svg)](https://github.com/aleattene/learning-retention-analytics/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/aleattene/learning-retention-analytics/graph/badge.svg?token=LS2ASS9Z6K)](https://codecov.io/gh/aleattene/learning-retention-analytics)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Dataset: OULAD](https://img.shields.io/badge/dataset-OULAD-orange.svg)](https://analyse.kmi.open.ac.uk/open_dataset)

---

## Overview

A **product analytics case study** that analyzes student retention and
drop-out in online education using the
[Open University Learning Analytics Dataset (OULAD)](https://analyse.kmi.open.ac.uk/open_dataset),
~32,000 students, 7 courses, complete behavioral clickstream.

The project follows a **SQL-driven analytical pipeline**: DuckDB as a
local-first analytical database, descriptive and inferential statistics,
and a Looker Studio dashboard.

### Why this matters

Online education platforms face 40-60% drop-out rates. Understanding
**where**, **when**, and **why** students disengage is the foundation
for any retention strategy, whether in EdTech, SaaS subscriptions,
or fitness app engagement.

---

## Business Questions

| # | Question | Analytical approach |
|---|----------|---------------------|
| BQ1 | Where and when do students drop out? | Cohort analysis, cumulative dropout curves, cliff detection |
| BQ2 | Which early behavioral signals predict drop-out? | Engagement segmentation (first 28 days), t-test, effect size |
| BQ3 | Does demographics or behavior predict outcome more strongly? | Chi-square, Cramer's V, comparative analysis |
| BQ4 | How do course characteristics affect retention? | Cross-course comparison, correlation with retention rates |
| BQ5 | Top 3 actionable interventions for a platform operator? | Segment sizing, impact estimation, cost-benefit framing |

---

## Methodological Transferability

Every analytical pattern in this project is portable to other domains:

| Pattern | EdTech (this project) | SaaS Retention | Subscription Churn | Fitness App |
|---------|----------------------|----------------|---------------------|-------------|
| Cohort analysis | Enrollment cohort dropout | Trial-to-paid conversion by signup month | Renewal rate by subscription tier | 30-day retention by onboarding flow |
| Funnel analysis | Registration → first click → assessment → completion | Signup → activation → habit → upgrade | Subscribe → engage → renew | Download → first workout → weekly habit |
| Engagement segmentation | Click intensity in first 28 days | Feature adoption in first 14 days | Usage frequency before renewal window | Session frequency in first month |
| Survival-style dropout | Cumulative withdrawal curves | Time-to-churn Kaplan-Meier | Subscription survival by plan type | Days-to-lapse by activity type |

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Analytical DB | **DuckDB** (local-first) | Zero-cost, SQL-first, BigQuery migration path |
| SQL dialect | **ANSI SQL** only | No DuckDB-specific syntax — cloud-portable |
| Language | **Python 3.13+** | Pipeline orchestration, statistics, visualization |
| Statistics | **SciPy + statsmodels** | t-test, chi-square, confidence intervals, effect sizes |
| Visualization | **Matplotlib + Seaborn** | Publication-quality charts |
| Dashboard | **Looker Studio** | Free, shareable, Google Sheets as data source |
| CI/CD | **GitHub Actions** | Automated testing + linting |
| Code quality | **black + ruff + pre-commit** | Consistent formatting and linting |

---

## Project Structure

```
project_root/
├── run_pipeline.py                     # Entrypoint — orchestrates ETL
├── src/
│   ├── config.py                       # Paths, constants, env vars
│   ├── db/connection.py                # DB abstraction (DuckDB now, BQ later)
│   ├── pipeline/
│   │   ├── step_01_ingest.py           # CSV OULAD → raw DuckDB tables
│   │   ├── step_02_transform.py        # Raw tables → analytical views
│   │   └── step_03_export.py           # Views → CSV + optional Sheets push
│   ├── stats/tests.py                  # Statistical test wrappers
│   ├── sheets/push.py                  # Google Sheets integration
│   └── utils/                          # Logging, runtime utilities
├── sql/
│   ├── schema.sql                      # DDL for 7 raw OULAD tables
│   ├── views/                          # 5 analytical views
│   └── queries/                        # 5 business question queries
├── data_sample/                        # Synthetic data (~200 students) for CI
├── tests/                              # pytest suite (unit + integration + stress)
└── .github/workflows/                  # test.yml + lint.yml
```

---

## Quick Start

### Prerequisites

- Python 3.13+
- [pip-tools](https://pip-tools.readthedocs.io/) for dependency management

### Setup

```bash
# Clone the repository
git clone https://github.com/aleattene/learning-retention-analytics.git
cd learning-retention-analytics

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install pip-tools
pip-compile requirements.in
pip-compile requirements-dev.in
pip-compile requirements-test.in
pip-sync requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Download the OULAD dataset

```bash
python scripts/download_oulad.py
```

This downloads the full OULAD dataset (~450 MB) into `data/raw/`.

### Run the pipeline

```bash
# Full dataset
python -m run_pipeline

# Sample data only (for quick testing)
python -m run_pipeline --sample
```

### Run tests

```bash
# Full test suite with coverage
pytest

# Smoke tests only
pytest tests/test_smoke.py -v
```

---

## Dataset

The [Open University Learning Analytics Dataset (OULAD)](https://analyse.kmi.open.ac.uk/open_dataset)
contains data about ~32,000 students across 7 course presentations at
The Open University (UK).

| Table | Description | Key columns |
|-------|-------------|-------------|
| studentInfo | Demographics + final outcome | id_student, final_result |
| studentRegistration | Enrollment/unenrollment dates | date_registration, date_unregistration |
| studentVle | Clickstream (daily clicks per resource) | id_site, date, sum_click |
| studentAssessment | Assessment scores | id_assessment, score |
| assessments | Assessment metadata | assessment_type, date, weight |
| vle | VLE resource metadata | activity_type |
| courses | Course metadata | module_presentation_length |

**Target variable**: `final_result` ∈ {Pass, Distinction, Fail, Withdrawn}
— binarized as Completed (Pass + Distinction) vs Not completed (Fail + Withdrawn).

> **Citation**: Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2017).
> Open University Learning Analytics dataset.
> *Scientific Data*, 4, 170171.
> Licensed under [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## License

This project is licensed under the [MIT License](LICENSE).

The OULAD dataset is licensed under
[CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) - see citation above.
