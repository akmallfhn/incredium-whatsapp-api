# WhatsApp

Endpoint ini membaca percakapan dan chat WhatsApp per filter wajib, serta menerima verifikasi dan event webhook dari Meta. Endpoint daftar memakai JWT hasil `auth/login` dan membatasi data menurut akses tenant pengguna yang tersimpan di `users_access`; callback Meta memakai verify token atau signature milik `meta_apps` sesuai `app_id` pada URL.

## `POST /api/v1/whatsapp/conversations`

Mengembalikan percakapan milik satu tenant, diurutkan dari `created_at` terbaru dengan `id` sebagai pemecah waktu yang sama.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `page` | integer, minimum 1 | no |
| `page_size` | integer, minimum 1 | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "conversations retrieved successfully",
  "data": {
    "list": [
      {
        "id": "CSzBhHYZH2h61r5eXoe6n",
        "tenant_id": "8yuPA4qUjqC3OfizucQoH",
        "full_name": "Vicky",
        "phone_number": "6282213950021",
        "last_read_id": null,
        "created_at": "2026-09-02T10:00:08+00:00",
        "updated_at": "2026-09-02T10:00:08+00:00"
      }
    ],
    "metapaging": {
      "total_data": 1,
      "total_page": 1,
      "current_page": 1,
      "page_size": 20
    }
  }
}
```

`page` default `1`, `page_size` default `20` dan dibatasi maksimum `100`. Daftar kosong tetap mengembalikan `list: []` dan `total_page: 0`.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: tenant_id` | `tenant_id` tidak dikirim atau bukan string |
| 400 | `BAD_REQUEST` | `tenant_id is required` | `tenant_id` kosong atau hanya spasi |
| 400 | `BAD_REQUEST` | `invalid request: page` atau `invalid request: page_size` | nilai pagination kurang dari 1 atau bukan integer |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, dicabut, atau pengguna nonaktif |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak punya akses ke `tenant_id` |
| 404 | `NOT_FOUND` | `tenant not found` | tenant tidak ada |
| 500 | `INTERNAL_SERVER_ERROR` | `an unexpected error occurred` | `JWT_SECRET` belum diatur atau kegagalan server |

## `POST /api/v1/whatsapp/chats`

Mengembalikan semua pesan dari satu percakapan, diurutkan dari `created_at` terlama dengan `id` sebagai pemecah waktu yang sama.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`.

**Request**

```json
{
  "conv_id": "CSzBhHYZH2h61r5eXoe6n",
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Required |
|---|---|---|
| `conv_id` | string | yes |
| `page` | integer, minimum 1 | no |
| `page_size` | integer, minimum 1 | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "chats retrieved successfully",
  "data": {
    "list": [
      {
        "id": "G8k2r6v5mPq9T4hN0sW3x",
        "conv_id": "CSzBhHYZH2h61r5eXoe6n",
        "wam_id": "wamid.HBgMNjI4MjIxMzk1MDAyMRUCABIY",
        "direction": "inbound",
        "sender_type": "user",
        "reply_to_id": null,
        "type": "text",
        "message": "Halo, saya mau tanya kerja sama.",
        "attachment": null,
        "status": null,
        "sent_at": null,
        "delivered_at": null,
        "read_at": null,
        "failed_at": null,
        "created_at": "2026-09-02T10:00:08+00:00",
        "updated_at": "2026-09-02T10:00:08+00:00"
      }
    ],
    "metapaging": {
      "total_data": 1,
      "total_page": 1,
      "current_page": 1,
      "page_size": 20
    }
  }
}
```

`attachment` berisi metadata pesan nonteks dan bisa memuat `storage_url` setelah media berhasil diunggah. `status` serta waktu pengiriman, penerimaan, baca, dan gagal dapat bernilai `null`. Pagination sama dengan endpoint percakapan.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: conv_id` | `conv_id` tidak dikirim atau bukan string |
| 400 | `BAD_REQUEST` | `conv_id is required` | `conv_id` kosong atau hanya spasi |
| 400 | `BAD_REQUEST` | `invalid request: page` atau `invalid request: page_size` | nilai pagination kurang dari 1 atau bukan integer |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, dicabut, atau pengguna nonaktif |
| 404 | `NOT_FOUND` | `conversation not found` | percakapan tidak ada atau tenant-nya di luar akses pengguna |
| 500 | `INTERNAL_SERVER_ERROR` | `an unexpected error occurred` | `JWT_SECRET` belum diatur atau kegagalan server |

