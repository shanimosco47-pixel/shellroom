# מתכנן ייצור ליבוש קליפות — מסמך לביקורת עמיתים

> **מטרת המסמך:** לתעד בפירוט את הפרויקט, את האתגרים המרכזיים, ואת ההחלטות שנתקבלו במהלך היישום, כדי שיהיה אפשר להעביר אותו לביקורת של עמיתים לפני שהקוד עולה לפרודקשן. בסוף המסמך — רשימה מפוקרטת של נקודות שבהן אני צריך עין נוספת.

---

## 1. רקע עסקי ותיאור הסביבה הפיזית

### 1.1 החברה
**קבירן (1991) בע"מ** — יצרנית של יציקת־השקעה (investment casting). מפעל בו נוצקות מתכות בתבניות קליפות קרמיות חד־פעמיות. הקליפה נבנית על־ידי טבילה חוזרת של מודל שעווה בבוץ קרמי ויבוש ביניהן.

### 1.2 תחנת ייבוש הקליפות (`Shell Drying Station`)
ליבת הפרויקט. המבנה הפיזי:

- **שני מסועים סגורים בצורת O** המקיפים את אזור הייבוש:
  - מסוע Prime — 38 ווי־תליה (19 זוגות, שתי עמודות)
  - מסוע Backup — 76 ווי־תליה (19 שורות × 4 עמודות)
- **רובוט בודד על ציר שביעי** (7th axis) — מעביר קליפה אחת בלבד בכל רגע נתון בין התחנות השונות. זה **צוואר הבקבוק המרכזי** של כל המערכת.
- **תחנת סנדבלאסט (ניקוי חול)** — אופליין לרובוט, מופעלת ידנית על־ידי אופרטור.
- **רצפת ייבוש** — קליפות יורדות מהווים וממתינות 12 שעות נוספות.

### 1.3 מחזור החיים של אצווה (38 קליפות)

| שלב | פעולה | מבצע | משך טיפוסי |
|-----|-------|-------|-----------|
| Hang | תליית הקליפות על מסוע Prime | אופרטור | ~2h |
| Dip 1 | טבילת ציפוי ראשון | רובוט | ~10h |
| Sand | ניקוי חול בין Dip 1 ל־Dip 2 | אופרטור | ~45 דק' |
| Dip 2 | טבילת ציפוי שני על Prime | רובוט | ~10h |
| Dip 3–7 | חמש טבילות נוספות על Backup | רובוט | ~8h ל־dip |
| Seal | ציפוי אטימה אחרון | רובוט | ~12h |
| Hang-dry | יבוש על הווים | פסיבי | 12h |
| Unhang | הורדת הקליפות מהווים לרצפה | אופרטור | ~2h |
| Floor-dry | יבוש על הרצפה | פסיבי | 12h |
| DeWax-ready | הקליפה מוכנה לפירוק שעווה | — | — |

**אילוצים פיזיים כבדים:**
- רובוט יחיד — כל פעולת טבילה סריאלית.
- `dryAfter` — "שער ייבוש" בין טבילות: הטבילה הבאה לא יכולה להתחיל עד שחלף זמן ייבוש מינימלי מהקודמת.
- התחנת סנדבלאסט חייבת לסיים לפני שה־Prime יכול לעבור ל־Dip 2.
- קליפה אחת = ~₪13,000 בהכנסה פוטנציאלית (ל־KPI הכספי).

---

## 2. האתגר שהפרויקט בא לפתור

### 2.1 הבריף המקורי
מנהל הייצור של קבירן מבקש **אפליקציית web חד־קובצית** (ללא backend, ללא build step) שתעזור לו:

1. **לצפות במצב חי** של תחנת הייבוש — מה בכל ווה, איפה הרובוט, מי בציפוי איזה.
2. **לחזות 7 ימים קדימה** — להציג Gantt / dashboard של מה יקרה בשבוע הקרוב לפי פרמטרים נוכחיים.
3. **לתעד זמני השבתה** (downtime) וסיומי מחזור בפועל — לצורך השוואה בין תכנון לביצוע.
4. **לנעול תוכנית** ולראות סטייה ממנה.
5. **להציע אופטימיזציות** לתכנון — עורך המערכת רוצה לראות "מה קורה אם שיניתי סדר אצוות" או "אם קיצרתי ציפוי 3".
6. **לתכנן ידנית** — מתכנן הייצור רוצה לגרור משימות ולבנות תוכנית שבועית משלו.

