# The `.fet` format — practical reference

Checked against FET 7.10.5, which also reads `version="5.x"` files and converts them (a harmless
notice appears in `warnings.txt`). A wrong tag makes FET reject the **whole** file, often without
pointing to the line: only use tags you have seen in a file saved by the GUI.

## Skeleton

```xml
<?xml version="1.0" encoding="UTF-8"?>
<fet version="5.47.0">
<Institution_Name>…</Institution_Name>
<Comments>…</Comments>
<Days_List><Number_of_Days>5</Number_of_Days><Day><Name>Mon</Name></Day>…</Days_List>
<Hours_List><Number_of_Hours>6</Number_of_Hours><Hour><Name>08-09</Name></Hour>…</Hours_List>
<Subjects_List><Subject><Name>Maths</Name></Subject>…</Subjects_List>
<Activity_Tags_List></Activity_Tags_List>
<Teachers_List><Teacher><Name>Smith</Name><Comments></Comments></Teacher>…</Teachers_List>
<Students_List>
  <Year><Name>1A</Name><Number_of_Students>0</Number_of_Students>
    <!-- optional: <Group><Name>1A-latin</Name>…<Subgroup><Name>…</Name></Subgroup></Group> -->
  </Year>
</Students_List>
<Activities_List>…</Activities_List>
<Buildings_List></Buildings_List>
<Rooms_List><Room><Name>Room1</Name><Building></Building><Capacity>30</Capacity><Virtual>false</Virtual><Comments></Comments></Room></Rooms_List>
<Time_Constraints_List>
  <ConstraintBasicCompulsoryTime><Weight_Percentage>100</Weight_Percentage><Active>true</Active><Comments></Comments></ConstraintBasicCompulsoryTime>
  …
</Time_Constraints_List>
<Space_Constraints_List>
  <ConstraintBasicCompulsorySpace><Weight_Percentage>100</Weight_Percentage><Active>true</Active><Comments></Comments></ConstraintBasicCompulsorySpace>
</Space_Constraints_List>
</fet>
```

Days and hours are **free labels**, and constraints refer to them by name: the name must match
exactly. Hours don't need to be consecutive in real time: a lunch break is modelled simply by
not creating the slot (`12-13` followed by `15-16`). But FET treats two slots that are
consecutive in the list as **adjacent**, so a 2-hour activity may straddle the break. If it must
not, make the slot before the break unavailable or use a `Break`.

## Activities

```xml
<Activity>
  <Teacher>Smith</Teacher>            <!-- 0..n teachers -->
  <Subject>Maths</Subject>
  <Students>1A</Students>             <!-- 0..n student sets: several tags = shared lesson -->
  <Students>1B</Students>
  <Duration>2</Duration>              <!-- consecutive slots -->
  <Total_Duration>4</Total_Duration>  <!-- sum of the Durations of activities with the same Group_Id -->
  <Id>1</Id>                          <!-- unique -->
  <Activity_Group_Id>1</Activity_Group_Id>  <!-- "sibling" activities (split); 0 if alone -->
  <Active>true</Active>
  <Comments></Comments>
</Activity>
```

- **A lesson shared by several classes** (cross-listed course, merged classes): *one* activity
  with several `<Students>`, not N activities tied by constraints. Hours are not counted twice
  and FET itself prevents those classes from having anything else in that slot.
- A 12-hour course in 3-hour blocks is modelled as 4 activities with the same
  `Activity_Group_Id` and `Total_Duration` 12.

## Real calendar instead of a repeating week

