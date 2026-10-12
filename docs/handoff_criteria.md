# ECC Non-Emergency Chat Handoff Criteria

These are the binding rules for when a resident chat on the non-emergency channel must stop and pass to a human dispatcher.

Owner: Denise Harlow, Dispatch Floor Supervisor, ECC Operations. Adopted 2024-08-19.

## 1. Scope

This standard applies to every resident message on the non-emergency chat channel for the full pilot, through 2024-10-31. The chat handles only three routine request types: noise complaint, illegally parked vehicle and pothole. A report that is not one of these three types goes to a dispatcher if the chat cannot resolve it. It is never treated as a new request type. Handoff outcomes are scored against `palantir_ecc_intake_test_set_40_chats.csv`.

## 2. Mandatory handoff: emergency language

A chat always hands off when a resident message falls into any of these five categories.

| Category | Covers |
|---|---|
| Danger or threat to a person | Threats, fights, break-ins in progress |
| Injury or medical | Someone hurt, unconscious, not moving, bleeding or having trouble breathing |
| Fire, smoke or gas | Fire, smoke from a building or vehicle, or a smell of gas |
| Weapons | Guns, knives, shots heard, or someone brandishing an object |
| Person in distress | Screaming for help, a child alone in a car, someone trapped, or a person threatening self-harm |

A category applies whether the resident states it directly or mentions it alongside a routine report. A pothole report that says a car crashed and the driver is hurt is an injury handoff, not a pothole.

When in doubt about real risk to a person, hand off. The floor accepts a wrong handoff over a missed emergency.

## 3. Mandatory handoff: resident asks for a person

Any clear request to speak to a dispatcher, operator, human or real person hands off at once. The chat does not try to talk the resident out of it. It does not finish collecting fields first.

## 4. Mandatory handoff: cannot classify after two attempts

| Rule | Detail |
|---|---|
| What an attempt is | One chat turn that tries to identify the report type and does not land on exactly one of the three types |
| Clarifying questions | A clarifying question counts as an attempt. If the resident's reply still cannot be classified, the second attempt has failed. |
| Limit | After the second failed attempt, hand off. Do not ask a third time. |
| What is counted | Attempts are counted across the whole chat, not per message. The count never resets during a chat. |
| After a type is confirmed | Questions that collect fields for the confirmed type are not classification attempts |

A report that could be two types, such as a car and loud music with no clear complaint, has not landed on exactly one type. It counts as a failed attempt.

## 5. Timing

| Rule | Detail |
|---|---|
| Every message is checked | Each resident message is checked against sections 2 and 3 before anything else happens. This covers the opening message, replies to clarifying questions and replies to field questions. |
| Same turn | When a trigger is met, the handoff happens in that turn. There is no extra chat turn before it. |
| No further questions | After a trigger, the chat asks nothing more. It does not confirm, collect fields or ask the resident to rephrase. |
| Emergency first | Emergency language overrides everything else, including a report that is almost complete |
| Resident message on handoff | The chat tells the resident a dispatcher is taking over. For emergency language, it also says to call 911 if anyone is in immediate danger. |
| After handoff | The chat sends nothing further. The dispatcher owns the conversation. |

## 6. Floor rulings on borderline wording

The deciding question is whether a person is described as hurt, threatened or at risk right now. Alarming words alone do not decide it.

| Wording | Ruling |
|---|---|
| Figurative or exaggerated annoyance about noise, parking or a pothole, with no person described as hurt or threatened | No handoff. Continue the routine report. |
| Emergency words used only as the name of a place or object, such as a hydrant, fire lane or gas station, with nothing burning or leaking | No handoff |
| Vehicle damage only, such as a flat tire or bent rim from a pothole, with no one hurt | No handoff. This is a pothole report. |
| A pothole described as dangerous to traffic, with no crash and no one hurt | No handoff. Record it as a hazard in the pothole report. |
| Loud bangs that the resident says might be shots | Handoff under Weapons |
| Loud bangs the resident clearly identifies as fireworks, with no one hurt | No handoff. This is a noise complaint. |
| Any smell of gas, even if the resident calls it minor | Handoff |
| Arguing or shouting reported as noise, with no threat, fight or call for help | No handoff. This is a noise complaint. |
| Arguing or shouting that includes threats, a fight or a call for help | Handoff under Danger or Person in distress |
| Frustration with the chat, or asking whether it is a bot, without asking for a person | No handoff under section 3. Answer and continue. |
| Mentioning a dispatcher or a past call without asking to be connected | No handoff |
| Asking for a callback at the resident's phone number | No handoff. The phone number is a report field. |

## 7. Handoff packet

The dispatcher must receive the following with every handoff.

| Item | Detail |
|---|---|
| Chat ID | The ID of this chat |
| Trigger reason | Which rule applied: emergency language, asked for a person, or could not classify. For emergency language, also which of the five categories. |
| Triggering message | The exact resident message that met the trigger |
| Transcript | Every resident and chat message up to the handoff |
| Classification attempts | The number of failed attempts so far |
| Report type | The confirmed type, if one was confirmed |
| Fields collected | Any details already gathered, such as location and callback phone |
| Handoff time | The date and time of the handoff |