### 2.2 מגבלות טכניות שנקבעו
- **קובץ HTML יחיד** — ללא Node, ללא webpack, ללא React.
- Tailwind CSS + Lucide icons דרך CDN; Google Fonts (Inter + Playfair Display).
- כל המצב ב־`localStorage` תחת המפתח `cabiran.shellroom.v1`.
- JavaScript טהור, ללא framework.
- עבודה מקומית בלבד — מתוכננת לרוץ ב־Chrome על מסך 1920×1080.

### 2.3 האתגר העמוק שצמח במהלך הבנייה

מעבר לדרישות הממשק, **האתגר האמיתי** היה לבנות סימולטור אמין של פס הייצור. זאת אומרת:

> **בהינתן מצב התחלתי (מה בכל ווה), זמני מחזור, ולוח עדיפות — לחזות באיזה רגע בדיוק כל קליפה תגיע ל־DeWax-ready, תוך כיבוד של כל האילוצים הפיזיים.**

חישוב זה הוא **לב הפרויקט** — כל טאב אחר (Gantt, Forecast, Planner, Variance) יונק ממנו.

---

## 3. ארכיטקטורה טכנית

### 3.1 מבנה הקובץ
`index.html` יחיד (~100KB). מבנה:
- `<style>` משובץ (בסיסי — רוב העיצוב מגיע מ־Tailwind CDN).
- `<body>` עם 7 טאבים ראשיים:
  1. Live Conveyor — ויזואליזציה חיה של המסועים + הרובוט
  2. Robot Log — רשימת פעולות הרובוט
  3. Planner — לוח תכנון שבועי (נושא המסמך הזה — ראה פרק 5)
  4. Gantt — תרשים Gantt של האצוות
  5. Forecast — KPI חזוי + אופטימייזר
  6. MES Log — טופסי downtime וסיומי מחזור
  7. Plan Lock — נעילת תוכנית והשוואה ביצוע־מול־תכנון
- `<script>` משובץ עם כל הלוגיקה.

### 3.2 ה־state יחיד

```js
state = {
  config: {
    cycleTimes: [15,15,12,12,12,12,12,18],    // דקות לקליפה לכל stage
    postDipDryMin: [15,10,10,10,10,10,10,0],  // dryAfter לכל dip
    sandblast: { durationMin: 45 },
    hangCycleMin: 3, unhangCycleMin: 3,
    robotUptimePct: 92,
    sequence: ['P','P','B','B','B','B','B','B'],
    batchSizes: [38,38,38,38,38,38,38],
    batchPriority: [0,1,2,3,4,5,6],
    taskPriority: [...],   // רשימה שטוחה של (batchIdx, stage) מסודרת לפי עדיפות
    scheduleStrategy: 'pipeline',
  },
  current: {
    nowTs, sessionStartDay, sessionStartHour,
    waitingByBatch:  [38,38,38,38,38,38,38],
    primeByDay:      [0, ...],
    backupByDay:     [0, ...],
    floorByBatch:    [0, ...],
    dewaxedByBatch:  [0, ...],
    confirmed: false,
  },
  batches: [...],   // מושטח מהסנאפשוט
  logs: { downtime: [...], cycles: [...] },
  lockedPlan: null | { savedAt, forecast },
  ui: { page, scrubberMin },
}
```

**כל שינוי** קורא ל־`save()` שכותב את המצב ל־localStorage, ואז `renderAll()` שמחשב את כל התצוגות מחדש.

### 3.3 בניית DOM בטוחה (XSS)

