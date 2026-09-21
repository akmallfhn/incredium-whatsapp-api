# Incredium WhatsApp API

Single backend untuk **Incredium**: menerima webhook WhatsApp Cloud API langsung dari Meta dan
mencatatnya ke **Postgres multitenant** di Supabase.

Dibangun dengan **FastAPI + SQLAlchemy (async) + asyncpg**.

DDL referensinya ada di `docs/db/incredium.sql`; SQLAlchemy tidak pernah menggenerate schema.
Tabel yang dipakai: `tenants`, `wa_conversations`, `wa_chats`.

## Alur

```
Meta WhatsApp Cloud API
     │  POST /api/v1/webhook/whatsapp/callback/<app_id>   (signature X-Hub-Signature-256)
     ▼
[routes]   balas 200 secepatnya, proses di background task
     ▼
[service]  tenant di-resolve dari metadata.phone_number_id  ─▶  multitenant
     ├── messages            ─▶ wa_conversations (upsert) + wa_chats (inbound/user)
     │     └── media         ─▶ download dari Graph API ─▶ upload Supabase Storage ─▶ storage_url
     ├── smb_message_echoes  ─▶ wa_chats (outbound/admin)   pesan staff dari WA Business App
     └── statuses            ─▶ update sent/delivered/read/failed + timestamp-nya
```

Meta menjanjikan *at-least-once delivery* dan mengulang kirim kalau webhook tidak balas 200
dengan cepat, jadi seluruh persistensi jalan di background task. Tiap pesan di-commit
sendiri-sendiri: satu pesan gagal tidak menjatuhkan pesan lain di batch yang sama.

## Struktur Proyek

Pola `modules/<module>/{entity,repository,service,routes}` — tiap module punya layer sendiri,
dan `app/server.py` adalah **satu-satunya** tempat wiring (semua repo/service dirakit di sana).

```
app/
  main.py                       # objek FastAPI (dari server.create_app)
  server.py                     # DI/wiring + lifespan; module baru didaftarkan di sini
  scripts.py                    # entrypoint dev/start (pakai PORT / APP_PORT)
  core/config.py                # Settings (.env)
  db/
    base.py                     # DeclarativeBase entity Postgres
    session.py                  # engine async + session (normalisasi URL libpq -> asyncpg)
  shared/
    security.py                 # verifikasi signature Meta
    http.py                     # httpx client seumur hidup app
    storage.py                  # upload attachment ke Supabase Storage
  modules/
    health/routes.py            # /health, /health/db
    tenant/                     # entity + repository `tenants`
    whatsapp/                   # entity, repository, service, routes, meta_client
    stat/                       # endpoint agregat read-only untuk dashboard
```

Menambah module baru: bikin folder di `app/modules/`, lalu daftarkan di `create_app()`.

## Endpoint

| Method | Path | Dipanggil oleh | Auth |
|---|---|---|---|
| `GET` | `/health` | siapa saja | - |
| `GET` | `/health/db` | monitoring | - |
| `POST` | `/api/v1/auth/login` | dashboard TRC | `Bearer CLIENT_SECRET` |
| `GET` | `/api/v1/auth/check-session` | dashboard TRC | `Bearer <JWT>` |
| `POST` | `/api/v1/auth/logout` | dashboard TRC | `Bearer <JWT>` |
| `GET` | `/api/v1/webhook/whatsapp/callback/{app_id}` | Meta (verifikasi webhook) | `hub.verify_token` |
| `POST` | `/api/v1/webhook/whatsapp/callback/{app_id}` | Meta (event pesan/status) | `X-Hub-Signature-256` |
| `POST` | `/api/v1/stats/*` | dashboard TRC | `Bearer CLIENT_SECRET` |

## Setup

```bash
# 1. Install deps (pakai uv)
uv sync

# 2. Konfigurasi environment
cp .env.example .env
# wajib: DATABASE_URL (kredensial Meta ada di tabel meta_apps, bukan env)
# untuk attachment: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
# untuk stats + login: CLIENT_SECRET
# untuk login dashboard: JWT_SECRET
# untuk agent evaluasi lead: OPENAI_API_KEY atau DEEPSEEK_API_KEY (sesuai LLM_PROVIDER di constants.py)

# 3. Jalankan server
uv run dev          # http://localhost:$APP_PORT  (reload)
# atau: uv run start
```

> Tanpa `uv`: `pip install -e .` lalu `uvicorn app.main:app --reload`.

Port mengikuti pola yang sama dengan `ordina`: `PORT` (di-inject Railway/PaaS saat runtime)
dengan fallback `APP_PORT` untuk lokal.

`DATABASE_URL` memakai connection string Postgres biasa — param libpq
(`?schema=public`, `?pgbouncer=true`, `?sslmode=require`) dinormalisasi otomatis ke asyncpg.
Kalau pakai connection pooler Supabase (port 6543), prepared statement cache dimatikan sendiri.

Cek koneksi database: `curl http://localhost:8000/health/db`.

