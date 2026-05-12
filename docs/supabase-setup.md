# Supabase Manual Setup

These are the one-time dashboard steps required before running the web interface locally or deploying to production.

---

## 1. Create a Supabase project

1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard) and sign in.
2. Click **New project**.
3. Fill in:
   - **Name**: `credit-simulator` (or any name)
   - **Database password**: generate a strong one and save it
   - **Region**: pick the one closest to your users
4. Click **Create new project** and wait ~2 minutes for provisioning.

---

## 2. Run the migration

1. In the Supabase dashboard, go to **SQL Editor**.
2. Open a new query tab.
3. Paste the contents of [`supabase/migrations/001_init.sql`](../supabase/migrations/001_init.sql) and click **Run**.

This creates the `simulations` table with RLS enabled and the ownership policy.

---

## 3. Enable Auth providers

1. Go to **Authentication → Providers**.
2. Enable **Email** (magic link):
   - Toggle **Enable Email provider** on.
   - Set **Confirm email** to your preference (recommended: on for production, off for local dev).
3. (Optional) Enable **GitHub** or **Google** OAuth:
   - Follow the provider-specific instructions shown in the dashboard.
   - Add the Supabase callback URL to your OAuth app's allowed redirect URIs.

---

## 4. Configure redirect URLs

1. Go to **Authentication → URL Configuration**.
2. Set **Site URL**:
   - Local dev: `http://localhost:3000`
   - Production: your Vercel domain (e.g. `https://credit-simulator.vercel.app`)
3. Add to **Redirect URLs**:
   - `http://localhost:3000/auth/callback`
   - `https://<your-vercel-domain>/auth/callback`

---

## 5. Collect environment variables

Go to **Project Settings → API** and copy:

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | Project URL (e.g. `https://xxxx.supabase.co`) |
| `SUPABASE_ANON_KEY` | `anon` / `public` key |
| `SUPABASE_SERVICE_ROLE_KEY` | `service_role` key — **never expose client-side** |

### FastAPI (`api/`) — `.env`

```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

### Next.js (`web/`) — `.env.local`

```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

> Never commit either `.env` file. Both are listed in `.gitignore`.

---

## 6. Verify RLS is active

After running the migration, go to **Table Editor → simulations → RLS policies** and confirm:

- RLS is **enabled**
- The policy `users own their simulations` is listed for `SELECT`, `INSERT`, `UPDATE`, `DELETE`

---

## 7. Running migrations via Supabase CLI

Migrations live in `supabase/migrations/` and are applied directly against the production project — no local Docker stack needed.

### One-time setup

```bash
# Install (already available via scoop)
supabase --version

# Log in
supabase login

# Link to your project (find the ref in Project Settings → General)
supabase link --project-ref <your-project-ref>
```

### Applying a migration

```bash
supabase db push
```

This applies any SQL files in `migrations/` that haven't been run yet, in filename order.

### Adding a new migration

Create a new numbered file in `supabase/migrations/`:

```
supabase/migrations/002_add_column.sql
```

Then run `supabase db push` to apply it.

> Since this project has a single developer and no staging environment, migrations run directly against production. Review each SQL file carefully before pushing.

---

## Done

The backend (`api/db.py`) and auth layer (`api/auth.py`) will connect automatically once the environment variables are set.
Next step: Layer 3 — scaffold the Next.js app (`web/`).
