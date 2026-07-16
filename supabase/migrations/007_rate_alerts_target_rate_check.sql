-- Guard against malformed target_rate values.
--
-- target_rate stays text (matches the app-wide convention of storing
-- decimal/monetary values as strings to avoid float precision loss), but an
-- unvalidated value like "" or "abc" makes the rate-alerts edge function's
-- `parseFloat(alert.target_rate)` produce NaN. NaN compares false against
-- every numeric comparison, so the "skip if above target" guard silently
-- stops skipping and the alert fires on every cron run instead.
alter table rate_alerts
  add constraint rate_alerts_target_rate_valid
  check (
    target_rate ~ '^[0-9]+(\.[0-9]+)?$'
    and target_rate::numeric > 0
    and target_rate::numeric < 1
  );
