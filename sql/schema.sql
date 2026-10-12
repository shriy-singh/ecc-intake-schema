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

create table if not exists public.handoffs (
  id              bigint generated always as identity primary key,
  conversation_id text        not null,
  transcript      text        not null,
  trigger_label   text        not null
    check (trigger_label in ('weapon', 'injury', 'fire', 'danger',
                             'person_in_distress', 'unclassified_after_two_tries')),
  created_at      timestamptz not null default now()
);

-- Supabase exposes public tables through its API; lock them down.
-- The FastAPI backend writes with the service-role key, which bypasses RLS.
alter table public.requests enable row level security;
alter table public.handoffs enable row level security;
