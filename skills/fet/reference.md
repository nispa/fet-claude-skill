# Formato `.fet` — riferimento pratico

Verificato su FET 7.10.5, che legge anche i file `version="5.x"` e li converte (compare un
avviso in `warnings.txt`, innocuo). Un tag sbagliato fa rifiutare **l'intero** file, spesso senza
indicare la riga: usare solo tag visti in un file salvato dalla GUI.

## Scheletro

```xml
<?xml version="1.0" encoding="UTF-8"?>
<fet version="5.47.0">
<Institution_Name>…</Institution_Name>
<Comments>…</Comments>
<Days_List><Number_of_Days>5</Number_of_Days><Day><Name>Lun</Name></Day>…</Days_List>
<Hours_List><Number_of_Hours>6</Number_of_Hours><Hour><Name>08-09</Name></Hour>…</Hours_List>
<Subjects_List><Subject><Name>Matematica</Name></Subject>…</Subjects_List>
<Activity_Tags_List></Activity_Tags_List>
<Teachers_List><Teacher><Name>Rossi</Name><Comments></Comments></Teacher>…</Teachers_List>
<Students_List>
  <Year><Name>1A</Name><Number_of_Students>0</Number_of_Students>
    <!-- facoltativi: <Group><Name>1A-lat</Name>…<Subgroup><Name>…</Name></Subgroup></Group> -->
  </Year>
</Students_List>
<Activities_List>…</Activities_List>
<Buildings_List></Buildings_List>
<Rooms_List><Room><Name>Aula1</Name><Building></Building><Capacity>30</Capacity><Virtual>false</Virtual><Comments></Comments></Room></Rooms_List>
<Time_Constraints_List>
  <ConstraintBasicCompulsoryTime><Weight_Percentage>100</Weight_Percentage><Active>true</Active><Comments></Comments></ConstraintBasicCompulsoryTime>
  …
</Time_Constraints_List>
<Space_Constraints_List>
  <ConstraintBasicCompulsorySpace><Weight_Percentage>100</Weight_Percentage><Active>true</Active><Comments></Comments></ConstraintBasicCompulsorySpace>
</Space_Constraints_List>
</fet>
```

Giorni e ore sono **etichette libere**, e i vincoli li citano per nome: il nome deve coincidere
alla lettera. Le ore non devono essere per forza consecutive nel tempo reale: una pausa pranzo si
modella semplicemente non creando lo slot (`12-13` seguito da `15-16`). Attenzione però: FET
considera **adiacenti** due slot consecutivi nella lista, quindi un'attività da 2 h può cadere a
cavallo della pausa. Se non deve, rendere indisponibile lo slot prima della pausa o usare una
`Break`.

## Attività

```xml
<Activity>
  <Teacher>Rossi</Teacher>            <!-- 0..n docenti -->
  <Subject>Matematica</Subject>
  <Students>1A</Students>             <!-- 0..n insiemi di studenti: più tag = lezione comune -->
  <Students>1B</Students>
  <Duration>2</Duration>              <!-- slot consecutivi -->
  <Total_Duration>4</Total_Duration>  <!-- somma delle Duration delle attività con lo stesso Group_Id -->
  <Id>1</Id>                          <!-- unico -->
  <Activity_Group_Id>1</Activity_Group_Id>  <!-- attività "sorelle" (split); 0 se da sola -->
  <Active>true</Active>
  <Comments></Comments>
</Activity>
```

- **Lezione comune a più classi** (mutuazione, accorpamento): *una* attività con più
  `<Students>`, non N attività legate da vincoli. Le ore non si contano due volte e FET
  impedisce da sé che le classi abbiano altro in quello slot.
- Un corso da 12 h in blocchi da 3 si modella con 4 attività, stesso `Activity_Group_Id`,
  `Total_Duration` 12.

## Calendario reale invece della settimana tipo

FET produce un orario **settimanale ripetuto**. Per date puntuali («no il 22 ottobre», «dal 3
ottobre», termine diverso per classe) usare i giorni come **date**: `<Day><Name>Lun 05/10</Name></Day>`
per ogni giorno del periodo. Tutte le esclusioni diventano `Not_Available_Time`. Costo: file
grandi (1-2 MB con ~90 giorni), che FET gestisce comunque bene.

## Vincoli di tempo usati spesso (tag verificati)