## Menghubungkan Webhook Meta

Di Meta App Dashboard → WhatsApp → Configuration, set:

- **Callback URL**: `https://<host>/api/v1/webhook/whatsapp/callback/<app_id>`
- **Verify token**: `meta_apps.webhook_verify_token` milik App tersebut
- **Webhook fields**: `messages` (dan `smb_message_echoes` kalau pakai coexistence)

Segmen `<app_id>` wajib — nilainya kolom `meta_apps.app_id` (App ID numerik dari Meta,
bukan primary key nanoid). Tanpa segmen itu kredensial App pemanggil tidak bisa
ditentukan, jadi signature tidak bisa dicek sebelum body dipercaya. `app_id` yang tidak
cocok satu pun baris `meta_apps` aktif ditolak 403.

Tenant di-routing lewat `meta_connections.wa_phone_number_id`: satu baris `meta_connections`
= satu WABA = satu nomor. Download media memakai `meta_connections.access_token` milik
koneksi yang bersangkutan. Koneksi atau tenant dengan `status = 'inactive'` diabaikan.

`META_APP_SECRET` dan `META_WEBHOOK_VERIFY_TOKEN` sudah tidak dipakai — kredensialnya
seluruhnya dari `meta_apps` dan dua env var itu bisa dihapus. Kalau `meta_apps.app_secret`
kosong, verifikasi signature **dilewati** (hanya untuk dev lokal).

## Auth

`POST /auth/login` menerima email + password dan dijaga `CLIENT_SECRET`; balasannya JWT
HS256 berumur `JWT_TTL_DAYS` hari (365, konstanta di `app/core/constants.py`). `GET /auth/check-session` memvalidasi JWT dan
mengembalikan profil pemiliknya. `POST /auth/logout` dijaga JWT itu sendiri dan menghapus
barisnya di `tokens`, jadi token yang sama langsung ditolak.

JWT tidak dipercaya dari tanda tangannya saja: tiap pemakaian dicocokkan ke baris
`tokens` yang masih hidup, karena tanpa itu logout tidak akan berarti apa-apa selama
setahun ke depan. Kolom `tokens.token` menyimpan JWT-nya apa adanya, jadi siapa pun yang
bisa membaca tabel itu bisa memakai sesinya. Password di-hash bcrypt. Email tak terdaftar
dan password salah menghasilkan balasan yang sama supaya daftar email tidak bisa ditebak.

Peran ada di kolom `users.role` (`Super Admin`, `Administrator`, `Member`). Tenant yang
boleh diakses seorang user ada di `users_access`, many-to-many terhadap `tenants`.
Mengganti `JWT_SECRET` mematikan semua sesi yang sedang berjalan.

Detail endpoint-nya di [docs/api/auth.md](docs/api/auth.md).

## Catatan Desain

- **Tenant di-resolve dari `metadata.phone_number_id`** lewat `meta_connections`, bukan dari
  config — satu deployment melayani semua klinik dan semua App Meta.
- **Kredensial melekat ke levelnya masing-masing**: `app_secret` dan `webhook_verify_token`
  milik App (`meta_apps`), `access_token` milik WABA (`meta_connections`). Rotasi app secret
  jadi satu baris, bukan satu baris per tenant.
- **Conversation di-upsert**, bersandar pada unique constraint `(tenant_id, phone_number)`.
  Meta bisa mengirim beberapa event untuk kontak baru yang sama secara bersamaan, jadi
  cek-lalu-insert tidak aman. Nama profil di-refresh, kecuali event-nya memang tidak membawa
  nama (echo & status) — supaya nama yang sudah ada tidak tertimpa string kosong.
- **Attachment gagal disimpan tidak membatalkan pesannya**: `storage_url` sekadar tidak ikut
  disisipkan, teks/metadata pesannya tetap masuk.
- **`created_at` diambil dari timestamp Meta**, bukan waktu server, supaya urutan chat di UI
  mengikuti waktu kirim sebenarnya.
- Bucket dan layout path Storage (`<slug>/<type>s/<ts>_<media_id>.<ext>`) sengaja sama dengan
  yang dibaca UI dashboard.

## Known Gaps

- **RLS mati di semua tabel lama** Postgres-nya. Siapa pun dengan anon key bisa baca/tulis
  `tenants`, `wa_conversations`, `wa_chats`, dan sisanya. `meta_apps` dan `meta_connections`
  sudah RLS-on tanpa policy (tolak semua lewat anon key; role `postgres` milik API tetap
  lolos). Tabel lainnya perlu pass tersendiri.
- **`app_secret` dan `access_token` disimpan plaintext** di `meta_apps`/`meta_connections`.
- **Belum ada endpoint bikin/ubah user.** Baris `users`, `password_hash`, dan
  `users_access` untuk sekarang diisi manual lewat SQL.
- Belum ada test suite otomatis. Verifikasi perubahan dengan `uv run ruff check app` plus
  request manual ke server yang jalan.
