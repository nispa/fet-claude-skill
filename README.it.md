# FET skill per Claude

[English](README.md) · **Italiano**

Repository: <https://github.com/nispa/fet-claude-skill>

Skill per [Claude Code](https://claude.com/claude-code) che permette a Claude di lavorare con
**[FET — Free Evolutionary Timetabling](https://lalescu.ro/liviu/fet/)**, il risolutore open
source di orari scolastici e universitari. Serve a:

- **controllare** un file `.fet` prima di risolverlo: riferimenti rotti, giorni e ore inesistenti
  nei vincoli, carico di docenti e classi confrontato con gli slot liberi;
- **risolverlo** con `fet-cl` (FET da riga di comando), interpretando l'esito. Se FET fallisce,
  dice *perché*: dati rifiutati con il messaggio di FET, oppure tempo scaduto con l'attività su
  cui la ricerca si è bloccata;
- **verificare** l'orario prodotto in modo indipendente da FET (sovrapposizioni, indisponibilità,
  attività non piazzate) ed **esportarlo** in CSV o JSON, anche per un solo gruppo o docente;
- scrivere o correggere **generatori** di file `.fet`, con un riferimento pratico al formato.

Gli script usano solo la libreria standard di Python (3.8+) e stampano i messaggi in inglese;
Claude risponde comunque nella lingua dell'utente. FET **non** è incluso: va installato a
parte (vedi sotto).

## Requisiti

1. **Python 3.8 o successivo.**
2. **FET**, scaricabile da <https://lalescu.ro/liviu/fet/download.html>:
   - *Windows*: scaricare lo zip ed estrarlo in una cartella qualsiasi, ad es. `C:\FET`;
   - *Linux*: pacchetto `fet` della distribuzione (es. `sudo apt install fet`) o sorgenti;
   - *macOS*: sorgenti, seguendo il README di FET.

Il percorso d'installazione è libero. Al primo uso Claude esegue `fet_setup.py`, che cerca
`fet-cl` nel `PATH` e nelle cartelle usuali. Se non lo trova, Claude chiede il percorso e lo
salva in `~/.config/fet-skill/config.json`. Si può anche impostarlo a mano:

```bash
python skills/fet/scripts/fet_setup.py --set "C:\FET\fet-7.10.5"      # file o cartella
# oppure la variabile d'ambiente FET_CL=/percorso/di/fet-cl
```

## Installazione

### Come plugin di Claude Code, da questo repository (consigliato)

Il repository è anche un piccolo marketplace di plugin. Dentro Claude Code:

```
/plugin marketplace add nispa/fet-claude-skill
/plugin install fet@fet-skill
```

Gli aggiornamenti arrivano con `/plugin marketplace update fet-skill`.

### Come skill personale (copia manuale)

```bash
git clone https://github.com/nispa/fet-claude-skill
```

Copiare la cartella `skills/fet` in `~/.claude/skills/fet` (Windows:
`%USERPROFILE%\.claude\skills\fet`). La skill è disponibile in tutti i progetti.

### In un solo progetto

Copiare `skills/fet` in `<progetto>/.claude/skills/fet` e versionarla con il progetto.

### In claude.ai

Comprimere la cartella `skills/fet` in uno zip e caricarlo da *Impostazioni → Capacità → Skill*.
Nota: in claude.ai gli script girano nell'ambiente di Claude, dove FET di norma non è
installato. Lì la skill è utile soprattutto per scrivere e controllare file `.fet` e per
leggere i risultati caricati.

## Uso

Non servono comandi particolari: basta chiedere a Claude, ad esempio

> Risolvi `orario.fet` con FET e dimmi se ci sono problemi.
>
> Perché FET non trova una soluzione per questo file?
>
> Esporta in CSV l'orario della classe 3B dalla soluzione di FET.

oppure invocarla esplicitamente con `/fet`. Gli script si possono usare anche da soli:

```bash
python skills/fet/scripts/fet_setup.py                       # FET c'è? dove?
python skills/fet/scripts/fet_inspect.py orario.fet          # controlli statici
python skills/fet/scripts/fet_run.py orario.fet --seconds 600 --language it
python skills/fet/scripts/fet_timetable.py orario.fet <cartella>/timetables/orario/orario_activities.xml --csv orario.csv
```

| Exit code di `fet_run.py` | Significato |
|---|---|
| 0 | soluzione trovata (ultima riga `TIMETABLE: <percorso di *_activities.xml>`) |
| 2 | tempo scaduto: stampa l'attività bloccante e la soluzione parziale migliore |
| 3 | FET ha rifiutato i dati: stampa i messaggi di `logs/errors.txt` |
| 4 | `fet-cl` non trovato: stampa come installarlo |

## Struttura

```
.claude-plugin/
  plugin.json          manifest del plugin
  marketplace.json     permette /plugin marketplace add su questo repository
skills/fet/
  SKILL.md             istruzioni per Claude
  reference.md         formato .fet, vincoli, file prodotti da fet-cl
  scripts/             fet_setup · fet_inspect · fet_run · fet_timetable · fet_common
```

## Compatibilità

Provata con FET 7.10.5 su Windows 11, su file in formato FET 5.x e 7.x. I messaggi di FET
vengono riconosciuti in inglese e in italiano (`--language`).

## Licenza

Codice della skill: MIT (vedi `LICENSE`). FET è un programma separato, distribuito con licenza
AGPL v3 dal suo autore, Liviu Lalescu; questa skill non ne contiene alcuna parte.
