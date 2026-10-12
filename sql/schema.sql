-- ECC intake schema
-- Mirrors src/ecc_intake_schema/models.py. Every field is required except
-- the ones that don't apply to a request's type.

create table if not exists public.requests (
  id                   bigint generated always as identity primary key,
  conversation_id      text        not null,
  request_type         text        not null
    check (request_type in ('noise_complaint', 'illegally_parked_vehicle', 'pothole')),

  -- shared by all three types
  location             text        not null check (btrim(location) <> ''),
  incident_observed_at timestamptz not null,
  callback_phone       text        not null check (callback_phone ~ '^\(\d{3}\) \d{3}-\d{4}$'),

  -- noise_complaint
  noise_source         text,
  -- illegally_parked_vehicle
  vehicle_description  text,
  license_plate        text,  -- nullable: ECC-T-010, ECC-T-025, ECC-T-037 have no readable plate
  blocking_driveway    boolean,
  -- pothole
  pothole_size         text,
  hazard_to_traffic    boolean,

  created_at           timestamptz not null default now()
);

-- Each type must fill its own fields and leave the other types' fields empty.
-- A CHECK passes when it evaluates to NULL, and btrim(NULL) <> '' is NULL, so
-- every text test is wrapped in coalesce(..., '') to make a missing value fail.
-- Dropped and re-added so re-running this file also fixes an existing table.
alter table public.requests drop constraint if exists requests_fields_match_type;
alter table public.requests add constraint requests_fields_match_type check (
    (request_type = 'noise_complaint'
      and coalesce(btrim(noise_source), '') <> ''
      and vehicle_description is null and license_plate is null and blocking_driveway is null
      and pothole_size is null and hazard_to_traffic is null)
    or
    (request_type = 'illegally_parked_vehicle'
      and coalesce(btrim(vehicle_description), '') <> ''
      and blocking_driveway is not null
      and (license_plate is null or btrim(license_plate) <> '')
      and noise_source is null
      and pothole_size is null and hazard_to_traffic is null)
    or
    (request_type = 'pothole'
      and coalesce(btrim(pothole_size), '') <> ''
      and hazard_to_traffic is not null
      and noise_source is null
      and vehicle_description is null and license_plate is null and blocking_driveway is null)
);

-- One row per handoff: the packet the dispatcher receives (criteria §7,
-- docs/handoff_criteria.md). created_at is the handoff time.
create table if not exists public.handoffs (
  id                      bigint generated always as identity primary key,
  conversation_id         text        not null,
  transcript              jsonb       not null,
  trigger_label           text        not null,
  created_at              timestamptz not null default now()
);

-- Upgrade a handoffs table created by an earlier version of this file, which
-- stored the transcript as plain text and had only the columns above.
-- The new NOT NULL columns can only be added while the table is empty.
do $$
begin
  if (select data_type from information_schema.columns
      where table_schema = 'public' and table_name = 'handoffs' and column_name = 'transcript') = 'text' then
    alter table public.handoffs alter column transcript type jsonb using to_jsonb(transcript);
  end if;
end $$;

alter table public.handoffs
  -- which §7 rule applied; trigger_label says which category within it
  add column if not exists trigger_rule            text    not null,
  -- the exact resident message that met the trigger
  add column if not exists triggering_message      text    not null,
  -- failed classification attempts so far (§4: never more than 2)
  add column if not exists classification_attempts integer not null,
  -- the confirmed report type; null when none was confirmed
  add column if not exists request_type            text,
  -- details gathered before the handoff, e.g. {"location": ..., "callback_phone": ...}
  add column if not exists fields_collected        jsonb   not null;

alter table public.handoffs drop constraint if exists handoffs_trigger_label_check;
alter table public.handoffs drop constraint if exists handoffs_packet_check;
alter table public.handoffs add constraint handoffs_packet_check check (
  btrim(conversation_id) <> ''
  and btrim(triggering_message) <> ''
  -- every resident and chat message up to the handoff: [{"role", "text", "sent_at"}, ...]
  and jsonb_typeof(transcript) = 'array' and jsonb_array_length(transcript) > 0
  and jsonb_typeof(fields_collected) = 'object'
  and classification_attempts between 0 and 2
  and (request_type is null
       or request_type in ('noise_complaint', 'illegally_parked_vehicle', 'pothole'))
  -- the label must belong to the rule (docs/agent_spec.md §1)
  and (
    (trigger_rule = 'emergency_language'
      and trigger_label in ('danger', 'injury', 'fire', 'weapon', 'person_in_distress'))
    or
    (trigger_rule = 'asked_for_person' and trigger_label = 'asked_for_person')
    or
    -- §4: hand off only after the second failed attempt, and no type was confirmed
    (trigger_rule = 'cannot_classify' and trigger_label = 'unclassified_after_two_tries'
      and classification_attempts = 2 and request_type is null)
  )
);

-- Supabase exposes public tables through its API; lock them down.
-- The FastAPI backend writes with the service-role key, which bypasses RLS.
alter table public.requests enable row level security;
alter table public.handoffs enable row level security;