## `GET /api/v1/webhook/whatsapp/callback/{app_id}`

Menjawab verifikasi langganan webhook Meta dengan mengembalikan challenge persis seperti yang diterima.

**Method:** `GET`

**Authorization:** `hub.verify_token` yang cocok dengan `meta_apps.webhook_verify_token` untuk `app_id` aktif.

**Request** — field berikut dikirim sebagai query parameter, bukan body JSON.

```json
{
  "hub.mode": "subscribe",
  "hub.verify_token": "token-verifikasi-meta",
  "hub.challenge": "123456789"
}
```

| Field | Type | Required |
|---|---|---|
| `app_id` | string, segmen URL | yes |
| `hub.mode` | string, harus `subscribe` | yes |
| `hub.verify_token` | string | yes |
| `hub.challenge` | string | yes |

**Response** — `200 OK`, body berupa teks biasa tanpa envelope JSON.

```text
123456789
```

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 403 | `FORBIDDEN` | `Forbidden` | App tidak aktif/tidak dikenal, mode salah, atau verify token tidak cocok |
| 500 | `INTERNAL_SERVER_ERROR` | kegagalan server | lookup kredensial App gagal |

## `POST /api/v1/webhook/whatsapp/callback/{app_id}`

Menerima event Meta, menyimpan payload valid ke `wa_webhook_events` sebelum membalas, lalu memproses pesan dan status dari baris tersebut di belakang respons.

**Method:** `POST`

**Authorization:** header `X-Hub-Signature-256` yang diverifikasi memakai `meta_apps.app_secret` untuk `app_id` aktif.

Jika `app_secret` kosong, pemeriksaan signature dilewati untuk pengembangan lokal.

**Request** — contoh ringkas event pesan masuk.

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "123456789012345",
      "changes": [
        {
          "field": "messages",
          "value": {
            "metadata": {"phone_number_id": "987654321098765"},
            "contacts": [{"profile": {"name": "Vicky"}}],
            "messages": [
              {
                "id": "wamid.HBgMNjI4MjIxMzk1MDAyMRUCABIY",
                "from": "6282213950021",
                "timestamp": "1788343208",
                "type": "text",
                "text": {"body": "Halo, saya mau tanya kerja sama."}
              }
            ]
          }
        }
      ]
    }
  ]
}
```

| Field | Type | Required |
|---|---|---|
| `app_id` | string, segmen URL | yes |
| `X-Hub-Signature-256` | string, header signature | yes jika `app_secret` diisi |
| `object` | string | yes untuk diproses |
| `entry` | array | no |
| `entry[].changes[].field` | string | yes untuk diproses |
| `entry[].changes[].value.metadata.phone_number_id` | string | yes untuk routing tenant |

**Response** — `200 OK`, body kosong tanpa envelope JSON.

Payload dengan `object` lain atau body yang bukan JSON tetap dibalas `200` dan diabaikan. Event yang disimpan dapat berisi `messages`, `smb_message_echoes`, dan status delivery. Pesan masuk maupun echo di-upsert ke `wa_chats`; tenant ditentukan dari `metadata.phone_number_id` lewat `meta_connections`. Pemrosesan melakukan commit per pesan dan sweeper mengulang event yang tertinggal. `200` berarti payload telah diterima, bukan seluruh pesannya telah selesai diproses.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | `Invalid signature` | signature tidak cocok saat `app_secret` diisi |
| 403 | `FORBIDDEN` | `Forbidden` | App tidak aktif atau tidak dikenal |
| 500 | `INTERNAL_SERVER_ERROR` | kegagalan server | lookup App atau penyimpanan event gagal |