FET produces a **repeating weekly** timetable. For one-off dates ("not on 22 October", "from
3 October", a different end date per class) use days as **dates**:
`<Day><Name>Mon 05/10</Name></Day>` for every day of the period. All exclusions become
`Not_Available_Time` entries. Cost: large files (1–2 MB for ~90 days), which FET still handles well.

## Commonly used time constraints (verified tags)

| Tag | Main fields | Use |
|---|---|---|
| `ConstraintTeacherNotAvailableTimes` | `Weight_Percentage`, `Teacher`, `Number_of_Not_Available_Times`, `Not_Available_Time{Day,Hour}` | teacher availability |
| `ConstraintStudentsSetNotAvailableTimes` | same, with `Students` | class time window, early end |
| `ConstraintTeacherMaxHoursDaily` | `Teacher_Name`, `Maximum_Hours_Daily` | max hours per day for a teacher |
| `ConstraintTeachersMaxHoursDaily` | `Maximum_Hours_Daily` | the same for all teachers |
| `ConstraintStudentsSetMinHoursDaily` | `Students`, `Minimum_Hours_Daily`, `Allow_Empty_Days` | no empty days (`false`) |
| `ConstraintStudentsSetMaxHoursDaily` | `Students`, `Maximum_Hours_Daily` | |
| `ConstraintActivitiesPreferredTimeSlots` | `Teacher_Name`, `Students_Name`, `Subject_Name`, `Activity_Tag_Name` (empty = all), `Duration` (optional), `Number_of_Preferred_Time_Slots`, `Preferred_Time_Slot{Preferred_Day,Preferred_Hour}` | restrict *where* some activities may go, e.g. 3-hour lessons on weekdays only |
| `ConstraintActivityPreferredStartingTime` | `Activity_Id`, `Preferred_Day`, `Preferred_Hour`, `Permanently_Locked` | pin a lesson |
| `ConstraintMinDaysBetweenActivities` | `Consecutive_If_Same_Day`, `Number_of_Activities`, `Activity_Id`…, `MinDays` | spread a course's lessons over different days (usually weight 95) |
| `ConstraintActivitiesSameStartingTime` | `Number_of_Activities`, `Activity_Id`… | simultaneity: **not** needed for shared lessons, see above |

Every constraint ends with `<Active>true</Active><Comments>…</Comments>`. `Weight_Percentage`
100 = hard; below 100 FET may break it, and violations are listed in `*_soft_conflicts.txt`.

**What FET cannot express** (needs an external check, or a different grid): "at most N hours *on
one specific day*", conditional constraints ("if X teaches on Saturday, Saturday is in the
afternoon"), end dates to be optimised. Compute them outside (e.g. with CP-SAT) and pass them to
FET as unavailability.

## `fet-cl` output

```
<outputdir>/
  logs/result.txt                 "Generation successful" | "Time exceeded" | "Cannot precompute - data is wrong - aborting"
  logs/errors.txt                 "Title:/Message:" blocks with the cause when the data is rejected
  logs/warnings.txt               notices (e.g. conversion from FET-5 format)
  logs/max_placed_activities.txt  "…reached N activities placed": last line = maximum reached
  logs/initial_order.txt          "No: k, Id: …, Teachers: …, Students: …" → activity k=N+1 is the blocking one
  timetables/<name>/<name>_activities.xml      <Activity><Id/><Day/><Hour/><Room/></Activity>
  timetables/<name>/<name>_data_and_timetable.fet   data + locked timetable, to reopen in the GUI
  timetables/<name>/*.html, *_soft_conflicts.txt
  timetables/<name>-highest/ , <name>-current/      only on time exceeded: partial solutions
```

In partial solutions, unplaced activities have an empty `<Day></Day>`. `fet-cl` exit code: 1
when the data is rejected, **0 even on time exceeded**. Always read `result.txt`. Log and HTML
language follows `--language` (the scripts recognise English and Italian messages).

By default the GUI saves to `~/fet-results/timetables/<name>[-N]/`, with an increasing suffix
at each generation.

## Useful `fet-cl` options

`--inputfile=F --outputdir=D --timelimitseconds=S --language=en_US|it|… --htmllevel=0..7
--exportcsv=true --overwritecsv=true --writetimetablesteachers=false … --verbose=true`
Reproducible seeds: `--randomseeds10=… --randomseeds11=… --randomseeds12=… --randomseeds20=…
--randomseeds21=… --randomseeds22=…`. Generation can be stopped with SIGTERM/SIGBREAK (it still
writes current/highest). Full list: `fet-cl --help`.
