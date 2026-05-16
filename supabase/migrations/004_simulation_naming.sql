-- Layer 6 A1: simulation naming & tagging
-- Adds an optional human-readable name and a tag list to saved simulations.
-- RLS is already enforced by the existing "users own their simulations" policy.
alter table simulations
  add column if not exists name text,
  add column if not exists tags text[] not null default '{}';
