-- Every RLS check (auth.uid() = user_id) and every .eq("user_id", ...) query
-- in api/routes/*.py filters on user_id with no supporting index besides the
-- primary key, forcing a sequential scan as these tables grow.
create index if not exists simulations_user_id_idx on simulations (user_id);
create index if not exists api_keys_user_id_idx on api_keys (user_id);
create index if not exists rate_alerts_user_id_idx on rate_alerts (user_id);

-- Explicit Data API grants for rate_alerts, for consistency with newer
-- Supabase projects that require them for PostgREST access. Not currently
-- exploitable without this — the FastAPI backend always uses the
-- service-role key (see api/db.py), which bypasses grants and RLS — but
-- this future-proofs the table if a direct client-side path is ever added.
-- RLS (006_rate_alerts.sql) still restricts every row to its owner.
grant select, insert, update, delete on rate_alerts to authenticated;
