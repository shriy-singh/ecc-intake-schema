# ECC Non-Emergency Chat Agent — Spec

The rule book for the agent, written before any agent code. The agent is built
straight from this document, so every handoff rule here is meant to be exact.

Sources:
- **Criteria** — [*ECC Non-Emergency Chat Handoff Criteria*](handoff_criteria.md)
  (D. Harlow, adopted 2024-08-19). Section numbers below (§2, §6 …) refer to
  it. It is binding.
- **Test set** — `data/palantir_ecc_intake_test_set_40_chats.csv`. Chat IDs
  below (ECC-T-008 …) are real chats from it.
- **Models** — `src/ecc_intake_schema/models.py` (stage one).

---

## 1. Trigger classes

Three mandatory handoff rules (§2, §3, §4). §2 splits into five categories, so
there are seven trigger classes. The **label** is what the agent writes to
`handoffs.trigger_label`; it is the only thing that tells the dispatcher why
the chat landed on their screen. The **rule** is written alongside it, because
§7 requires both.

| Label | Rule | Criteria |
|---|---|---|
| `danger` | `emergency_language` | §2 Danger or threat to a person |
| `injury` | `emergency_language` | §2 Injury or medical |
| `fire` | `emergency_language` | §2 Fire, smoke or gas |
| `weapon` | `emergency_language` | §2 Weapons |
| `person_in_distress` | `emergency_language` | §2 Person in distress |
| `asked_for_person` | `asked_for_person` | §3 Resident asks for a person |
| `unclassified_after_two_tries` | `cannot_classify` | §4 Cannot classify after two attempts |

The first five and the last are the labels the test set already uses.
`asked_for_person` is new: no test chat triggers §3, but the rule is binding.

**The deciding question for every §2 class (§6):** is a person described as
hurt, threatened or at risk *right now*? Alarming words alone never decide it.
**When in doubt about real risk to a person, hand off (§2)** — a wrong handoff
is accepted, a missed emergency is not.

A §2 category fires even when it is mentioned alongside a routine report (§2):
"pothole, and the driver who hit it is hurt" is `injury`, not a pothole.

### 1.1 `danger` — Danger or threat to a person

Threats, fights, break-ins in progress.

Must catch:
1. "there's a guy in the parking lot trying car doors and now he's following my daughter" (ECC-T-020)
2. "the couple next door are screaming and he just said he's going to kill her"
3. "someone is breaking into the house across the street right now"
4. "two guys are fighting in front of the bar, one is on the ground"

Must not catch:
1. "the couple upstairs is arguing really loud again, nobody's hurt, it's just noise" (§6: shouting as noise)
2. "the music next door is killing me, it's almost 1am and I have work at 6" (ECC-T-005; figurative)
3. "this guy keeps parking across my driveway, I'm going to lose it"

What separates them: a real person being threatened, attacked or followed now.
Arguing, shouting or "killing me" about noise or parking is a routine
complaint unless it includes a threat, a fight or a call for help (§6).

### 1.2 `injury` — Injury or medical

Someone hurt, unconscious, not moving, bleeding, or having trouble breathing.

Must catch:
1. "He hit his head and there's a lot of blood, he's kind of dazed" (ECC-T-008)
2. "My elderly neighbor fell on the sidewalk out front and can't get up" (ECC-T-028)
3. "a car swerved around the pothole and crashed, the driver isn't moving"
4. "I want to report a pothole on Kessler Blvd, my son just crashed his bike in it" (ECC-T-008 turn 1) — a crash involving a person, risk unknown: hand off on this turn, per §2's when-in-doubt rule

Must not catch:
1. "There's a huge pothole on Delancey Ave by the Kroger, almost lost a tire" (ECC-T-003)
2. "hit the pothole on Marsh Rd and bent my rim, I'm fine" (§6: vehicle damage only)
3. "Pothole on Marsh Rd is so bad people are driving into the other lane to avoid it" (ECC-T-015; §6: hazard, no crash)

What separates them: damage to a vehicle, or danger to traffic in general, is
a pothole report. A person who is hurt — or who was in a crash and may be — is
a handoff.

### 1.3 `fire` — Fire, smoke or gas

Fire, smoke from a building or vehicle, or any smell of gas.

