# Sample Data

Synthetic OULAD-conformant data for testing and CI.

## How it was generated

```bash
python scripts/generate_sample_data.py
```

## Contents

| File | Rows | Description |
|------|------|-------------|
| courses.csv | 6 | 3 modules × 2 presentations |
| assessments.csv | 36 | 6 assessments per course |
| vle.csv | 180 | 30 VLE resources per course |
| studentInfo.csv | 198 | ~33 students per course |
| studentRegistration.csv | 198 | Enrollment/withdrawal dates |
| studentAssessment.csv | ~686 | Assessment submissions |
| studentVle.csv | ~42K | Daily clickstream |

## Characteristics

- **Outcome distribution**: ~40% Pass, 10% Distinction, 15% Fail, 35% Withdrawn
- **Click patterns**: correlated with outcome (completed students click more)
- **Assessment scores**: correlated with outcome (higher scores → Pass/Distinction)
- **Demographics**: realistic distributions matching OULAD proportions
- **Reproducible**: fixed seed (42), same output every run
