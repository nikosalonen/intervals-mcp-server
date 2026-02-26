# Intervals.icu Training Plan — API Prompt

Use this prompt with Claude to modify the Tiirismaa Trail Marathon training plan on Intervals.icu.

---

## Prompt

```
I have a training plan on Intervals.icu that I need you to modify via the API.

**API credentials:**
- API Key: uql0qkdonq2mb9gz8jrjqvss
- Athlete ID: i37450
- Base URL: https://intervals.icu/api/v1
- Auth: HTTP Basic with username "API_KEY" and the API key as password

**Endpoints:**
- List events: GET /api/v1/athlete/{id}/events?oldest=YYYY-MM-DD&newest=YYYY-MM-DD
- Create bulk: POST /api/v1/athlete/{id}/events/bulk (JSON array)
- Update: PUT /api/v1/athlete/{id}/events/{eventId} (JSON object)
- Delete: DELETE /api/v1/athlete/{id}/events/{eventId}
- Custom zones: GET/PUT /api/v1/athlete/{id}/custom-item/{itemId}

**Custom HR zones (zone set: TiirismaaTrail, ID: 953220):**
- CZZ1 = Recovery (60-75% LTHR)
- CZMAF = MAF Easy (75-83% LTHR, ~126-140 bpm)
- CZMOD = Moderate (83-86% LTHR, ~140-145 bpm)
- CZHRD = Hard (86-98% LTHR, ~145-166 bpm)
- CZMAX = Max (98-115% LTHR, ~166-194 bpm)

**Workout description format (this is how Intervals.icu parses workouts):**
Workouts are defined in the `description` field as markdown text. The API auto-parses this into workout_doc. Set `"target": "HR"` at the event level.

Simple workout:
  {
    "category": "WORKOUT",
    "start_date_local": "2026-03-03T00:00:00",
    "type": "Run",
    "name": "Easy Run",
    "description": "Easy run. MAF ≤140 bpm.\n\n- 45m CZMAF HR",
    "target": "HR",
    "moving_time": 2700,
    "distance": 5000
  }

Multi-section workout with repeats:
  {
    "description": "Jättäri power hiking — 4 reps.\n\nWarmup\n- 12m CZMAF HR\n\nJättäri reps 4x\n- 10m CZHRD HR press lap, power hike UP\n- 5m CZMAF HR press lap, jog DOWN recover\n\nCooldown\n- 10m CZMAF HR"
  }

Key syntax rules:
- Section headers on their own line: `Warmup`, `Main set`, `Cooldown`, etc.
- Steps: `- <duration> CZ<zone> HR` (e.g., `- 45m CZMAF HR`)
- Repeats: `Label Nx` as section header (e.g., `Strides 4x`)
- Press lap: append `press lap` to step (e.g., `- 10m CZHRD HR press lap`)
- Duration units: `m` = minutes, `s` = seconds
- Text after the HR target is treated as a note

**Event types:**
- Workouts: `"category": "WORKOUT"`, types: `Run`, `TrailRun`, `WeightTraining`
- Notes: `"category": "NOTE"`, set `"show_as_note": true, "not_on_fitness_chart": true`
- Seasons: `"category": "SEASON_START"`
- Race: `"category": "RACE_A"`

**Strength workout format (bullet points for readability):**
  "Strength Phase N — Title (XX min)\n\n- Exercise 1\n- Exercise 2\n- Exercise 3"

**Current plan (22 weeks, March 2 – August 1, 2026):**

PHASE 1 — AEROBIC BASE (W1-4, Mar 2-29)
Season: Phase 1 — Aerobic Base (2026-03-02)
All runs MAF ≤140 bpm. Build 30→36 km. 2x strength/week.

  W1 (Mar 2-8) | 30 km | BUILD
    2026-03-03 | Run | W1 Tue — Easy Run | 45m CZMAF | 5 km
    2026-03-04 | WeightTraining | W1 Wed — Strength | Phase 1 Foundation
    2026-03-05 | Run | W1 Thu — Easy Run | 45m CZMAF | 5 km
    2026-03-06 | Run | W1 Fri — Easy Run | 70m CZMAF | 8 km
    2026-03-07 | Run | W1 Sat — Long Run | 105m CZMAF | 12 km
    2026-03-08 | WeightTraining | W1 Sun — Strength | Phase 1 Foundation

  W2 (Mar 9-15) | 33 km | BUILD
    2026-03-09 | Run | W2 Mon — LTHR Test (Garmin guided) | 25m | 3 km
    2026-03-10 | Run | W2 Tue — Easy Run | 45m CZMAF | 5 km
    2026-03-11 | WeightTraining | W2 Wed — Strength | Phase 1 Foundation
    2026-03-12 | Run | W2 Thu — Easy Run | 53m CZMAF | 6 km
    2026-03-13 | Run | W2 Fri — Easy Run | 70m CZMAF | 8 km
    2026-03-14 | WeightTraining | W2 Sun — Strength | Phase 1 Foundation
    2026-03-14 | Run | W2 Sat — Long Run | 120m CZMAF | 14 km

  W3 (Mar 16-22) | 36 km | BUILD
    2026-03-17 | Run | W3 Tue — Easy Run | 53m CZMAF | 6 km
    2026-03-18 | WeightTraining | W3 Wed — Strength | Phase 1 Foundation
    2026-03-19 | Run | W3 Thu — Easy Run | 62m CZMAF | 7 km
    2026-03-20 | Run | W3 Fri — Easy Run | 70m CZMAF | 8 km
    2026-03-21 | Run | W3 Sat — Long Run | 130m CZMAF | 15 km
    2026-03-22 | WeightTraining | W3 Sun — Strength | Phase 1 Foundation

  W4 (Mar 23-29) | 30 km | DOWN WEEK
    2026-03-24 | Run | W4 Tue — Easy Run | 45m CZMAF | 5 km
    2026-03-25 | WeightTraining | W4 Wed — Strength | Phase 1 Reduced
    2026-03-26 | Run | W4 Thu — Easy Run | 45m CZMAF | 5 km
    2026-03-27 | Run | W4 Fri — Easy Run | 62m CZMAF | 7 km
    2026-03-28 | Run | W4 Sat — Long Run (easy) | 112m CZMAF | 13 km
    2026-03-29 | WeightTraining | W4 Sun — Strength | Phase 1 Reduced
    2026-03-29 | NOTE | Phase 1 Check

PHASE 2 — AEROBIC BUILD + TRAIL (W5-12, Mar 30 - May 24)
Season: Phase 2 — Aerobic Build + Trail (2026-03-30)
Introduce hills, Jättäri every 2 weeks, trail long runs. Build 35→45 km.

  W5 (Mar 30 - Apr 5) | 35 km | BUILD
    2026-03-30 | Run | W5 Mon — LTHR Test (Garmin guided) | 25m | 3 km
    2026-03-31 | Run | W5 Tue — Easy Run | 53m CZMAF | 6 km
    2026-04-01 | WeightTraining | W5 Wed — Strength | Phase 2 Unilateral
    2026-04-02 | Run | W5 Thu — Easy Run | 62m CZMAF | 7 km
    2026-04-03 | Run | W5 Fri — Easy Run | 70m CZMAF | 8 km
    2026-04-04 | Run | W5 Sat — Long Run | 120m CZMAF | 14 km
    2026-04-05 | WeightTraining | W5 Sun — Strength | Phase 2 Unilateral

  W6 (Apr 6-12) | 38 km | BUILD — first trail long run
    2026-04-07 | Run | W6 Tue — Easy Run | 62m CZMAF | 7 km
    2026-04-08 | WeightTraining | W6 Wed — Strength | Phase 2 Unilateral
    2026-04-09 | Run | W6 Thu — Medium Run | 70m CZMAF | 8 km
    2026-04-10 | Run | W6 Fri — Easy Run | 62m CZMAF | 7 km
    2026-04-11 | TrailRun | W6 Sat — Long Trail Run | 140m CZMOD | 16 km
    2026-04-12 | WeightTraining | W6 Sun — Strength | Phase 2 Unilateral

  W7 (Apr 13-19) | ~41 km | BUILD — first Jättäri
    2026-04-14 | Run | W7 Tue — Easy Run | 62m CZMAF | 7 km
    2026-04-15 | WeightTraining | W7 Wed — Strength | Phase 2 Unilateral
    2026-04-16 | Run | W7 Thu — Easy Run | 62m CZMAF | 7 km
    2026-04-17 | Run | W7 Fri — Easy Run | 70m CZMAF | 8 km
    2026-04-18 | Run | W7 Sat — Jättäri Power Hiking | 4x (10m CZHRD + 5m CZMAF) press lap | 7 km
    2026-04-19 | WeightTraining | W7 Sun — Strength | Phase 2 Unilateral

  W8 (Apr 20-26) | 32 km | DOWN WEEK
    2026-04-21 | Run | W8 Tue — Easy Run | 53m CZMAF | 6 km
    2026-04-22 | WeightTraining | W8 Wed — Strength | Phase 2 Reduced
    2026-04-23 | Run | W8 Thu — Easy Run | 53m CZMAF | 6 km
    2026-04-24 | Run | W8 Fri — Easy Run | 62m CZMAF | 7 km
    2026-04-25 | Run | W8 Sat — Long Run (easy) | 112m CZMAF | 13 km
    2026-04-26 | WeightTraining | W8 Sun — Strength | Phase 2 Reduced

  W9 (Apr 27 - May 3) | 40 km | BUILD
    2026-04-27 | Run | W9 Mon — LTHR Test (Garmin guided) | 25m | 3 km
    2026-04-28 | Run | W9 Tue — Easy Run | 62m CZMAF | 7 km
    2026-04-29 | WeightTraining | W9 Wed — Strength | Phase 2 Unilateral
    2026-04-30 | Run | W9 Thu — Easy Run + Hills | 70m CZMAF | 8 km
    2026-05-01 | Run | W9 Fri — Easy Run | 62m CZMAF | 7 km
    2026-05-02 | TrailRun | W9 Sat — Long Trail Run | 155m CZMOD | 18 km
    2026-05-03 | WeightTraining | W9 Sun — Strength | Phase 2 Unilateral

  W10 (May 4-10) | ~44 km | BUILD — Jättäri
    2026-05-05 | Run | W10 Tue — Easy Run | 62m CZMAF | 7 km
    2026-05-06 | WeightTraining | W10 Wed — Strength | Phase 2 Unilateral
    2026-05-07 | Run | W10 Thu — Medium Run | 78m CZMAF | 9 km
    2026-05-08 | Run | W10 Fri — Easy Run | 62m CZMAF | 7 km
    2026-05-09 | Run | W10 Sat — Jättäri Power Hiking | 5x (10m CZHRD + 5m CZMAF) press lap | 8 km
    2026-05-10 | WeightTraining | W10 Sun — Strength | Phase 2 Unilateral

  W11 (May 11-17) | ~42 km | BUILD — 20 km trail
    2026-05-12 | Run | W11 Tue — Easy Run | 62m CZMAF | 7 km
    2026-05-13 | WeightTraining | W11 Wed — Strength | Phase 2 Unilateral
    2026-05-14 | Run | W11 Thu — Easy Run + Hills | 70m CZMAF | 8 km
    2026-05-15 | Run | W11 Fri — Easy Run | 62m CZMAF | 7 km
    2026-05-16 | TrailRun | W11 Sat — Long Trail Run | 175m CZMOD | 20 km
    2026-05-17 | WeightTraining | W11 Sun — Strength (optional) | Phase 2 Unilateral

  W12 (May 18-24) | 32 km | DOWN WEEK
    2026-05-19 | Run | W12 Tue — Easy Run | 53m CZMAF | 6 km
    2026-05-20 | WeightTraining | W12 Wed — Strength | Phase 2 Reduced
    2026-05-21 | Run | W12 Thu — Easy Run | 53m CZMAF | 6 km
    2026-05-22 | Run | W12 Fri — Easy Run | 53m CZMAF | 6 km
    2026-05-23 | Run | W12 Sat — Long Run (easy) | 120m CZMAF | 14 km
    2026-05-24 | NOTE | Phase 2 Check

PHASE 3 — RACE-SPECIFIC (W13-20, May 25 - Jul 19)
Season: Phase 3 — Race-Specific (2026-05-25)
Weekly Jättäri/long trail alternating. Strength 1x/week maintenance. Fridays = office days.

  W13 (May 25-31) | ~43 km | BUILD — Jättäri
    2026-05-26 | Run | W13 Tue — Easy Run | 62m CZMAF | 7 km
    2026-05-27 | WeightTraining | W13 Wed — Strength | Phase 3 Trail-specific
    2026-05-28 | Run | W13 Thu — Medium Run | 78m CZMAF | 9 km
    2026-05-30 | Run | W13 Sat — Jättäri Power Hiking | 5x (10m CZHRD + 5m CZMAF) press lap | 8 km
    2026-05-31 | Run | W13 Sun — Easy Run (optional) | 53m CZMAF | 6 km

  W14 (Jun 1-7) | ~42 km | BUILD — Long Trail Run
    2026-06-02 | Run | W14 Tue — Easy Run | 60m CZMAF | 7 km
    2026-06-03 | WeightTraining | W14 Wed — Strength | Phase 3 Trail-specific
    2026-06-04 | Run | W14 Thu — Easy Run + Hills | 70m CZMAF | 8 km
    2026-06-06 | TrailRun | W14 Sat — Long Trail Run | 180m CZMOD | 22 km
    2026-06-07 | Run | W14 Sun — Easy Run (optional) | 45m CZMAF | 5 km

  W15 (Jun 8-14) | ~44 km | BUILD — Jättäri 6 reps
    2026-06-09 | Run | W15 Tue — Easy Run | 60m CZMAF | 7 km
    2026-06-10 | WeightTraining | W15 Wed — Strength | Phase 3 Trail-specific
    2026-06-11 | Run | W15 Thu — Medium Run | 78m CZMAF | 9 km
    2026-06-13 | Run | W15 Sat — Jättäri Power Hiking | 6x (10m CZHRD + 5m CZMAF) press lap | 9 km
    2026-06-14 | Run | W15 Sun — Easy Run (optional) | 53m CZMAF | 6 km

  W16 (Jun 15-21) | 32 km | DOWN WEEK (Midsummer)
    2026-06-16 | Run | W16 Tue — Easy Run | 53m CZMAF | 6 km
    2026-06-17 | WeightTraining | W16 Wed — Strength | Phase 3 Reduced
    2026-06-18 | Run | W16 Thu — Easy Run | 53m CZMAF | 6 km
    2026-06-20 | Run | W16 Sat — Long Run (easy) | 120m CZMAF | 14 km
    2026-06-21 | Run | W16 Sun — LTHR Test (Garmin guided) | 25m | 3 km

  W17 (Jun 22-28) | ~50 km | BUILD — Extended Jättäri
    2026-06-22 | Run | W17 Mon — Easy Run | 53m CZMAF | 6 km
    2026-06-23 | Run | W17 Tue — Easy Run | 60m CZMAF | 7 km
    2026-06-24 | WeightTraining | W17 Wed — Strength | Phase 3 Trail-specific
    2026-06-25 | Run | W17 Thu — Easy Run + Hills | 70m CZMAF | 8 km
    2026-06-27 | Run | W17 Sat — Jättäri Extended | 6x (10m CZHRD + 5m CZMAF) press lap | 9 km

  W18 (Jun 29 - Jul 5) | ~48 km | BUILD — Peak Long Trail Run
    2026-06-29 | NOTE | July — Vacation Flexibility
    2026-06-29 | Run | W18 Mon — Easy Run | 53m CZMAF | 6 km
    2026-06-30 | Run | W18 Tue — Easy Run | 60m CZMAF | 7 km
    2026-07-01 | WeightTraining | W18 Wed — Strength | Phase 3 Trail-specific
    2026-07-02 | Run | W18 Thu — Easy Run | 60m CZMAF | 7 km
    2026-07-04 | TrailRun | W18 Sat — KEY: Peak Long Trail Run | 225m CZMOD | 27 km

  W19 (Jul 6-12) | ~50 km | BUILD — Peak Jättäri
    2026-07-06 | Run | W19 Mon — Easy Run | 50m CZMAF | 6 km
    2026-07-07 | Run | W19 Tue — Easy Run | 60m CZMAF | 7 km
    2026-07-08 | WeightTraining | W19 Wed — Strength | Phase 3 Trail-specific
    2026-07-09 | Run | W19 Thu — Medium Run | 75m CZMAF | 9 km
    2026-07-11 | Run | W19 Sat — Jättäri Power Hiking (Peak) | 6x (10m CZHRD + 5m CZMAF) press lap | 9 km
    2026-07-12 | Run | W19 Sun — Easy Run (optional) | 43m CZMAF | 5 km

  W20 (Jul 13-19) | ~45 km | FINAL BUILD — Last Long Trail Run
    2026-07-13 | Run | W20 Mon — Easy Run | 50m CZMAF | 6 km
    2026-07-14 | Run | W20 Tue — Easy Run | 60m CZMAF | 7 km
    2026-07-15 | WeightTraining | W20 Wed — Strength | Phase 3 Trail-specific
    2026-07-16 | Run | W20 Thu — Easy Run | 60m CZMAF | 7 km
    2026-07-18 | TrailRun | W20 Sat — Last Long Trail Run | 200m CZMOD | 24 km

PHASE 4 — TAPER (W21-22, Jul 20 - Aug 1)
Season: Phase 4 — Taper (2026-07-20)
Volume -40-50%. No strength, no Jättäri. Rest and race prep.

  W21 (Jul 20-26) | ~24 km | TAPER 1
    2026-07-21 | Run | W21 Tue — Easy Run | 50m CZMAF | 6 km
    2026-07-23 | Run | W21 Thu — Easy Run + Strides | 42m CZMAF + 4x(20s CZHRD, 40s CZMAF) + 3m CZMAF | 6 km
    2026-07-25 | Run | W21 Sat — Easy Long Run | 100m CZMAF | 12 km

  W22 (Jul 27-31) | RACE WEEK
    2026-07-27 | Run | W22 Mon — Easy Run | 43m CZMAF | 5 km
    2026-07-29 | Run | W22 Wed — Shakeout + Strides | 25m CZMAF + 4x(15s CZHRD, 45s CZMAF) + 3m CZMAF | 4 km
    2026-07-30 | NOTE | Race Prep
    2026-08-01 | RACE_A | RACE — Tiirismaa Trail Marathon 42 km

**Strength progressions:**
- Phase 1 Foundation: Goblet squat 3x10 (16kg 3s eccentric), Bulgarian split squat 3x8/leg (BW), RDL 3x10 (16kg), Step-ups 3x8/leg, Calf raises 3x15 (3s eccentric), Dead bugs 3x10/side, Plank 2x30-45s
- Phase 2 Unilateral: Goblet squat 3x10 (16kg 3s pause), Bulgarian split squat 3x8/leg (12kg), Single-leg RDL 3x8/leg (12kg), Weighted step-ups 3x8/leg (16kg), Single-leg calf raises 3x12 (3s eccentric), KB swings 3x15 (16kg), Dead bugs 3x10/side, Plank 2x30-45s
- Phase 3 Trail-specific: Double KB front squat 3x8 (12+16kg), Bulgarian split squat 3x8/leg (16kg slow eccentric), Single-leg RDL 3x8/leg (16kg), Deficit step-ups 2x8/leg (16kg), Single-leg eccentric calf raises 3x12 off step, KB swings 3x20 (16kg), Plank 2x30s
- Down weeks: Reduced volume (2 sets, fewer reps)
- Equipment: 12kg + 16kg kettlebells + bodyweight only

**LTHR tests (Garmin guided, on rest days):**
- 2026-03-09 W2 Mon — baseline
- 2026-03-30 W5 Mon — post down week
- 2026-04-27 W9 Mon — post down week
- 2026-06-21 W16 Sun — post down week

Now, here's what I'd like to change: [DESCRIBE YOUR CHANGES HERE]
```

---

## Example requests

- "Move W7 Jättäri from Saturday to Sunday"
- "Add an extra easy run on Wednesday W15"
- "Change all trail long runs from CZMOD to CZMAF"
- "Swap W10 and W11 workouts"
- "Add a rest note on June 19 for Midsummer"
- "Delete the optional Sunday runs in Phase 3"
- "Update my LTHR — recalculate zone boundaries"
- "Make the Phase 2 strength sessions harder"
- "Add press lap to all Jättäri recovery steps"
