# Analisi della Retention Studentesca — Report Esecutivo

> Open University Learning Analytics Dataset (OULAD) | 32.593 iscrizioni | 7 corsi
>
> Destinatario: Head of Product | Analisi osservazionale — associazioni, non relazioni causali | No ML

---

## Metodologia

Questo report sintetizza i risultati di una pipeline analitica SQL-driven applicata al
dataset OULAD — 32.593 iscrizioni studente-corso distribuite su 7 moduli, con clickstream
comportamentale completo, record delle valutazioni e profili demografici.

**Definizione dell'outcome:** Ogni iscrizione è classificata come *Completato* (Pass o
Distinction) o *Non completato* (Fail o Withdrawn). Questa suddivisione binaria è
coerente con la letteratura OULAD e consente un'analisi di retention pulita.

**Toolkit statistico:**

| Metodo | Utilizzato per | Metriche riportate |
|--------|----------------|---------------------|
| Welch's t-test | Segnali continui vs. outcome | t-statistic, p-value, d di Cohen |
| Test chi-quadrato | Variabili demografiche categoriche vs. outcome | chi-quadrato, p-value, V di Cramér |
| Bonferroni + Benjamini-Hochberg | Correzione per confronti multipli | p-value corretti |
| Bootstrap CI | Gruppi con tassi estremi (es. studenti ghost) | Intervalli di confidenza al 95% |

Tutti i test utilizzano una soglia di significatività alfa = 0,05. L'effect size — non il
p-value — è il criterio primario per classificare i predittori, perché con ~32K osservazioni
anche differenze banali raggiungono la significatività statistica. Non vengono utilizzati
modelli di machine learning. Tutti i risultati sono associazioni osservazionali.

---

## BQ1 — Dove e quando gli studenti abbandonano?

> **Risultato chiave:** Circa un'iscrizione su tre termina con il ritiro esplicito.
> L'abbandono non è casuale — si concentra intorno a tappe del corso, e il suo
> profilo temporale varia tra i moduli.

Tra i 7 moduli OULAD, i tassi di ritiro vanno dall'**11,8%** (modulo GGG) al
**44,2%** (modulo CCC). Il tasso di ritiro complessivo ponderato è circa il **31%**
di tutte le iscrizioni — una quota significativa della popolazione studentesca che non
raggiunge mai il completamento.

Le curve cumulative di abbandono rivelano **profili temporali distinti** per corso. Alcuni
moduli mostrano un'attrizione precoce ripida (pattern di fallimento dell'onboarding),
mentre altri presentano un declino più graduale a metà corso. All'interno dello stesso
modulo, presentazioni (coorti) diverse seguono traiettorie sostanzialmente simili,
suggerendo che il design del corso — non la variazione casuale della coorte — determina
la forma dell'abbandono.

![Curve cumulative di abbandono per tutti i 7 corsi](figures/03_dropout_curves_overlaid.png)

*Le curve cumulative di abbandono mostrano profili temporali distinti per corso. Ogni linea
rappresenta una presentazione del corso, colorata per modulo.*

I **cliff event** — giorni con un numero sproporzionatamente alto di ritiri (sopra il
95° percentile per quel corso) — coincidono con le scadenze delle valutazioni e il rilascio
dei voti. Questi sono azionabili: gli interventi possono essere programmati prima delle
date dei cliff event.

![Principali cliff event di abbandono](figures/03_dropout_cliffs.png)

*Cliff event rilevati tramite soglia p95. I picchi di abbandono più grandi in un singolo
giorno corrispondono a tappe del corso.*

Una quota misurabile di ritiri avviene **prima ancora dell'inizio del corso** (giorno di
dropout < 0). Questi ritiri pre-corso rappresentano puro churn di registrazione — studenti
che si sono iscritti ma non hanno mai fruito di alcun contenuto. Si tratta di un problema
di attivazione, non accademico.

![Ritiri pre-corso per modulo](figures/03_precourse_withdrawals.png)

*Ritiri pre-corso per modulo. Questi studenti necessitano di nudge di onboarding, non di
supporto accademico.*

Sapere *quando* gli studenti se ne vanno solleva la domanda successiva: possiamo prevederlo?

---

## BQ2 — Quali segnali precoci predicono l'abbandono?