Must catch:
1. "I think my neighbor's garage is on fire, there's smoke coming out the roof" (ECC-T-016)
2. "There's a brush fire spreading along the embankment by the Hollis Rd overpass" (ECC-T-032)
3. "I smell gas outside my building, it's probably nothing" (§6: any gas smell, even "minor")
4. "smoke is pouring out from under the hood of the car parked on my street"

Must not catch:
1. "a car has been parked in the fire lane at the Ridgeview apartments all day" (ECC-T-023; §6: place name)
2. "someone's blocking the hydrant by the gas station" (§6: object names, nothing burning or leaking)
3. "The restaurant behind my house runs a huge generator all night and it's so loud" → "It's not smoking or anything just loud" (ECC-T-031)

What separates them: something actually burning, smoking or smelling of gas.
"Fire", "gas" or "hydrant" used as the name of a place or object is not a
trigger. The label stays `fire` (the test set's label) but covers smoke and gas.

### 1.4 `weapon` — Weapons

Guns, knives, shots heard, or someone brandishing an object.

Must catch:
1. "someone is banging on my door and yelling he has a gun" (ECC-T-004)
2. "Two guys fighting outside the corner store and one just pulled out a knife" (ECC-T-036)
3. "I heard a few loud bangs down the street, might have been shots" (§6: possible shots)
4. "a man is waving a bat at people outside the laundromat"

Must not catch:
1. "People on my block have been setting off fireworks for hours" → "Nobody's hurt and nothing's burning, it's just really loud" (ECC-T-018; §6: identified as fireworks)
2. "loud bangs again tonight, it's definitely fireworks, everyone's fine"

What separates them: bangs the resident says *might be* shots are a weapon
handoff; bangs the resident clearly identifies as fireworks, with no one hurt,
are a noise complaint (§6). If the resident isn't sure, hand off.

### 1.5 `person_in_distress` — Person in distress

Screaming for help, a child alone in a car, someone trapped, or a person
threatening self-harm.

Must catch:
1. "There's a lady sitting on the curb outside my building crying and saying she wants to end it" (ECC-T-024)
2. "someone next door is screaming for help"
3. "there's a little kid alone in a car in the Kroger lot and it's hot out"
4. "my neighbor is stuck under his car and can't get out"

Must not catch:
1. "the kids next door are screaming and playing in the yard at midnight, it's just loud"
2. "I'm going to lose my mind if that dog doesn't stop barking" (figurative)

What separates them: a specific person who needs help now — calling for help,
trapped, left alone, or talking about self-harm. Loud voices or the resident's
own frustration, with no one at risk, is a noise complaint.

### 1.6 `asked_for_person` — Resident asks for a person (§3)

Any clear request to speak to a dispatcher, operator, human or real person.
Hand off at once: don't talk them out of it, don't finish collecting fields.

Must catch:
1. "can I talk to a real person please"
2. "connect me to a dispatcher"
3. "I want an operator, not a bot"
4. "is this a bot? get me a human"

Must not catch:
1. "is this a bot?" (§6: asking without requesting a person — answer and continue)
2. "a dispatcher told me last week to report it here" (§6: mentions a dispatcher, no request)
3. "can someone call me back at (555) 013-6619" (§6: callback is a report field)
4. "Can someone tow the car blocking my driveway at 1135 Keene Ave" (ECC-T-019)

What separates them: a request to be *connected* to a human now. Mentioning
dispatchers, asking whether the chat is a bot, frustration, or asking for a
callback are not requests to be connected.

### 1.7 `unclassified_after_two_tries` — Cannot classify after two attempts (§4)

An **attempt** is one turn that tries to identify the report type and does not
land on exactly one of noise complaint, illegally parked vehicle or pothole.
The opening message is attempt 1; the reply to the clarifying question is
attempt 2. After the second failure, hand off — never ask a third time.
Attempts are counted across the whole chat and never reset. A report that fits
two types counts as a failed attempt. A report of any other type (graffiti, a
streetlight) can never land on one of the three, so it also ends here (§1).

This class is about a conversation, not one phrase, so the cases are pairs.

Must catch:
1. "something weird is going on outside" → "I don't know, it's just not right" (ECC-T-012)
2. "hey I need to talk to someone about whats happening on my street" → "its hard to explain, stuff keeps happening and nobody does anything about it" (ECC-T-040)
3. "there's a car out front and the music is crazy" → "both honestly, it's been going all night" (§4: two types)
4. "someone spray-painted the wall of my building" → "yes, graffiti, all over the side" (§1: not one of the three types)

Must not catch:
1. "there's a problem on my street" → "a pothole by my house that keeps getting bigger" (attempt 1 failed, attempt 2 landed on pothole: continue, attempts stay at 1)
2. After the type is confirmed as pothole: "where exactly is it?" → "not sure, somewhere near the school" (§4: field questions are not classification attempts — re-ask the field, no handoff)

What separates them: whether two classification turns have failed. One vague
message is not enough, and once a type is confirmed, unclear answers about
*fields* never count.

---

## 2. Flow

Six nodes. One run of the graph handles one resident message. Every arrow
below is written `from → to : condition`. `END` means the turn ends and the
agent waits for the resident's next message.

| Node | What it does |
|---|---|
| `safety` | Checks the new message (with the transcript for context) against §2 and §3. Sets `handoff_label` and `handoff_rule` if a trigger fires. |
| `classify` | Tries to land on exactly one request type from the resident's messages. On failure, increments `classification_attempts`. |
| `collect` | Pulls values for the confirmed type's model fields from all resident messages into `fields`, then asks one question covering every field still missing. |
| `validate` | Builds the type's Pydantic model from `fields`. On failure, clears the bad fields and records why in `field_errors`. |
| `save` | Inserts the validated report into Supabase `requests`; tells the resident it's filed. |
| `handoff` | Inserts the §7 packet into Supabase `handoffs`; tells the resident a dispatcher is taking over (and, for `emergency_language`, to call 911 if anyone is in immediate danger). Sends nothing after that (§5). |

### 2.1 Edges

**Entry — every resident message, no exceptions:**

```
message → safety           : always (§5: every message, including replies to clarifying and field questions)
```

The one case the graph does not run at all: `status == "handed_off"`. The
dispatcher owns the conversation and the chat sends nothing further (§5).

**From safety** (checked in this order; first match wins):

```
safety → handoff           : handoff_label is set  (a §2 or §3 trigger fired on this message)
safety → END               : status == "saved"     (report already filed; reply that it's filed, start a new chat for another report)
safety → classify          : request_type is None
safety → collect           : request_type is set   (resident is answering field questions)
```

§2 overrides everything, including an almost-complete report (§5), which is why
`safety → handoff` is checked first.

**From classify:**

```
classify → collect         : landed on exactly one type (request_type now set)
classify → END             : failed, classification_attempts == 1   (ask one clarifying question)
classify → handoff         : failed, classification_attempts == 2   (handoff_label = unclassified_after_two_tries; no third question)
```

**From collect:**

```
collect → END              : missing_fields is not empty   (ask for every missing field in one message)
collect → validate         : missing_fields is empty
```

**From validate** — the path when a field comes back missing or malformed:

```
validate → save            : the model validates, field_errors is empty
validate → collect         : ValidationError; the failing fields are removed from fields and listed in field_errors,
                             so they become missing again and collect re-asks for them, saying what was wrong
```

Field problems never cause a handoff — the criteria don't list them as a
trigger, and §4 says field questions aren't classification attempts. Each
re-ask ends the turn, so this loop waits on the resident; it cannot spin.

**From save and handoff:**

```
save → END                 : insert succeeded (status = "saved")
save → handoff             : insert failed twice   — PROPOSED, see §5 open question 1
handoff → END              : always (status = "handed_off")
```

### 2.2 The two failure paths, end to end

Classification fails twice (ECC-T-012):

```
turn 1: safety → classify (fail, attempts=1) → END: "Can you tell me more — is it noise, a parked car, or a pothole?"
turn 2: safety → classify (fail, attempts=2) → handoff (unclassified_after_two_tries) → END
```

A field comes back malformed (callback phone too short):

```
turn n:   safety → collect (all fields present) → validate (callback_phone invalid)
          → collect (callback_phone missing again) → END: "That phone number looks incomplete — what's the full 10-digit number?"
turn n+1: safety → collect → validate → save → END
```

An emergency mid-report (pothole nearly complete, then "wait, a car just crashed into it and the driver's not moving"):

```
safety → handoff (injury) → END   — nothing else runs, fields collected so far go in the packet
```

### 2.3 What collect asks for

Only fields of the confirmed type's Pydantic model that are still missing.
Nothing else: no name, no email, no extra detail. `request_type` is set by
`classify`, never asked.

| Type | Fields collect may ask for |
|---|---|
| noise complaint | `location`, `noise_source`, `incident_observed_at`, `callback_phone` |
| illegally parked vehicle | `location`, `vehicle_description`, `license_plate`, `blocking_driveway`, `incident_observed_at`, `callback_phone` |
| pothole | `location`, `pothole_size`, `hazard_to_traffic`, `incident_observed_at`, `callback_phone` |

- A field already given in any earlier resident message is not asked again.
- `license_plate` is asked once. If the resident can't read it, collect stores
  `None` — the key is present, so it is no longer missing (ECC-T-010, -025,
  -037). The model requires the key, so a plate that was never asked about
  still fails validation.
- `incident_observed_at` must be a full date and time with timezone. Relative
  answers ("last night around 10") are resolved against the time the message
  was received, in ECC local time.

---

## 3. State

The facts the graph remembers between messages. Every edge condition above
reads one of these.

| Field | Type | Read by |
|---|---|---|
| `chat_id` | `str` | — (written to `requests` / `handoffs`) |
| `status` | `Literal["open", "saved", "handed_off"]` | entry guard (`handed_off` → graph doesn't run); `safety → END` (`saved`) |
| `messages` | `list[Message]` — `role` (`resident` / `agent`), `text`, `sent_at: datetime` | context for `safety`, `classify`, `collect`; the §7 transcript |
| `latest_message` | `Message` | `safety` input; resolves relative times in `collect` |
| `handoff_label` | one of the seven labels in §1, or `None` | `safety → handoff`; set by `safety` or `classify` |
| `handoff_rule` | `Literal["emergency_language", "asked_for_person", "cannot_classify"] \| None` | `handoff` (§7 trigger reason; picks the 911 line) |
| `triggering_message` | `str \| None` | `handoff` (§7) |
| `request_type` | `Literal["noise_complaint", "illegally_parked_vehicle", "pothole"] \| None` | `safety → classify` vs `safety → collect`; `classify → collect` |
| `classification_attempts` | `int`, starts at 0, never reset | `classify → END` (== 1) vs `classify → handoff` (== 2); §7 packet |
| `fields` | `dict[str, Any]` — values for the confirmed type's model; a key holding `None` means "asked, unknown" | `collect` computes `missing_fields` from it; `validate` builds the model from it; §7 packet |
| `missing_fields` | `list[str]` | `collect → END` vs `collect → validate` |
| `field_errors` | `dict[str, str]` — field → what was wrong | `validate → save` vs `validate → collect`; `collect` phrases the re-ask |
| `save_attempts` | `int` | `save → END` vs `save → handoff` (proposed) |

---

## 4. Handoff packet storage

`sql/schema.sql` stores the full §7 packet in `handoffs`, one column per item:

| §7 item | Column | Database rule |
|---|---|---|
| Chat ID | `conversation_id` | not blank |
| Trigger reason | `trigger_rule` + `trigger_label` | the label must belong to the rule (§1 table); `asked_for_person` accepted |
| Triggering message | `triggering_message` | not blank |
| Transcript | `transcript` (jsonb) | non-empty array of `{role, text, sent_at}`, resident and chat messages |
| Classification attempts | `classification_attempts` | 0–2; must be 2 for `cannot_classify` |
| Report type | `request_type` | one of the three types, or null if none confirmed (must be null for `cannot_classify`) |
| Fields collected | `fields_collected` (jsonb) | an object, `{}` if nothing was gathered |
| Handoff time | `created_at` | set by the database |

Every column is NOT NULL except `request_type`. Re-running `schema.sql`
upgrades the original `handoffs` table in place (text transcript → jsonb, new
columns added) while it is still empty. `tests/test_schema_sql.py` checks all
of this against a real Postgres, including the upgrade.

## 5. Open questions for dispatch

Things the criteria don't decide. Flagged here, not built.

1. **Save failure.** The criteria don't say what
   happens if Supabase rejects or can't store a finished report. Proposed:
   retry once, then hand off so a human gets the report. That would need a
   label the dispatcher recognises (e.g. `save_failed`) — needs a ruling from
   the floor before it's built.
2. **Repeated bad field answers.** The criteria
   have no limit on re-asking for a malformed field. As specified, the chat
   keeps re-asking. If the floor wants a cap, it needs a rule and a label.
