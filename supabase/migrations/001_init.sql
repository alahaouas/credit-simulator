-- Credit Simulator: simulations table + RLS
create table if not exists simulations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade not null,
  created_at  timestamptz default now(),
  inputs      jsonb not null,
  result      jsonb not null,
  schedule    jsonb
);

alter table simulations enable row level security;

drop policy if exists "users own their simulations" on simulations;
create policy "users own their simulations"
  on simulations for all
  using  (auth.uid() = user_id)
  with check (auth.uid() = user_id);
