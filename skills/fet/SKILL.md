---
name: fet
description: Interfaccia con FET (Free Evolutionary Timetabling) per orari scolastici e universitari. Usala quando si deve creare, generare, modificare, controllare o risolvere un file .fet, lanciare FET/fet-cl da riga di comando, capire perché FET non trova una soluzione ("Time exceeded", "Cannot precompute - data is wrong"), leggere ed esportare l'orario prodotto (*_activities.xml, CSV, HTML), verificare che un orario rispetti i vincoli, o stampare orari per classe o docente. Si attiva anche con "orario", "timetable", "orario lezioni", "calendario lezioni" quando c'è di mezzo FET.
---

# FET — generare, risolvere e verificare orari

FET è un risolutore di orari open source (<https://lalescu.ro/liviu/fet/>). Si lavora così:
**si scrive un file `.fet` (XML) → lo si risolve con `fet-cl` → si legge e si verifica
`*_activities.xml`**. Questa skill ha uno script per ciascun passaggio, tutti solo con la
libreria standard di Python:

| Script | Cosa fa |
|---|---|
| `scripts/fet_setup.py [--set PERCORSO]` | Trova `fet-cl`, ne verifica la versione, salva il percorso; se FET manca spiega come installarlo |
| `scripts/fet_inspect.py FILE.fet` | Riepilogo e controlli statici **prima** di lanciare FET: riferimenti rotti, giorni/ore inesistenti nei vincoli, carico docenti e studenti confrontato con gli slot liberi |
| `scripts/fet_run.py FILE.fet [--secondi N] [--out DIR]` | Lancia `fet-cl`, interpreta l'esito e, in caso di fallimento, dice **quale attività** ha bloccato FET |
| `scripts/fet_timetable.py FILE.fet SOL.xml [--students G] [--teacher T] [--csv/--json]` | Unisce `.fet` e soluzione, verifica sovrapposizioni e indisponibilità **indipendentemente da FET**, esporta |

Gli script stanno in `scripts/`, accanto a questo `SKILL.md`. La cartella della skill dipende
da come è installata (`~/.claude/skills/fet/`, `<progetto>/.claude/skills/fet/` o la cache dei
plugin): usare la *base directory* indicata al caricamento della skill e lanciare gli script con
il percorso completo, ad es. `python "<base>/scripts/fet_run.py" orario.fet`.

## Passo 0 — FET è installato? (sempre, prima di lanciare qualcosa)

```
python fet_setup.py
```

- **exit 0**: stampa il percorso di `fet-cl` e la versione. Si procede.
- **exit 1**: FET manca o non è stato trovato. **Fermarsi e chiedere all'utente** di installare
  FET e di indicare il percorso di `fet-cl` (o della cartella di FET). Riportargli le istruzioni
  stampate dallo script (download da <https://lalescu.ro/liviu/fet/download.html>). Non
  cercare FET sul disco a tentativi e non installarlo senza il suo consenso. Avuto il percorso:
  `python fet_setup.py --set "<percorso>"`. Lo script verifica che si avvii e lo salva in
  `~/.config/fet-skill/config.json`, così le volte successive non serve più chiederlo.

Ordine di ricerca: `--fet-cl` → variabile `FET_CL` → configurazione salvata → `PATH` →
cartelle d'installazione usuali. Se il percorso viene trovato solo con la ricerca nelle cartelle
usuali, proporre all'utente di fissarlo con `--set`. Nella cartella di `fet-cl` c'è anche
l'interfaccia grafica (`fet.exe` / `fet`), utile all'utente per aprire e ritoccare a mano i risultati.

Serve solo Python 3.8+ con la libreria standard; nessun pacchetto da installare.

## Procedura

1. **Costruire il `.fet` con uno script** (Python o altro), mai scriverlo a mano: centinaia di
   `Not_Available_Time` sono ingestibili a mano e rigenerare è l'unico modo di tenere i dati
   coerenti. Se il progetto ha già un generatore, le correzioni vanno lì, non nel `.fet`.
   Formato, tag e trappole: **leggere `reference.md`** prima di scrivere o modificare un generatore.
2. `python fet_inspect.py file.fet`: deve chiudersi senza `ERRORI`. Un `IMPOSSIBILE` qui
   significa che FET fallirà comunque.
3. `python fet_run.py file.fet --secondi 600`: interpretare l'exit code.
   - **0**: soluzione trovata. L'ultima riga `ORARIO: …` è il percorso di `*_activities.xml`.
   - **2, tempo scaduto**: lo script stampa l'attività numero N+1 dell'ordine iniziale, cioè quella
     su cui FET si è fermato, e il percorso della soluzione parziale (`<nome>-highest`).
     Quasi sempre il problema è quell'attività o una risorsa che condivide: docente troppo
     vincolato, gruppo saturo, durata che non entra in nessuna finestra.
   - **3, dati rifiutati** (`Cannot precompute - data is wrong`): i messaggi di `logs/errors.txt`
     dicono cosa non torna, ad esempio «number of hours for subgroup is 198 and you have only
     136 free slots».
   - **4**: `fet-cl` non trovato: tornare al passo 0.
4. `python fet_timetable.py file.fet <ORARIO> --quiet`: **verificare sempre**, anche se FET dice
   "successful". Deve riportare 0 violazioni e 0 non piazzate. Aggiungere poi controlli specifici
   del progetto, per le regole che il `.fet` non sa esprimere.
5. Consegna: FET scrive già HTML per gruppi, docenti, aule (`timetables/<nome>/*.html`) e con
   `--extra --exportcsv=true` anche i CSV. Per stampe su misura (una pagina per classe,
   colori per materia, righe vuote tolte) conviene generare un HTML proprio da
   `fet_timetable.py --json`.

## Buone regole

- **Diagnosticare prima di allentare.** Se FET non trova la soluzione, non ammorbidire vincoli
  alla cieca: leggere l'attività bloccante e il carico in `fet_inspect.py`. Per sapere se un
  problema è davvero impossibile, un modello CP-SAT (OR-Tools) dà una **prova**, FET no: FET
  è euristico e un "Time exceeded" non dimostra nulla.
- I vincoli con `Weight_Percentage` < 100 sono preferenze: FET può violarli. Le regole
  inderogabili vanno al 100%.
- FET, dopo averlo aperto, può riscrivere il file in un formato più nuovo (`version="7.x"`). Il
  file salvato dalla GUI è la migliore fonte per nomi di tag nuovi o dubbi.
- Una soluzione di FET dipende dal seme casuale: due esecuzioni danno orari diversi, entrambi
  validi. Se l'utente ha già stampato o approvato un orario, lavorare su **quella** soluzione
  (cercarla in `~/fet-results/timetables/`, la cartella di default della GUI), non rigenerarla.
- Non trattare `logs/warnings.txt` come errori: spesso contiene solo la conversione di formato.
