-- Confirms the handoffs table holds the full handoff packet (criteria §7).
-- Expected: 10 columns, transcript and fields_collected are jsonb,
-- and request_type is the only nullable column.
select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public' and table_name = 'handoffs'
order by ordinal_position;