הוכלל איסור שימוש ב־`innerHTML =` עם טקסט שמקורו במשתמש. במקום זאת:
- `el(tag, attrs, children)` לבניית אלמנטים דינמית — attributes עוברים escape אוטומטי, ילדים מוצמדים כ־text nodes אלא אם הם כבר DOM.
- `textContent` לכל טקסט חופשי מהמשתמש (שם קטגוריית downtime, סיבה וכו').
- `setHTML(node, markup)` משמש **רק** עבור markup סטטי שאין בו input משתמש (חלקי SVG של הצ'ארטים).

זה היה הכרחי כי hook של security-guidance plugin מעכב כל edit שמכיל `innerHTML` של תוכן משתמש.

---

## 4. מודל הסימולציה (ליבת המערכת)

### 4.1 הפונקציה `computeForecast(cfg, anchorTsISO)`

מקבלת את ה־config הנוכחי ואת חותמת הזמן של תחילת המחזור, ומחזירה:
```js
{
  batches: [ { batchIdx, role, size, stages: [{stage, startMin, endMin}, ...] } ],
  robotBusyUntil: <minutes>,
  anchorTs: <ISO>,
}
```

### 4.2 שלבי החישוב

**שלב א' — בניית pipeline עצמאי לכל cohort**
- כל אצווה מתחילה מרגע ה־anchor שלה (Batch 0 בשעה 0, Batch 1 בשעה 24, וכו').
- הפונקציה `buildStages(size, startMin, startAt)` בונה את ה־timeline כאילו לרובוט יש משרת אישי לכל אצווה — כלומר, ללא התחשבות באילוץ הרובוט היחיד.
- כל שלב מקבל `startMin` ו־`endMin` ראשוניים לפי `perShellMin × size / uptime`.

**שלב ב' — Single-robot serialization**
הלב של האלגוריתם. אחרי שכל האצוות קיבלו timeline עצמאי, מריצים pass שני שמתאם ביניהן:

1. משטחים את כל ה־stages לרשימה שטוחה של `instances`, כל אחת מסומנת `needsRobot`.
2. ממיינים את ה־instances לפי (א) עדיפות המשתמש ב־`taskPriority`, (ב) `startMin` המקורי, (ג) עדיפות אצווה.
3. מריצים while-loop שמעבד instance־ים לפי סדר המיון:
   - אם `needsRobot === true` — התחלה = `max(batchReady, robotFreeAt)`, מעדכן את `robotFreeAt`.
   - אחרת (Hang, Sand, Unhang, Hang-dry, Floor-dry, DeWax) — התחלה = `batchReady`, **לא נועל את הרובוט** (רץ במקביל).
   - אילוץ: שלב לא ירוץ עד שכל השלבים הקודמים **באותה אצווה** הושלמו.

**שלב ג' — Task-priority override (הגמישות של המתכנן)**

המשתמש יכול לגרור chips ב־Planner כדי לשנות את הסדר שבו הרובוט ישרת את המשימות. רשימת `taskPriority` הוא רשימה שטוחה של `{batchIdx, stage}`. כשהמיון מגלה ששתי משימות רובוטיות מתחרות על זמן הרובוט, דרגת ה־`tp` היא שמכריעה.

### 4.3 הבחנה קריטית: Robot vs Operator

זיהינו במהלך הפיתוח שהנחה שגויה הייתה לטפל ב־Hang/Unhang/Sand כ"עבודת רובוט". בפועל הם **משימות אופרטור** שרצות **במקביל** לעבודת הרובוט. אם אופרטור תולה אצווה חדשה, הרובוט יכול בו־זמנית לטבול אצווה שכבר תלויה. הבחנה זו גרמה לשינוי ב־`ROBOT_STAGES` מ־`[12,0,2,3,4,5,6,7,8,13]` ל־`[0,2,3,4,5,6,7,8]`, שחילצה ~50h של זמן רובוט מדומה לשבוע.

---

## 5. עיצוב ה־Planner (הטאב שעליו הייתה הכי הרבה עבודה)

### 5.1 ההתלבטות הראשונה — ייצוג ויזואלי

**נסיון 1: מטריצה "אצוות × שלבים"**  
שורה לכל אצווה, עמודה לכל stage. חסרונות:
- לא קל לראות מה קורה בכל יום בשבוע.
- הקישור לזמן לא ישיר — המשתמש לא חי במטריצה, הוא חי בלוח שנה.

**נסיון 2: יום כשורה, משימות כ־chips (הגישה הסופית)**
- 7 שורות = 7 ימי השבוע (ראשון עד שבת מבוססות על `sessionStartDay`).
- שורה שמינית אמבר = **Past window** — משימות שלא מספיקות להיכנס ל־168 שעות.
- כל שורה מכילה flex־container של chips בסדר כרונולוגי.
- **Chip solid עם מילוי צבע** = משימה רובוטית (Dip 1-7, Seal).
- **Chip עם border מקווקו + תג "OP"** = משימה אופרטור (Hang, Sand, Unhang).

**למה זה טוב?** המתכנן רואה את היום, את רצף הפעולות בו, ואת הפער בין מה שהרובוט עושה למה שהאופרטור צריך להיות מוכן אליו.

### 5.2 מכניקת הגרירה

היו שני נסיונות כושלים עם HTML5 drag-and-drop (`draggable="true"` + `ondragstart` + `ondrop`). הבעיות:
1. המאזין של השורה חטף את הגרירה במקום המאזין של ה־cell.
2. Drop zones פסדו החוצה כשהמשתמש גרר במהירות.

**הפתרון שנבחר — Click-to-pick / Click-to-place:**
1. לחיצה על chip → chip הופך "picked" (outline כחול נייבי + halo + scale 1.08).
2. לחיצה על chip אחר → ה־chip הראשון נעקר מהרשימה ונדחף למיקום השני.
3. לחיצה על ה־chip הנבחר שוב → ביטול.

**תוספת מאוחרת יותר: "drop zones" בסוף כל שורה:**
באות בלשון `＋ append here`. מאפשרות להוסיף chip **אחרי** ה־chip האחרון ביום נתון — פעולה שלא הייתה אפשרית עד אז.

### 5.3 אילוץ pipeline (`violatesBatchOrder`)

אחרי שני איטרציות ובעיית אמת (guard מידי דוחה כל תנועה בגלל תקלה ב־baseline), הפתרון הסופי:
```
מעבר חוקי אם ורק אם הסדר הפנימי של stages באותה אצווה לא השתנה.
```
כלומר — ניתן להחליף chip של אצווה X עם chip של אצווה Y כל עוד הסדר של כל X־ים בתוך X ושל כל Y־ים בתוך Y לא התהפך. הכלל הקודם "stages חייבים להיות לפי PIPE" נכשל כי ה־baseline עצמו (מצב batch #7 שבו יש cohort שכבר ב־backup + cohort המתנה) מכיל "הפרות" חוקיות של הרצף, ולכן הכלל הקודם דחה גם תנועות שאינן מזיקות.

### 5.4 חישוב "Used / Free" לכל יום

לכל יום מוצגת שורה עם:
- `USED` — כמה זמן רובוט בפועל נעשה באותו יום.
- `FREE` — כמה זמן רובוט פנוי (קיבוע חיווי מרמזור: ירוק > 25%, ענבר 10-25%, אדום < 10%).
- bar גרפי מתחת.

חישוב: עבור כל משימה ב־tp, הצלבנו את טווח `[startMin, endMin]` שלה עם `[d * 1440, (d+1) * 1440]` ואספנו את החיתוכים. משימה שחוצה חצות תורמת את הזמן המתאים לשני הימים. **רק משימות `isRobot === true` נספרות** — אופרטור רץ במקביל ולא תופס זמן רובוט.

### 5.5 גודל אצווה גמיש (תוספת אחרונה)

בעקבות פידבק של המשתמש — שמראה המציאות היא שלא כל אצווה מגיעה ב־38 קליפות (שבר, פסילה, טעינה חלקית) — הוספנו שורת **Size** ב־Opening Position:
- קלט מספרי לכל אצווה (0-38).
- משנה את ה־cap הדינמי של השאר: `min(slotMax, size[i] − othersTotal)`.
- אם המשתמש מוריד size מתחת לסכום נוכחי, המערכת אוטומטית שופכת עודפים מ־Waiting → Floor → DeWax → Backup → Prime (הלא־מחויבים קודם).
- הכנסה מחושבת מחדש: `size × ₪13,000`.

---

## 6. החלטות שיפוט מרכזיות

| החלטה | אופציה נבחרה | למה |
|---------|----------------|------|
| ייצוג זמן בסימולטור | דקות מאז anchor | שברי שעה רלוונטיים; יותר מדויק מ־Date object בחישובים |
| גרירה | Click-to-pick/place | HTML5 drag נכשל באופטימיזציה של grids מקוננים |
| guard על reorder | per-batch sequence preservation | הכלל הקודם נכשל על in-flight batches |
| סדר ברירת מחדל של tp | FIFO לפי startMin | תאם לתוכנית רפרנס שסופקה ב־Excel (שחיברתם); batch-major הייתה טעות |
| robot vs operator | 8 stages רובוט, 3 operator | דירגנו זאת אחרי פידבק מהמשתמש שזיהה שאופרטור עובד במקביל |
| per-batch size | שורת Size במקום שדה יחיד | החלוקה הוויזואלית הברורה יותר, חוסך אנדרסון |

---

## 7. מה שעבד טוב

- **localStorage persistence** — חסר לחלוטין אובדן מידע בין refreshים.
- **מפה פונקציונלית אחת של state → UI** — קל להוסיף תצוגות חדשות, כל אחת יונקת מ־`computeForecast`.
- **ה־scrubber** — גרירה משנה את הזמן הנצפה לכל התצוגות באותו frame.
- **Planner chips** — ברורים ויזואלית, ההבחנה robot vs operator נקלטת מהר.
- **הפרדה קשיחה בין מוסברנות (forecast) לתצוגה (render*)** — הקוד נשאר פחות מבולבל גם אחרי 7 טאבים.

---

## 8. מה שעדיין פתוח / באגים מוכרים

### 8.1 (חשוב) — סימולטור מתזמן לא תמיד אופטימלי
במצב ברירת מחדל (7 אצוות × 38 קליפות), הסימולטור מזיז חלק מהעבודה של Batch #2 ל־"Past Window" גם כשלוגיקה רגילה הייתה אמורה לפצל אותה טוב יותר. בפרט ראינו בחקירה:
```
B2 Dip 1-4 ב־Sunday/Monday, B4 Dip 1-Seal על החלון, B6 על החלון,  
חזרה ל־B2 Dip 5-Seal ב־Friday+.
```
הסבר אפשרי: הסידור של instances במערך לפי tp rank + startMin גורר מצבים שבהם אצווה אחת "מאבדת את התור" כשה־dryAfter שלה גדול מזמן של משימה אחרת שמוכנה. לא נבדק עד הסוף.

### 8.2 Live Conveyor לא משקף batch size קטן
אם אצווה = 20, הוויזואליזציה עדיין מציירת 38 מעגלי־ווים. הוסכם להוסיף טקסט קטן "20 of 38 loaded" מעל כל עמודה.

### 8.3 "FREE" יכול לבלבל
המספר "4h free" כולל בתוכו זמני המתנה פיזיים (Hang של 2h, Sand של 45m, dryAfter) שאי־אפשר להפוך למשימה חדשה. שינוי השם ל־"Robot idle (blocked)" או הוספת פירוק בצידו עשויים לעזור.

### 8.4 האופטימייזר פשוט מדי
כיום הוא מתבסס על permutations של `batchPriority` + נסיונות swap בין שני cells שכנים. לא מתחשב באופטימיזציית cycleTimes באמת. יכול להיות שילוב של חיפוש simulated annealing על-גבי מספר שלבים.

### 8.5 עלולים להיות שני סבבי Sand Blast
בקובץ Excel שהמשתמש סיפק (`dipping plan 20 hangers.xlsx`), יש SB גם אחרי coat 1 וגם אחרי coat 2. הסימולטור שלנו עושה רק SB אחד — יש לאמת עם הלקוח האם שתי תחנות שתיהן קיימות.

---

## 9. נקודות שהייתי רוצה לקבל עליהן ביקורת עמיתים

הנה הרשימה המפורטת של מה שאני רוצה עין נוספת עליו. מסודרת לפי עדיפות:

### 9.1 (הכי חשוב) — **נכונות מודל הסימולציה**
**שאלה:** האם אלגוריתם ה־`single-robot serialization` (`computeForecast`, פונקציה שורות ~1015–1107 ב־`index.html`) באמת מייצג את המציאות הפיזית של המפעל?
- האם ההנחה ש־Hang/Unhang/Sand אינם נועלים את הרובוט **תמיד** נכונה?
  - מה אם אותו טכנאי שמפעיל את הרובוט גם תולה את האצווה הבאה?
  - מה אם התחנה של הסנדבלאסט ממש צמודה לפס ולכן גם חוסמת תנועת רובוט?
- האם האילוץ של `dryAfter` מיושם נכון? בפרט — האם שער הייבוש צריך להיות **קשיח** (הטבילה הבאה ממש מחכה) או **גמיש** (הרובוט יכול להתחיל את ההכנה מוקדם יותר ולחכות על יד הטנק)?

### 9.2 (חשוב מאוד) — **בחירת default מתאימה ל־`taskPriority`**
**שאלה:** האם FIFO־by־startMin הוא באמת הבחירה הנכונה?
- במהלך הפיתוח ניסיתי batch-major (אצווה שלמה לפני הבאה) — גרם ל־`robot idle 50h` גדול.
- חזרתי ל־FIFO — פרוס על 7 אצוות של 38 קליפות, **אפס** אצוות מגיעות ל־DeWax באותו שבוע.
- לפי ה־Excel שמשתמש סיפק (בגודל 20 קליפות × 7 coats בלבד), 16 אצוות מגיעות בשבוע — אבל שם ה־cycle times שונים ב־2-3x.

**שאלות ספציפיות:**
1. האם יש אסטרטגיה אלגוריתמית טובה יותר שבה אפשר להשתמש? (SPT? EDF? LPT?)
2. האם שווה להוסיף simulated annealing כבחירה של ברירת־מחדל, על חשבון זמן חישוב?

### 9.3 (תכנוני) — **ארכיטקטורה של single-file**
**שאלה:** `index.html` מגיע ל־~100KB של קוד JS בתוך אותו קובץ. האם זה באמת המבנה הנכון?
- לטובת האתגר שנקבע: כן. לטובת maintainability ארוך טווח: לא.
- האם שווה לשקול לעבור ל־Vite + TypeScript ולהוריד את הכבד מה־HTML, גם במחיר של build step?
- פונקציות כגון `renderPlanner` הגיעו ל־200+ שורות. חלוקה לקבצים?

### 9.4 (UI/UX) — **התנהגות הגרירה**
**שאלה:** האם click-to-pick/place הוא באמת חלופה טובה ל־HTML5 drag?
- יתרונות: דטרמיניסטי, עובד בכל browser, קל לדבג.
- חסרונות: שונה ממה שמשתמשים מצפים ב־web modernי, דורש הסברים מילוליים.
- אלטרנטיבה: ספריית drag־and־drop מוכנה (SortableJS למשל) שלא ידרוש CDN.

### 9.5 (נתונים) — **מודל המצב הראשוני (Opening Position)**
**שאלה:** האם 5 שורות (Waiting, Prime, Backup, Floor, DeWax) + שורת Size בראש זה מודל נכון?
- חסר: זמן בתוך ה־cohort. כלומר — אם Batch 7 יש לה 18 קליפות על Backup, באיזה **dip** בדיוק הן נמצאות? (Dip 3? Dip 5?)
- נקבע שרירותית שהן ב־hang-dry, אבל זה לא בהכרח נכון. יש כאן מודל שעשוי להיות מדויק יותר.

### 9.6 (בטיחות) — **הגנות XSS**
**שאלה:** האם ה־`el()` helper + `textContent` פוסק את כל וקטורי ה־XSS?
- כרגע הכל עובר דרך אחד מהשניים, אבל יש `setHTML` אחד (לצ'ארט DeWax) שקורא templates סטטיים. האם זה חשוף למשהו שלא חשבתי עליו?
- ב־localStorage יכול להיות מצב שהוזרק אליו JS דרך export/import בעתיד — כדאי לבדוק.

### 9.7 (ביצועים) — **computeForecast על כל render**
כל פעולת משתמש (לחיצה על chip, שינוי cycle time) מריצה `renderAll` שמריץ `computeForecast` מאפס. סיבוך: `O(batches × stages × iterations)` = `~7 × 14 × 4 = 400` פעולות לכל render. בפועל זה מהיר (<50ms) אבל:
- האם יש mechanism של memoization שכדאי להוסיף?
- האם שווה להפריד render לעדכונים מדוריים?

### 9.8 (נגישות) — **צבעים + keyboard**
- הצבעים של 7 האצוות פסטליים — האם יש קונטרסט מספיק לאנשים עם פגמי ראייה?
- ה־Planner מיישרת click אבל אין keyboard navigation. האם זה מקובל לכלי פנים־מפעלי?
- אין `aria-label` על ה־chips. שווה להוסיף?

### 9.9 (בדיקות) — **חוסר tests כלל**
אין אף test unit בפרויקט. עבור אלגוריתם קריטי כמו `computeForecast`, זה מטריד:
- האם כדאי לבנות snapshot tests של "בהינתן state X, forecast הוא Y"?
- מה היינו ממליצים להוריד ל־QA:
  - תרחיש 1: Opening Position ריק → 7 אצוות → ודא ש־Batch 1 dewax בשעה ~100.
  - תרחיש 2: Batch 7 עם 18 על backup → Unhang קורה ב־hour ~22 של יום 1.
  - תרחיש 3: שינוי Dip 1 מ־15 ל־10 → forecast צריך להזדרז ב־~40 דק' לאצווה.

### 9.10 (נתונים עתידיים) — **האופטימייזר**
כרגע האופטימייזר מייצר 20-30 candidates לפי תמורות של `batchPriority`. האם:
- שווה להוסיף חיפוש על `cycleTimes` (±2 דק' לכל stage)?
- שווה להשתמש ב־genetic algorithm?
- האם כדאי לאפשר למשתמש לקבוע "fixed constraints" (לדוגמה — "Batch #3 חייב להסתיים עד יום רביעי") ולחפש תחת האילוצים?

---

## 10. סיכום

**מה נבנה:** מתכנן ייצור single-file עם 7 טאבים, כולל ויזואליזציה חיה, Gantt, forecast dashboard, תכנון ידני עם גרירה, MES log, ונעילת תוכנית.

**מה עבד:** המודל הפיזי של single-robot serialization + עדכון חי בכל שינוי state. הממשק של Planner (יום כשורה, chips עם זמני סוף) התקבל היטב.

**מה פתוח:** נכונות האלגוריתם על scenarios מגוונים. בדיקה אם batch-major או FIFO הם באמת הנכונים. חוסר tests. אופטימייזר פשוט מדי.

**הערות כלליות לביקורת עמיתים:**
- הפרויקט בנוי כ־prototype איכותי. הפתרון לא designed for scale — אבל designed for evolution.
- מודל ה־state הוא היחיד — כל שינוי עובר דרך `save() → renderAll()`. קל לדבג. קשה לעשות ביצועים.
- ראשי הפרק הם ההחלטות־שיפוט (פרק 6) והנקודות־לביקורת (פרק 9).

תודה על הזמן — אשמח לכל הערה, גם אלו הקטנות.

---

## Review Response Log (Phase 10, April 2026)

After the two peer-review documents landed (`REVIEW_RESPONSE.md` and `peer_review_report.md`),
an approved 10-phase refactor was executed. Every concrete reviewer point is mapped below
to the phase that addressed it.

| # | Reviewer point | Status | Handled in |
|---|---|---|---|
| R1.1 | `computeForecast`'s sort-once-then-walk model causes Batch #2 "lost-its-turn" bug (8.1 ≡ 9.1) | ✅ Fixed | **Phase 2** — event-driven dispatcher with resource pools |
| R1.2 | No explicit objective function — "heuristic dispatch without a scoring target" | ✅ Fixed | **Phase 2** — `scoreOf(inst)` = w1·tp + w2·batchPriority + w3·idx |
| R1.3 | "Minutes from anchor" breaks around DST | ⏭ Partial | `test.html` S4 smoke-tests it; deeper epoch-UTC refactor parked |
| R1.4 | Auto-spill of size reductions needs audit trail (§4) | ✅ Fixed | **Phase 7** — `state.logs.spills` + MES Log "Auto-adjustments" table |
| R1.5 | Robot-vs-operator decision deserves a chapter, not a table row | ✅ Documented | DECISIONS.md — Phase 4 section + Phase 2 has operator resource model |
| R1.6 | XSS coverage — `setHTML` for SVG, localStorage import/export, `no-inner-html` lint | ⏭ Partial | Phase 3 schema-versioning validates inputs; ESLint rule not added (single-file constraint) |
| R1.7 | 7 snapshot tests including DST, size=0, tiebreak | ✅ Added | **Phase 1** — `test.html` with 9 scenarios (S1–S9) |
| R1.8 | WCAG contrast + aria-labels | ✅ Fixed | **Phase 8** — 1 px navy chip borders + `aria-label` on all chips |
| R1.9 | Who's the user? Manager vs planner? | ✅ Answered | **Phase 5** — user chose both, Planner is home, no hidden features |
| R1.10 | What happens when the model is wrong? (tolerance) | ⏭ Open question | Flagged; needs Cabiran's explicit tolerance threshold |
| R1.11 | MES-to-forecast feedback loop | ⏭ Parked for v2 | **Phase 6** — banner explicitly documents the absence |
| R1.12 | Schema versioning + `migrateIfNeeded` | ✅ Added | **Phase 3** — `SCHEMA_VERSION`, `MIGRATIONS[n]`, called from `load()` |
| R1.13 | JSDoc for `state` | ✅ Added | **Phase 9** — `@typedef` block for state / config / forecast / etc. |
| R1.14 | "FREE" metric misleads (includes blocked idle) | ✅ Fixed | **Phase 8** — renamed to "idle" with tooltip explaining dry-gates |
| R1.15 | Live Conveyor visualization vs small batch size | ✅ Fixed | **Phase 8** — "X of 38 loaded" annotation on partial batches |
| R2.1 | Missing resource model (operators, sand station) | ✅ Fixed | **Phase 4** — `config.resources = {operators, sandStations}` |
| R2.2 | Opening position lacks stage-within-cohort detail | ⏭ Partial | `role` field already captures coarse position; finer-grained deferred |
| R2.3 | Optimizer too early to expand | ⏭ Held | Current heuristic optimizer kept; GA explicitly out-of-scope |
| R2.4 | `dryAfter` as hard delay is fine for now | ✅ Confirmed | No change needed; documented |

### Items that stayed out of scope
- **TypeScript / multi-file split** — original single-file constraint held.
- **Genetic-algorithm optimizer** — heuristic optimizer + objective function is sufficient.
- **MES-to-forecast feedback loop** — user decision.
- **DST deep-fix (epoch UTC)** — reviewer #1 raised but parked; S4 smoke-tests for now.
- **Modal prompt for size-reduction spill** — rejected in favour of audit trail (§4).

### Two-reviewer convergence score-card (reviewer #2's rubric)

| היבט | לפני | אחרי |
|---|---:|---:|
| איכות המסמך עצמו | 4 | 4.5 |
| הארכיטקטורה | 4 | 4.5 (schema versioning) |
| UI/UX | 4 | 4.5 (WCAG borders, renamed FREE, partial-load annotation) |
| נכונות המודל החישובי | 2.5 | **4** (event-driven dispatcher, resource pools, objective function) |
| Test coverage | 1 | 3.5 (9 pinned scenarios; need browser run to confirm) |
| מוכנות לפרודקשן | 2 | 3.5 (still not a ship-date-authority, but fit for daily planning) |

**Net**: the tool has moved from "prototype that demos" to "planning tool fit for shop-floor
daily use." The two remaining blockers are (a) Cabiran's explicit accuracy tolerance
(R1.10) and (b) the MES feedback loop, both policy decisions rather than code.

