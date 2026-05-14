-- Layer 6 E1: user preferences (one row per user, upsert on save)
create table if not exists user_preferences (
  user_id                         uuid primary key references auth.users(id) on delete cascade,
  default_country                 text not null default 'BE',
  default_optimization_preference text not null default 'balanced',
  currency_display                text not null default 'symbol',
  updated_at                      timestamptz default now()
);

alter table user_preferences enable row level security;

drop policy if exists "users own their preferences" on user_preferences;
create policy "users own their preferences"
  on user_preferences for all
  using  (auth.uid() = user_id)
  with check (auth.uid() = user_id);
