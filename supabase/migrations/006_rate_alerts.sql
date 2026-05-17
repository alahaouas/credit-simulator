-- C5: rate alerts — notify users when a country's mortgage rate hits their target
create table if not exists rate_alerts (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid references auth.users(id) on delete cascade not null,
  country          text not null,
  target_rate      text not null,  -- decimal fraction e.g. "0.035"
  active           boolean not null default true,
  created_at       timestamptz default now(),
  last_notified_at timestamptz
);

alter table rate_alerts enable row level security;

drop policy if exists "users own their rate alerts" on rate_alerts;
create policy "users own their rate alerts"
  on rate_alerts for all
  using  (auth.uid() = user_id)
  with check (auth.uid() = user_id);
