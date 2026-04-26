# Environment Variables Guide

## Railway (Backend)

Set semua ini di Railway dashboard → Variables.

| Variable | Wajib | Keterangan |
|----------|-------|------------|
| `ANTHROPIC_API_KEY` | ✅ | sk-ant-... dari console.anthropic.com |
| `EXA_API_KEY` | ✅ | Dari dashboard.exa.ai |
| `VOYAGE_API_KEY` | ✅ | Dari dash.voyageai.com |
| `CLERK_ISSUER` | ✅ | Format: `https://<your-app>.clerk.accounts.dev` — lihat Clerk dashboard → API Keys |
| `CLERK_SECRET_KEY` | ✅ | `sk_live_...` dari Clerk dashboard |
| `DATABASE_URL` | ✅ | Railway auto-inject kalau Anda add Postgres plugin (format: `postgresql+asyncpg://...`) |
| `REDIS_URL` | ✅ | Railway auto-inject kalau Anda add Redis plugin |
| `APP_ENV` | | `production` |
| `LOG_LEVEL` | | `INFO` |
| `SECRET_KEY` | ✅ | Random 32 char string |
| `CLAUDE_MODEL` | | Default: `claude-opus-4-7` |

### Railway services yang perlu dibuat:
1. **backend** — dari repo ini, dockerfile `backend/Dockerfile`
2. **worker** — sama dockerfile, override start command: `arq app.jobs.worker.WorkerSettings`
3. **Postgres** — Railway plugin, pilih Postgres 16
4. **Redis** — Railway plugin

Database URL dari Railway format `postgresql://user:pass@host:port/db` — perlu diubah ke `postgresql+asyncpg://...` untuk asyncpg. Tambahkan variable transform di Railway atau set manual.

---

## Vercel (Frontend)

Set di Vercel dashboard → Settings → Environment Variables.

| Variable | Wajib | Keterangan |
|----------|-------|------------|
| `NEXT_PUBLIC_API_URL` | ✅ | URL Railway backend, e.g., `https://researchpilot-backend.up.railway.app` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | ✅ | `pk_live_...` dari Clerk dashboard |
| `CLERK_SECRET_KEY` | ✅ | `sk_live_...` dari Clerk dashboard |

---

## Clerk Setup Checklist

1. Buat aplikasi di dashboard.clerk.com
2. Copy Publishable Key ke frontend ENV
3. Copy Secret Key ke backend dan frontend ENV
4. Copy Issuer URL (format: `https://your-app.clerk.accounts.dev`) ke backend `CLERK_ISSUER`
5. Di Clerk dashboard → Redirect URLs, tambahkan:
   - Sign-in: `https://your-vercel-domain.vercel.app/sign-in`
   - Sign-up: `https://your-vercel-domain.vercel.app/sign-up`
   - After sign-in: `https://your-vercel-domain.vercel.app/dashboard`

---

## Local Development (.env)

Copy `.env.example` ke `.env` dan isi:

```bash
cp .env.example .env
```

Untuk local, `CLERK_ISSUER` bisa pakai development instance dari Clerk.
`APP_ENV=development` akan skip JWT verification kalau tidak ada token (untuk test via curl).
