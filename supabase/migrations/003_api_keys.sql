-- Layer 6 E3: API key management
-- Full key is never stored; only a SHA-256 hash is kept.
-- key_prefix holds the first 12 chars (e.g. "csim_ab12cd") for display.
create table if not exists api_keys (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references auth.users(id) on delete cascade not null,
  name         text not null,
  key_hash     text not null unique,
  key_prefix   text not null,
  created_at   timestamptz default now(),
  last_used_at timestamptz
);

alter table api_keys enable row level security;

-- Users can manage their own keys via the service-role backend.
-- The service role bypasses RLS, so this policy only matters for
-- anon/authenticated calls (none are made directly from the browser).
drop policy if exists "users own their api keys" on api_keys;
create policy "users own their api keys"
  on api_keys for all
  using  (auth.uid() = user_id)
  with check (auth.uid() = user_id);