| Tag | Campi principali | Uso |
|---|---|---|
| `ConstraintTeacherNotAvailableTimes` | `Weight_Percentage`, `Teacher`, `Number_of_Not_Available_Times`, `Not_Available_Time{Day,Hour}` | disponibilità dei docenti |
| `ConstraintStudentsSetNotAvailableTimes` | idem con `Students` | fascia oraria delle classi, fine anticipata |
| `ConstraintTeacherMaxHoursDaily` | `Teacher_Name`, `Maximum_Hours_Daily` | max ore/giorno per docente |
| `ConstraintTeachersMaxHoursDaily` | `Maximum_Hours_Daily` | lo stesso per tutti i docenti |
| `ConstraintStudentsSetMinHoursDaily` | `Students`, `Minimum_Hours_Daily`, `Allow_Empty_Days` | niente giornate vuote (`false`) |
| `ConstraintStudentsSetMaxHoursDaily` | `Students`, `Maximum_Hours_Daily` | |
| `ConstraintActivitiesPreferredTimeSlots` | `Teacher_Name`, `Students_Name`, `Subject_Name`, `Activity_Tag_Name` (vuoti = tutti), `Duration` (facoltativo), `Number_of_Preferred_Time_Slots`, `Preferred_Time_Slot{Preferred_Day,Preferred_Hour}` | limitare *dove* possono cadere certe attività, ad esempio le lezioni da 3 h solo nei feriali |
| `ConstraintActivityPreferredStartingTime` | `Activity_Id`, `Preferred_Day`, `Preferred_Hour`, `Permanently_Locked` | fissare una lezione |
| `ConstraintMinDaysBetweenActivities` | `Consecutive_If_Same_Day`, `Number_of_Activities`, `Activity_Id`…, `MinDays` | spalmare le lezioni di un corso su giorni diversi (di solito peso 95) |
| `ConstraintActivitiesSameStartingTime` | `Number_of_Activities`, `Activity_Id`… | simultaneità: **non** serve per le lezioni comuni, vedi sopra |

Ogni vincolo termina con `<Active>true</Active><Comments>…</Comments>`. `Weight_Percentage`
100 = inderogabile; sotto 100 FET può violarlo, e le violazioni finiscono in `*_soft_conflicts.txt`.

**Cosa FET non sa esprimere** (serve un controllo esterno, o si ristruttura la griglia):
«al massimo N ore *in un giorno specifico*», vincoli condizionali («se c'è X il sabato allora il
sabato è di pomeriggio»), date di fine da ottimizzare. Si calcolano fuori (ad es. CP-SAT) e si
passano a FET come indisponibilità.

## Risultati di `fet-cl`

```
<outputdir>/
  logs/result.txt                 "Generation successful" | "Time exceeded" | "Cannot precompute - data is wrong - aborting"
  logs/errors.txt                 blocchi "Title:/Message:" con la causa quando i dati sono rifiutati
  logs/warnings.txt               avvisi (es. conversione da formato FET-5)
  logs/max_placed_activities.txt  "…reached N activities placed": ultima riga = massimo raggiunto
  logs/initial_order.txt          "No: k, Id: …, Teachers: …, Students: …" → l'attività k=N+1 è quella bloccante
  timetables/<nome>/<nome>_activities.xml      <Activity><Id/><Day/><Hour/><Room/></Activity>
  timetables/<nome>/<nome>_data_and_timetable.fet   dati + orario bloccato, da riaprire nella GUI
  timetables/<nome>/*.html, *_soft_conflicts.txt
  timetables/<nome>-highest/ , <nome>-current/      solo con tempo scaduto: soluzioni parziali
```

Nelle soluzioni parziali le attività non piazzate hanno `<Day></Day>` vuoto. Exit code di
`fet-cl`: 1 se i dati sono rifiutati, **0 anche con tempo scaduto**. Leggere sempre `result.txt`.

La GUI salva per default in `~/fet-results/timetables/<nome>[-N]/`, con un suffisso crescente a
ogni generazione.

## Opzioni utili di `fet-cl`

`--inputfile=F --outputdir=D --timelimitseconds=S --language=it|en_US --htmllevel=0..7
--exportcsv=true --overwritecsv=true --writetimetablesteachers=false … --verbose=true`
Semi riproducibili: `--randomseeds10=… --randomseeds11=… --randomseeds12=… --randomseeds20=…
--randomseeds21=… --randomseeds22=…`. Si può fermare la generazione con SIGTERM/SIGBREAK
(scrive comunque current/highest). Elenco completo: `fet-cl --help`.
