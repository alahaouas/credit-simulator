-- Layer 6 A5: shareable read-only links
-- Adds an optional share token to saved simulations. A non-null token means
-- the simulation is publicly accessible at /share/<token> without auth.
-- The token is generated server-side (secrets.token_urlsafe(32)) and is
-- long enough that brute-force guessing is infeasible.
alter table simulations
  add column if not exists share_token text;

create unique index if not exists simulations_share_token_idx
  on simulations (share_token)
  where share_token is not null;