> **Risultato chiave:** Tutte le 8 metriche di engagement precoce testate sono
> significativamente associate all'abbandono dopo correzione per confronti multipli
> (8/8 dopo Bonferroni e Benjamini-Hochberg). I predittori più forti sono le metriche
> di volume dell'engagement — giorni attivi e click totali nei primi 28 giorni.

Utilizzando solo i dati dei primi 28 giorni di iscrizione, abbiamo testato 8 segnali
comportamentali per la loro associazione con il completamento finale. L'effect size
(d di Cohen) — non il p-value — è il criterio primario di classificazione, perché con
~32K osservazioni la significatività è facile da raggiungere.

Il **forest plot** sottostante classifica tutti i segnali per effect size assoluto.
Le metriche di volume dell'engagement (giorni attivi, click totali, decile di engagement
intra-corso) dominano la classifica, seguite dall'ultimo giorno attivo e dall'intensità
media dei click.

![Forest plot degli effect size](figures/04_forest_plot_effect_sizes.png)

*Tutti gli 8 segnali classificati per d di Cohen. I punti verdi indicano significatività
dopo correzione Benjamini-Hochberg. Le linee di riferimento verticali segnano le soglie
di effect size piccolo, medio e grande.*

Il contrasto più drammatico è tra gli **studenti ghost** — quelli con zero attività VLE
nei primi 28 giorni — e gli studenti attivi. Gli studenti ghost hanno un tasso di
completamento prossimo allo zero, mentre gli studenti attivi completano a un tasso vicino
alla media della piattaforma. Gli intervalli di confidenza bootstrap al 95% non si
sovrappongono. (Nota: BQ5 amplia questa definizione per includere attività quasi nulla —
≤1 giorno attivo AND <10 click — per catturare l'intero segmento a rischio ai fini del
targeting degli interventi.)

![Tasso di completamento ghost vs attivi](figures/04_ghost_vs_active_completion.png)

*Gli studenti ghost — zero attività VLE nei primi 28 giorni — hanno tassi di completamento
prossimi allo zero. Le barre di errore mostrano intervalli di confidenza bootstrap al 95%.*

La relazione dose-risposta è **monotonica**: più engagement predice costantemente un
completamento più alto, senza soglia né rendimenti decrescenti. Questo significa che il
segnale è utile lungo tutto il suo range, non solo agli estremi.

![Dose-risposta per i segnali principali](figures/04_top_signal_dose_response.png)

*Tasso di completamento per quartile del segnale per i 3 predittori principali. La
relazione è graduata, non binaria.*

Due insight aggiuntivi rafforzano il portafoglio di segnali. La **submission delle
valutazioni** è un potente predittore binario: gli studenti che hanno consegnato almeno
una valutazione nei primi 28 giorni completano a tassi sostanzialmente più alti dei
non-submitter. E la **costanza batte l'intensità** — login giornalieri regolari predicono
il completamento più fortemente di burst ad alto numero di click per sessione.

Questi segnali comportamentali sono forti — ma sono semplicemente proxy della demografia?

---

## BQ3 — Demografia o comportamento: cosa conta di più?

> **Risultato chiave:** Il comportamento domina. Gli effect size comportamentali sono
> multipli rispetto a quelli demografici. All'interno di ogni livello di istruzione,
> l'engagement alto supera drammaticamente l'engagement basso.

Abbiamo testato 6 variabili demografiche categoriche (genere, fascia d'età, livello di
istruzione, fascia IMD, disabilità, regione) e 2 variabili demografiche numeriche
(tentativi precedenti, crediti studiati) contro l'esito di completamento. Tutte le 8 sono
statisticamente significative dopo correzione Benjamini-Hochberg — ma i loro effect size
sono uniformemente deboli. Il predittore demografico più forte (livello di istruzione
più alto) ha una V di Cramér inferiore a **0,13**; tutti gli altri sono sotto **0,11**.

Per contro, le variabili comportamentali (giorni attivi, click totali, submission
valutazioni, intensità click) mostrano effect size diverse volte superiori. Il divario è
netto: i segnali comportamentali predicono l'esito molto più fortemente di qualsiasi
variabile demografica.

![Confronto demografia vs comportamento](figures/05_demographics_vs_behavior_comparison.png)

*Confronto diretto degli effect size demografici e comportamentali. Il divario è
sostanziale — i segnali comportamentali sono costantemente più forti.*

