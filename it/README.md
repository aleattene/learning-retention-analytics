# Analisi della Retention nell'Apprendimento <a href="#"><img src="https://github.githubassets.com/images/icons/emoji/unicode/1f1ee-1f1f9.png?v8" width="28" alt="Versione italiana"/></a> <a href="../README.md"><img src="https://github.githubassets.com/images/icons/emoji/unicode/1f1ec-1f1e7.png?v8" width="28" alt="English version"/></a>

[![Test & Coverage](https://github.com/aleattene/learning-retention-analytics/actions/workflows/test.yml/badge.svg)](https://github.com/aleattene/learning-retention-analytics/actions/workflows/test.yml)
[![Code Quality](https://github.com/aleattene/learning-retention-analytics/actions/workflows/code_quality.yml/badge.svg)](https://github.com/aleattene/learning-retention-analytics/actions/workflows/code_quality.yml)
[![codecov](https://codecov.io/gh/aleattene/learning-retention-analytics/graph/badge.svg?token=LS2ASS9Z6K)](https://codecov.io/gh/aleattene/learning-retention-analytics)
[![Last Commit](https://img.shields.io/github/last-commit/aleattene/learning-retention-analytics)](https://github.com/aleattene/learning-retention-analytics/commits/main)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Analytical%20DB-yellow)](https://duckdb.org/)
[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange)](https://jupyter.org/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-blue)](https://pandas.pydata.org/)
[![Matplotlib](https://img.shields.io/badge/Matplotlib-Visualization-green)](https://matplotlib.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](../LICENSE)
[![Dataset: OULAD](https://img.shields.io/badge/dataset-OULAD-orange.svg)](https://analyse.kmi.open.ac.uk/open_dataset)

> 32.593 iscrizioni e sette corsi online: dove si concentra l'abbandono e quali segnali lo annunciano 
> già nei primi 28 giorni.

---

<br/>

## Panoramica

Un **caso studio di product analytics** che analizza la retention e l'abbandono degli studenti
nella formazione online, utilizzando 
l'[Open University Learning Analytics Dataset (OULAD)](https://analyse.kmi.open.ac.uk/open_dataset):
- **32.593** iscrizioni
- **28.785** studenti distinti
- **7** corsi
- clickstream **comportamentale** completo

Il progetto segue una pipeline analitica **SQL-driven**:
- **DuckDB** come database analitico locale
- **statistica** descrittiva e inferenziale



### Perché è rilevante

Le piattaforme di formazione online registrano mediamente **tassi di abbandono** del 40-60%.
Comprendere **dove**, **quando** e **perché** gli studenti si disimpegnano è la base di qualsiasi **strategia di
retention**, che si tratti di EdTech, abbonamenti a SaaS o app per il fitness.

---

<br/>

## Domande di Business

**Cinque domande** guidano l'intera analisi, **dalla diagnosi all'azione**:

| # | Domanda                                                               | Approccio analitico                                                            |
|---|-----------------------------------------------------------------------|--------------------------------------------------------------------------------|
| **BQ1** | Dove e quando gli studenti abbandonano?                               | Analisi per coorte, curve cumulative di abbandono e rilevamento punti critici. |
| **BQ2** | Quali segnali comportamentali precoci predicono l'abbandono?          | Segmentazione dell'engagement (primi 28 giorni), t-test ed effect size.        |
| **BQ3** | Le variabili demografiche o comportamentali predicono meglio l'esito? | Chi-quadrato, V di Cramér e analisi comparativa.                               |
| **BQ4** | Come le caratteristiche dei corsi influenzano la retention?           | Confronto tra corsi e correlazione con i tassi di retention.                   |
| **BQ5** | Migliori 3 interventi concreti per un operatore di piattaforma?       | Dimensionamento dei segmenti, stima dell'impatto e analisi costi-benefici.     |

---

<br/>

## Risultati Principali

L'analisi completa è disponibile nel [Report Esecutivo](../reports/it/REPORT.md).
In pillole:

- **BQ1**: circa **1 iscrizione su 3** termina con il ritiro esplicito. Il dropout si concentra intorno a scadenze 
di valutazione e rilascio voti.


- **BQ2**: tutti gli **8 segnali comportamentali precoci** (primi 28 giorni) sono significativamente associati 
all'abbandono. Il volume di engagement (decile di engagement, giorni attivi, click totali) domina il ranking per 
effect size.


- **BQ3**: **il comportamento è un predittore** molto più forte della demografia. In ogni livello di istruzione, 
l'engagement alto batte l'engagement basso.


- **BQ4**: i **tassi di completamento** variano dal 37% al 71% tra i 7 moduli. Pattern suggestivi con la densità di 
valutazioni, ma n = 7 non consente conclusioni inferenziali.


- **BQ5**: **tre interventi behavior-based** (attivazione ghost, checkpoint valutazioni, re-engagement terza 
settimana) coprono la maggioranza degli studenti a rischio.

---

<br/>

### La storia in tre grafici: il problema, l'insight e l'azione

![Curve cumulative di abbandono per tutte le presentazioni dei corsi](../reports/figures/it/03_dropout_curves_overlaid.png)
*Dove vive il problema (BQ1): il ritiro si accumula costantemente, con punti critici specifici per corso intorno alle 
scadenze di valutazione.*

<br/>

![Confronto effect size: demografia vs comportamento](../reports/figures/it/05_demographics_vs_behavior_comparison.png)
*L'insight centrale (BQ3): i segnali comportamentali precoci mostrano effect size molto più ampi di qualunque attributo demografico.*

<br/>

![Matrice di priorità: impatto vs costo](../reports/figures/it/07_priority_matrix.png)
*L'azione (BQ5): gli interventi candidati posizionati per impatto stimato e costo di implementazione.*

---

<br/>

## Dashboard

Una dashboard interattiva in Looker Studio (tassi di retention per corso, curve di abbandono, segmenti a rischio) è in 
fase di realizzazione: è previsto il rilascio per l'ultimo trimestre del 2026 (con la Milestone 03 della
[roadmap](#stato-del-progetto)).

---

<br/>

## Metodo e Limiti

L'analisi è interamente **osservazionale**: misura associazioni, non relazioni causali e non utilizza modelli di 
machine learning (scelta deliberata di perimetro: analytics e non data science).
Il perimetro non esclude comunque un'integrazione futura della data science, che potrebbe innestarsi sulla stessa 
pipeline e sugli stessi dati.

- **Rigore statistico**: ogni confronto riporta p-value ed effect size (d di Cohen, V di Cramér), con correzione per 
confronti multipli (Bonferroni\* e Benjamini-Hochberg\*\*) e intervalli di confidenza al 95%.


- **Effect size prima del p-value**: con ~32K osservazioni anche differenze banali raggiungono la significatività 
statistica; il criterio di ranking dei predittori è la dimensione dell'effetto.


- **Limite dichiarato**: i corsi sono solo 7 (n = 7), quindi i confronti a livello di corso (BQ4) restano descrittivi, 
senza conclusioni inferenziali.

\* **Bonferroni**: quando si eseguono molti test statistici insieme, cresce la probabilità che almeno uno 
risulti "significativo" per puro caso. La correzione di Bonferroni compensa rendendo la soglia di 
significatività più severa: la divide per il numero di test eseguiti. Approfondimento: 
[Bonferroni correction](https://en.wikipedia.org/wiki/Bonferroni_correction) (Wikipedia, in inglese).

\*\* **Benjamini-Hochberg**: correzione alternativa e meno drastica: invece di proteggere ogni singolo test, 
tiene sotto controllo la quota attesa di falsi positivi tra i risultati dichiarati significativi. In questo 
progetto tutti i risultati restano significativi con entrambe le correzioni. Approfondimento: 
[False discovery rate](https://en.wikipedia.org/wiki/False_discovery_rate) (Wikipedia, in inglese).

La guida completa alla lettura dei numeri (scale ed esempi svolti) si trova nella sezione Metodologia 
del [Report Esecutivo](../reports/it/REPORT.md).

---

<br/>

## Trasferibilità Metodologica

Ogni **pattern** analitico di questo progetto è **portabile** ad altri domini:

| Pattern | EdTech (questo progetto) | Retention SaaS | Churn Abbonamenti | App Fitness                                          |
|---------|--------------------------|----------------|-------------------|------------------------------------------------------|
| Analisi per coorte | Abbandono per coorte di iscrizione | Conversione trial-to-paid per mese di registrazione | Tasso di rinnovo per fascia di abbonamento | Retention a 30 giorni per flusso di onboarding       |
| Analisi funnel | Iscrizione - primo click - valutazione - completamento | Registrazione - attivazione - abitudine - upgrade | Sottoscrizione - utilizzo - rinnovo | Download - primo allenamento - abitudine settimanale |
| Segmentazione engagement | Intensità click nei primi 28 giorni | Adozione funzionalità nei primi 14 giorni | Frequenza d'uso prima della finestra di rinnovo | Frequenza sessioni nel primo mese                    |
| Analisi di sopravvivenza | Curve cumulative di ritiro | Time-to-churn Kaplan-Meier | Sopravvivenza abbonamento per tipo di piano | Giorni al disimpegno per tipo di attività            |

---

<br/>

## Notebook di Analisi

L'analisi completa vive in **7 notebook**: **2 esplorativi**, uno per ognuna delle **5 domande di business**.

| #      | Notebook | Focus                                                                  |
|--------|----------|------------------------------------------------------------------------|
| **01** | [EDA: Student Base](../notebooks/01_eda_student_base.ipynb) | Profilo della popolazione, esiti e baseline di qualità dei dati.       |
| **02** | [EDA: Engagement Patterns](../notebooks/02_eda_engagement_patterns.ipynb) | Comportamento clickstream, tipologie di engagement e studenti ghost.   |
| **03** | [BQ1: Dropout Timing](../notebooks/03_bq1_dropout_timing.ipynb) | Curve cumulative di abbandono e rilevamento punti critici.             |
| **04** | [BQ2: Early Signals](../notebooks/04_bq2_early_signals.ipynb) | Segnali comportamentali nei primi 28 giorni e ranking per effect size. |
| **05** | [BQ3: Demographics vs Behavior](../notebooks/05_bq3_demographics_vs_behavior.ipynb) | Forza predittiva comparata delle due famiglie di variabili.            |
| **06** | [BQ4: Course Comparison](../notebooks/06_bq4_course_comparison.ipynb) | Caratteristiche di design dei corsi e retention.                       |
| **07** | [BQ5: Recommendations Synthesis](../notebooks/07_bq5_recommendations_synthesis.ipynb) | Dimensionamento dei segmenti, matrice di priorità e top 3 interventi.  |

---

<br/>

## Stack Tecnologico

| Livello | Tecnologia                   | Motivazione                                                   |
|---------|------------------------------|---------------------------------------------------------------|
| DB analitico | **DuckDB** (local-first)     | Costo zero, SQL-first e percorso di migrazione a BigQuery.    |
| Dialetto SQL | Solo **ANSI SQL**            | Nessuna sintassi DuckDB-specifica e portabilità su cloud.     |
| Linguaggio | **Python 3.13+**             | Orchestrazione pipeline, statistica e visualizzazione.        |
| Statistica | **SciPy e statsmodels**      | t-test, chi-quadrato, intervalli di confidenza ed effect size. |
| Visualizzazione | **Matplotlib e Seaborn**     | Grafici di qualità pubblicabile.                              |
| Dashboard | **Looker Studio**            | Gratuito, condivisibile e Google Sheets come data source.     |
| CI/CD | **GitHub Actions**           | Testing e linting automatizzati.                              |
| Qualità codice | **black, ruff e pre-commit** | Formattazione e linting consistenti.                          |

---

<br/>

## Dataset

L'[Open University Learning Analytics Dataset (OULAD)](https://analyse.kmi.open.ac.uk/open_dataset) contiene **32.593 iscrizioni** 
ai **corsi** di **28.785 studenti** distinti, distribuite su **7 moduli** (22 presentazioni) presso la Open University (UK).

| Tabella | Descrizione                                         | Colonne chiave |
|---------|-----------------------------------------------------|----------------|
| studentInfo | Dati demografici con esito finale                   | id_student, final_result |
| studentRegistration | Date di iscrizione e/o cancellazione                | date_registration, date_unregistration |
| studentVle | Clickstream (click giornalieri per risorsa)         | id_site, date, sum_click |
| studentAssessment | Punteggi delle valutazioni                          | id_assessment, score |
| assessments | Metadati delle valutazioni                          | assessment_type, date, weight |
| vle | Metadati risorse VLE (Virtual Learning Environment) | activity_type |
| courses | Metadati dei corsi                                  | module_presentation_length |

**Variabile target**: l'esito finale dell'iscrizione (`final_result`). Nei dati originali può assumere quattro 
valori: Pass (promosso), Distinction (promosso con merito), Fail (bocciato) e Withdrawn (ritirato dal corso). 
Per l'analisi i quattro esiti sono raggruppati in due classi (binarizzazione dell'outcome):

- **Completato**: Pass o Distinction, il corso è stato concluso con successo;
- **Non completato**: Fail o Withdrawn, il corso non è stato portato a termine, per bocciatura o per abbandono.

> **Citazione**: Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2017).
> Open University Learning Analytics dataset.
> *Scientific Data*, 4, 170171.
> Distribuito con licenza [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

<br/>

## Struttura del Progetto

```
project_root/
├── run_pipeline.py                     # Entrypoint: orchestra l'ETL
├── src/
│   ├── config.py                       # Path, costanti, variabili d'ambiente
│   ├── db/connection.py                # Astrazione DB (DuckDB ora, BigQuery in futuro)
│   ├── pipeline/
│   │   ├── step_01_ingest.py           # CSV OULAD: tabelle raw DuckDB
│   │   ├── step_02_transform.py        # Tabelle raw: viste analitiche
│   │   ├── step_03_export.py           # Viste: CSV con push opzionale su Sheets
│   │   └── step_04_stats.py            # Test statistici BQ2/BQ3: CSV
│   ├── stats/tests.py                  # Wrapper per test statistici
│   ├── sheets/push.py                  # Integrazione Google Sheets
│   └── utils/                          # Logging, utilità runtime
├── sql/
│   ├── schema.sql                      # DDL per le 7 tabelle raw OULAD
│   ├── views/                          # 5 viste analitiche
│   └── queries/                        # 5 query per le domande di business
├── notebooks/                          # 7 notebook di analisi (EDA e BQ1-BQ5)
├── reports/
│   ├── REPORT.md                       # Report esecutivo (specchio IT in reports/it/)
│   └── figures/                        # Grafici esportati dai notebook
├── data_sample/                        # Dati sintetici (~200 studenti) per CI
├── it/                                 # Specchio italiano di questo README
├── tests/                              # Suite pytest (unit, integration e stress)
└── .github/workflows/                  # test.yml e code_quality.yml
```

---

<br/>

## Avvio Progetto

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

# macOS e Linux
source .venv/bin/activate      
    
# Windows: 
.venv\Scripts\activate

# Installa le dipendenze dai lockfile
pip install pip-tools
pip-sync requirements-dev.txt

# Installa i pre-commit hook
pre-commit install

# Per aggiornare le dipendenze, modificare i file `.in` e ricompilare con il seguente comando
pip-compile requirements.in && pip-compile requirements-dev.in && pip-compile requirements-test.in
```



### Download del dataset OULAD

```bash
python scripts/download_oulad.py
```

Con questo comando viene effettuato il download del dataset OULAD completo (~450 MB) in `data/raw/`.

> **Attenzione**: lo script di download non è ancora pubblicato *(in arrivo nel mese di settembre 2026)*.
> 
> Nel frattempo il dataset può essere scaricato manualmente dalla pagina ufficiale OULAD linkata nella sezione
> [Dataset](#dataset).

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

<br/>

## Documentazione Completa

La documentazione estesa e completa è in preparazione: sarà pubblicata a breve, con la Milestone 02 
della [roadmap](#stato-del-progetto).

| Documento | Contenuto                                                            |
|-----------|----------------------------------------------------------------------|
| [Report Esecutivo](../reports/it/REPORT.md) | Analisi completa BQ1–BQ5 con figure e numeri.                        |
| [Metodologia](../docs/it/METHODOLOGY.md) | Approccio statistico, scelte progettuali e trade-off. *(in arrivo)*  |
| [Trasferibilità](../docs/it/TRANSFERABILITY.md) | Portabilità dei pattern a SaaS, abbonamenti e fitness. *(in arrivo)* |
| [Migrazione Cloud](../docs/it/MIGRATION.md) | Percorso da DuckDB a BigQuery, gap e checklist. *(in arrivo)*        |
| [ADR](../docs/it/ADR.md) | Decisioni architetturali. *(in arrivo)*                              |
| [Testing](../docs/it/TESTING.md) | Architettura di test, strategia e decisioni. *(in arrivo)*           |

---

<br/>

## Stato del Progetto

- [x] **Milestone 01**: analisi end-to-end della retention (pipeline ETL, 7 notebook di analisi, statistica 
inferenziale con export dedicato, README e report esecutivo EN/IT, suite di test con CI, release v1.0)
- [ ] **Milestone 02**: pubblicazione della documentazione estesa (metodologia, trasferibilità, migrazione cloud, 
decisioni architetturali, testing) e degli script di download e generazione dati
- [ ] **Milestone 03**: dashboard interattiva in Looker Studio collegata alla pipeline via Google Sheets

---

<br/>

## Autore

[Alessandro Attene](https://www.linkedin.com/in/aleattene)

---

<br/>

## Licenze

Questo **progetto** è distribuito con [Licenza MIT](../LICENSE).

Il dataset **OULAD** è distribuito con licenza [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/).
