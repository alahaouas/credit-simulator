-- Share tokens (005) had no expiry — a leaked link stayed valid forever
-- unless the owner explicitly revoked it. Add an expiry column; existing
-- tokens are grandfathered as non-expiring (column defaults to null for
-- pre-existing rows), new tokens get a 30-day TTL set by the API at
-- generation time (see api/routes/share.py).
alter table simulations
  add column if not exists share_token_expires_at timestamptz;