Il test critico: l'engagement riflette semplicemente la demografia? Il grafico di
interazione sottostante mostra che all'interno di **ogni livello di istruzione**, gli
studenti ad alto engagement superano drammaticamente quelli a basso engagement. Uno
studente con un livello di istruzione formale inferiore ma alto engagement ha più
probabilità di completare rispetto a uno studente altamente istruito che non interagisce
con la piattaforma.

![Interazione istruzione × engagement](figures/05_education_engagement_interaction.png)

*All'interno di ogni livello di istruzione, il gap di engagement sovrasta il gap
educativo. Il comportamento è il fattore determinante, non il background.*

Questo risultato ha una **dimensione etica**: i segnali comportamentali sono sia
statisticamente più forti *sia* azionabili. La demografia non può essere cambiata; il
comportamento può essere influenzato attraverso il design della piattaforma. Targetizzare
il comportamento evita le preoccupazioni di equità insite nel profiling demografico.

Il design del corso stesso influenza i livelli di engagement?

---

## BQ4 — Come le caratteristiche dei corsi influenzano la retention?

> **Risultato chiave:** I tassi di completamento variano sostanzialmente tra i 7 moduli —
> dal **37,4%** (CCC) al **70,9%** (AAA), un gap di **33,5 punti percentuali**. Pattern
> suggestivi emergono intorno alla densità delle valutazioni e alla durata del corso, ma
> con soli 7 punti dati non è possibile alcuna conclusione inferenziale.

Il grafico di ranking sottostante mostra l'intera distribuzione. Il modulo AAA trattiene
quasi tre quarti dei suoi studenti; il modulo CCC ne perde quasi due terzi.

![Ranking completamento per corso](figures/06_course_completion_ranking.png)

*I tassi di completamento vanno dal 37,4% al 70,9% tra i 7 moduli OULAD.*

Gli scatter plot esplorativi rivelano pattern suggestivi tra le caratteristiche del design
del corso (densità valutazioni, durata) e i tassi di completamento. Tuttavia, con n = 7,
qualsiasi correlazione è descrittiva, non inferenziale — la correlazione di Spearman
richiede |rho| > 0,79 per la significatività a questa dimensione campionaria.

![Design del corso vs completamento](figures/06_course_design_vs_completion.png)

*La densità delle valutazioni e la durata del corso mostrano associazioni suggestive con
il completamento. Ogni punto è un modulo (mediato sulle sue presentazioni).*

**Avvertenze critiche:** Questi pattern sono confusi da almeno tre fattori: (1) difficoltà
della materia — alcuni moduli insegnano contenuti intrinsecamente più difficili; (2)
auto-selezione degli studenti — studenti più motivati potrebbero scegliere determinati
corsi; (3) investimento istituzionale — l'allocazione delle risorse varia tra i
dipartimenti. Il design del corso è una leva che vale la pena studiare, ma richiede più
dati (più corsi, o variazione sperimentale) per trarre conclusioni.

Attingendo da tutte e quattro le analisi precedenti, proponiamo ora tre interventi concreti.

---

## BQ5 — Top 3 interventi raccomandati

> **Risultato chiave:** Tre interventi basati sul comportamento, ordinati per rapporto
> impatto/costo, coprono insieme la maggioranza degli studenti a rischio. Poiché i
> segmenti si sovrappongono significativamente, un rollout sequenziato evita outreach
> ridondanti.

### Segmenti target

La query BQ5 dimensiona tre segmenti studenteschi definiti da criteri osservabili e
azionabili — non demografici. Tutte le definizioni utilizzano dati comportamentali dei
primi 28 giorni.

| Segmento | Definizione | Dimensione | Tasso di non completamento |
|----------|------------|------------|---------------------------|
| **Studenti ghost** | ≤1 giorno attivo AND <10 click | **5.555** (17,0%) | **92,3%** |
| **Non-submitter** | Nessuna valutazione consegnata nei primi 28 giorni | **11.494** (35,3%) | **71,8%** |
| **Early disengager** | Attività nei giorni 0–14, zero nei giorni 15–28 | **2.213** (6,8%) | **77,8%** |

Tutti e tre i segmenti mostrano tassi di non completamento molto superiori al baseline
della piattaforma (~53%).

### I tre interventi

