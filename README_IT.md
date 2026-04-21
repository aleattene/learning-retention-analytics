# Analisi della Retention nell'Apprendimento 🇮🇹 [🇬🇧](README.md)

[![Test & Coverage](https://github.com/aleattene/learning-retention-analytics/actions/workflows/test.yml/badge.svg)](https://github.com/aleattene/learning-retention-analytics/actions/workflows/test.yml)
[![Lint & Format](https://github.com/aleattene/learning-retention-analytics/actions/workflows/lint.yml/badge.svg)](https://github.com/aleattene/learning-retention-analytics/actions/workflows/lint.yml)
[![codecov](https://codecov.io/gh/aleattene/learning-retention-analytics/graph/badge.svg?token=LS2ASS9Z6K)](https://codecov.io/gh/aleattene/learning-retention-analytics)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Dataset: OULAD](https://img.shields.io/badge/dataset-OULAD-orange.svg)](https://analyse.kmi.open.ac.uk/open_dataset)

---

## Panoramica

Un **case study di product analytics** che analizza la retention e
l'abbandono degli studenti nella formazione online, utilizzando
l'[Open University Learning Analytics Dataset (OULAD)](https://analyse.kmi.open.ac.uk/open_dataset), 
~32.000 studenti, 7 corsi, clickstream comportamentale completo.

Il progetto segue una **pipeline analitica SQL-driven**: DuckDB come
database analitico locale, statistica descrittiva e inferenziale, e una
dashboard in Looker Studio.

### Perché è rilevante

Le piattaforme di formazione online registrano tassi di abbandono del
40-60%. Comprendere **dove**, **quando** e **perché** gli studenti si
disimpegnano è la base di qualsiasi strategia di retention, che si
tratti di EdTech, abbonamenti SaaS o app per il fitness.

---

## Domande di Business

| # | Domanda | Approccio analitico |
|---|---------|---------------------|
| BQ1 | Dove e quando gli studenti abbandonano? | Analisi per coorte, curve cumulative di abbandono, rilevamento punti critici |
| BQ2 | Quali segnali comportamentali precoci predicono l'abbandono? | Segmentazione dell'engagement (primi 28 giorni), t-test, effect size |
| BQ3 | Le variabili demografiche o comportamentali predicono meglio l'esito? | Chi-quadrato, V di Cramer, analisi comparativa |
| BQ4 | Come le caratteristiche dei corsi influenzano la retention? | Confronto tra corsi, correlazione con i tassi di retention |
| BQ5 | Top 3 interventi azionabili per un operatore di piattaforma? | Dimensionamento dei segmenti, stima dell'impatto, analisi costi-benefici |

---

## Trasferibilità Metodologica

Ogni pattern analitico di questo progetto è portabile ad altri domini:

| Pattern | EdTech (questo progetto) | Retention SaaS | Churn Abbonamenti | App Fitness |
|---------|--------------------------|----------------|-------------------|-------------|
| Analisi per coorte | Abbandono per coorte di iscrizione | Conversione trial-to-paid per mese di registrazione | Tasso di rinnovo per fascia di abbonamento | Retention a 30 giorni per flusso di onboarding |
| Analisi funnel | Iscrizione → primo click → valutazione → completamento | Registrazione → attivazione → abitudine → upgrade | Sottoscrizione → utilizzo → rinnovo | Download → primo allenamento → abitudine settimanale |
| Segmentazione engagement | Intensità click nei primi 28 giorni | Adozione funzionalità nei primi 14 giorni | Frequenza d'uso prima della finestra di rinnovo | Frequenza sessioni nel primo mese |
| Analisi di sopravvivenza | Curve cumulative di ritiro | Time-to-churn Kaplan-Meier | Sopravvivenza abbonamento per tipo di piano | Giorni-al-disimpegno per tipo di attività |

---

## Stack Tecnologico

| Livello | Tecnologia | Motivazione |
|---------|------------|-------------|
| DB analitico | **DuckDB** (local-first) | Costo zero, SQL-first, percorso di migrazione a BigQuery |
| Dialetto SQL | Solo **ANSI SQL** | Nessuna sintassi DuckDB-specifica — portabile su cloud |
| Linguaggio | **Python 3.13+** | Orchestrazione pipeline, statistica, visualizzazione |
| Statistica | **SciPy + statsmodels** | t-test, chi-quadrato, intervalli di confidenza, effect size |
| Visualizzazione | **Matplotlib + Seaborn** | Grafici di qualità pubblicabile |
| Dashboard | **Looker Studio** | Gratuito, condivisibile, Google Sheets come data source |
| CI/CD | **GitHub Actions** | Testing e linting automatizzati |
| Qualità codice | **black + ruff + pre-commit** | Formattazione e linting consistenti |

---

## Struttura del Progetto

```
project_root/
├── run_pipeline.py                     # Entrypoint — orchestra l'ETL
├── src/
│   ├── config.py                       # Path, costanti, variabili d'ambiente
│   ├── db/connection.py                # Astrazione DB (DuckDB ora, BQ in futuro)
│   ├── pipeline/
│   │   ├── step_01_ingest.py           # CSV OULAD → tabelle raw DuckDB
│   │   ├── step_02_transform.py        # Tabelle raw → viste analitiche
│   │   └── step_03_export.py           # Viste → CSV + push opzionale su Sheets
│   ├── stats/tests.py                  # Wrapper per test statistici
│   ├── sheets/push.py                  # Integrazione Google Sheets
│   └── utils/                          # Logging, utilità runtime
├── sql/
│   ├── schema.sql                      # DDL per le 7 tabelle raw OULAD
│   ├── views/                          # 5 viste analitiche
│   └── queries/                        # 5 query per le domande di business
├── data_sample/                        # Dati sintetici (~200 studenti) per CI
├── tests/                              # Suite pytest (unit + integration + stress)
└── .github/workflows/                  # test.yml + lint.yml
```

---

## Avvio Rapido

### Prerequisiti

- Python 3.13+
- [pip-tools](https://pip-tools.readthedocs.io/) per la gestione delle dipendenze

### Setup

```bash
# Clona il repository
git clone https://github.com/aleattene/learning-retention-analytics.git
cd learning-retention-analytics

# Crea e attiva l'ambiente virtuale
python -m venv .venv
source .venv/bin/activate

# Installa le dipendenze dai lockfile pinnati
pip install pip-tools
pip-sync requirements-dev.txt

# Installa i pre-commit hook
pre-commit install
```

> **Nota maintainer**: per aggiornare le dipendenze, modificare i file `.in`
> e ricompilare: `pip-compile requirements.in && pip-compile requirements-dev.in && pip-compile requirements-test.in`

### Download del dataset OULAD

```bash
python scripts/download_oulad.py
```

Questo scarica il dataset OULAD completo (~450 MB) in `data/raw/`.

### Esecuzione della pipeline

```bash
# Dataset completo
python -m run_pipeline

# Solo dati di esempio (per test rapidi)
python -m run_pipeline --sample
```

### Esecuzione dei test

```bash
# Suite completa con coverage
pytest

# Solo smoke test
pytest tests/test_smoke.py -v
```

---

## Dataset

L'[Open University Learning Analytics Dataset (OULAD)](https://analyse.kmi.open.ac.uk/open_dataset)
contiene dati su ~32.000 studenti distribuiti su 7 presentazioni di corsi
presso la Open University (UK).

| Tabella | Descrizione | Colonne chiave |
|---------|-------------|----------------|
| studentInfo | Dati demografici + esito finale | id_student, final_result |
| studentRegistration | Date di iscrizione/cancellazione | date_registration, date_unregistration |
| studentVle | Clickstream (click giornalieri per risorsa) | id_site, date, sum_click |
| studentAssessment | Punteggi delle valutazioni | id_assessment, score |
| assessments | Metadati delle valutazioni | assessment_type, date, weight |
| vle | Metadati risorse VLE | activity_type |
| courses | Metadati dei corsi | module_presentation_length |

**Variabile target**: `final_result` ∈ {Pass, Distinction, Fail, Withdrawn}
— binarizzata come Completato (Pass + Distinction) vs Non completato (Fail + Withdrawn).

> **Citazione**: Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2017).
> Open University Learning Analytics dataset.
> *Scientific Data*, 4, 170171.
> Distribuito con licenza [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## Licenza

Questo progetto è distribuito con [Licenza MIT](LICENSE).

Il dataset OULAD è distribuito con licenza
[CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) - vedi citazione sopra.