| | Attivazione Ghost | Checkpoint Valutazioni | Re-engagement Settimana 3 |
|---|---|---|---|
| **Priorità** | 1 — Quick win | 2 — Costruire dopo | 3 — Investire quando pronti |
| **Trigger** | Zero attività VLE entro il giorno 3 | 3 giorni prima della prima scadenza, non consegnato | 3+ giorni consecutivi di inattività dopo attività iniziale |
| **Azione** | Sequenza email: benvenuto giorno 3 + follow-up giorno 7 con link al primo step | Promemoria con anteprima della valutazione e stima del tempo | Email "Ci manchi" con riepilogo progressi e confronto con i pari |
| **Costo** | **Basso** — solo automazione email | **Medio** — trigger consapevoli delle scadenze + calendario del corso | **Medio-Alto** — tracciamento attività in tempo reale + personalizzazione |
| **Evidenza** | BQ2: l'engagement precoce è il predittore più forte; BQ3: comportamento > demografia | BQ2: la submission è un segnale binario chiave; BQ1: cliff alle scadenze | BQ1: cliff di abbandono a metà corso alle settimane 3–4; BQ2: predittore ultimo-giorno-attivo |
| **Stima impatto** | Maggiore — divario più ampio tra segmento e tasso della piattaforma | Medio — divario sostanziale submitter vs non-submitter | Medio — targetizza un failure mode distinto dai ghost |

**Approccio alla stima dell'impatto:** Per ogni intervento, modelliamo scenari di
conversione conservativi (10–25% degli studenti targetizzati cambiano comportamento).
Gli studenti ghost convertiti si assumono raggiungere il tasso medio di completamento
della piattaforma — non quello degli studenti attivi. Gli studenti re-ingaggiati si
assumono raggiungere un tasso a metà tra disimpegnati e costanti. Queste sono assunzioni
deliberatamente conservative.

### Sovrapposizione dei segmenti

Gli studenti ghost e i non-submitter si **sovrappongono fortemente** — uno studente con
zero accesso VLE non può consegnare una valutazione. Questo significa che gli interventi
1 e 2 targetizzano in larga misura la stessa popolazione da angolazioni diverse; il loro
impatto non va sommato ingenuamente. Gli early disengager, per definizione, hanno avuto
attività iniziale — si sovrappongono meno con i ghost, rendendo l'intervento 3 una leva
indipendente che targetizza un failure mode diverso.

![Matrice delle priorità](figures/07_priority_matrix.png)

*Matrice priorità impatto-vs-costo. L'Attivazione Ghost è il chiaro quick win:
segmento più grande, eccesso di non completamento più alto, costo più basso.*

![Sovrapposizione dei segmenti](figures/07_segment_overlap.png)

*Analisi della sovrapposizione dei segmenti. Le barre grigie mostrano studenti
appartenenti a più segmenti. La sovrapposizione ghost–non-submitter è sostanziale.*

---

## Limitazioni e avvertenze

- **Solo dati osservazionali.** Tutti gli effect size e le differenze nei tassi di
  completamento sono associazioni, non relazioni causali. Gli studenti più attivi
  potrebbero essere intrinsecamente più motivati — l'engagement potrebbe essere un
  proxy, non una causa.
- **Dati storici.** OULAD copre le coorti 2013–2014 della Open University (UK).
  I comportamenti degli studenti e le piattaforme di apprendimento online sono
  cambiati significativamente da allora.
- **BQ4 limitato da n = 7.** Con soli 7 moduli, nessuna statistica inferenziale è
  possibile per l'analisi a livello di corso. I pattern sulle caratteristiche del
  design sono ipotesi, non conclusioni.
- **Le stime di impatto sono assunzioni.** I tassi di conversione (10–25%) sono
  proiezioni plausibili basate su benchmark di settore, non su risultati misurati.
  Non esistono dati di A/B testing nel dataset.
- **Nessun dato sui costi.** Le stime dei costi di implementazione (Basso / Medio /
  Medio-Alto) sono qualitative. Lo sforzo ingegneristico effettivo dipende
  dall'infrastruttura della piattaforma esistente.
- **Nota etica.** Tutti gli interventi targetizzano il comportamento, non la
  demografia. L'outreach automatizzato dovrebbe includere meccanismi di opt-out
  per rispettare l'autonomia degli studenti.
