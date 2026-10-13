# WhatsApp

Endpoint ini membaca percakapan dan chat WhatsApp, menandai percakapan sudah dibaca, mengirim balasan teks, serta menerima verifikasi dan event webhook dari Meta. Endpoint daftar memakai JWT hasil `auth/login` dan membatasi data menurut akses tenant pengguna yang tersimpan di `users_access`; callback Meta memakai verify token atau signature milik `meta_apps` sesuai `app_id` pada URL.

## `POST /api/v1/whatsapp/conversations`

Mengembalikan percakapan milik satu tenant yang cocok dengan filter, diurutkan seperti inbox WhatsApp: `last_message_at` terbaru di atas, dengan `id` sebagai pemecah waktu yang sama. Percakapan tanpa chat memakai `created_at`-nya sebagai pengganti.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "search": "vicky",
  "stage_id": "Qm3vX8pL2nR6tY9wK4sJd",
  "mode": "human",
  "handler_id": null,
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `search` | string | no |
| `stage_id` | string | no |
| `mode` | string, `ai` atau `human` | no |
| `handler_id` | string UUID atau `null` | no |
| `page` | integer, minimum 1 | no |
| `page_size` | integer, minimum 1 | no |

`search` mencocokkan sebagian teks tanpa membedakan huruf besar-kecil pada nama kontak, nomor telepon, `brand_name` lead, dan isi chat mana pun di percakapan itu. `stage_id`, `mode`, dan `handler_id` memfilter data lead di `wa_leads`. `handler_id` yang dikirim `null` berarti hanya percakapan tanpa handler, sedangkan field yang tidak dikirim berarti tanpa filter handler. `search` dan `stage_id` yang kosong diabaikan.

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
        "meta_connection_id": "Fb2qL4nMx8pR0sT5vW9yZ",
        "full_name": "Vicky",
        "phone_number": "6282213950021",
        "last_read_id": null,
        "unread_count": 2,
        "window_expired": false,
        "last_message": "Baik kak, kami cek dulu ya.",
        "last_message_type": "text",
        "last_message_direction": "outbound",
        "last_message_status": "read",
        "last_message_at": "2026-09-02T10:05:12+00:00",
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

Field `last_message_*` diambil dari chat terbaru percakapan itu menurut `created_at`. `last_message_type` memakai nilai `wac_type_enum` (`text`, `image`, `document`, `audio`, `template`, dan seterusnya), dan `last_message` bisa berupa string kosong untuk pesan nonteks tanpa caption. `last_message_status` bernilai `sent`, `delivered`, `read`, atau `failed` hanya untuk `last_message_direction` `outbound`, dan selalu `null` untuk `inbound`. Pesan yang dikirim admin dari aplikasi WhatsApp Business langsung bernilai `sent` begitu echo-nya masuk, lalu naik ke `delivered` atau `read` kalau Meta mengirim statusnya; untuk sebagian pesan dari aplikasi, Meta tidak pernah mengirim status lanjutan sehingga tetap `sent`. Pesan dari `POST /api/v1/whatsapp/send` bisa `null` sampai status pertamanya datang. Percakapan tanpa chat sama sekali mengembalikan `null` di kelima field ini.

`meta_connection_id` menunjukkan nomor WhatsApp bisnis yang memiliki percakapan. Pelanggan yang sama dapat memiliki percakapan terpisah jika menghubungi nomor bisnis lain dalam tenant yang sama.

`unread_count` menghitung chat `inbound` yang lebih baru dari chat `last_read_id`; kalau `last_read_id` masih `null`, semua chat `inbound` terhitung. `window_expired` bernilai `true` kalau chat `inbound` terakhir sudah 24 jam atau lebih, atau belum ada sama sekali. Selama `true`, Meta hanya menerima pesan template, jadi `POST /api/v1/whatsapp/send` akan menolak dengan `409`.

`page` default `1`, `page_size` default `20` dan dibatasi maksimum `100`. Daftar kosong tetap mengembalikan `list: []` dan `total_page: 0`.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: tenant_id` | `tenant_id` tidak dikirim atau bukan string |
| 400 | `BAD_REQUEST` | `tenant_id is required` | `tenant_id` kosong atau hanya spasi |
| 400 | `BAD_REQUEST` | `invalid request: mode` | `mode` selain `ai` atau `human` |
| 400 | `BAD_REQUEST` | `invalid request: handler_id` | `handler_id` bukan UUID |
| 400 | `BAD_REQUEST` | `invalid request: page` atau `invalid request: page_size` | nilai pagination kurang dari 1 atau bukan integer |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, dicabut, atau pengguna nonaktif |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak punya akses ke `tenant_id` |
| 404 | `NOT_FOUND` | `tenant not found` | tenant tidak ada |
| 500 | `INTERNAL_SERVER_ERROR` | `an unexpected error occurred` | `JWT_SECRET` belum diatur atau kegagalan server |

## `POST /api/v1/whatsapp/chats`

Mengembalikan pesan dari satu percakapan, diurutkan dari `created_at` terbaru dengan `id` sebagai pemecah waktu yang sama, jadi `page` 1 selalu berisi pesan paling baru.

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

`attachment` berisi metadata pesan nonteks dan bisa memuat `storage_url` setelah media berhasil diunggah. `status` serta waktu pengiriman, penerimaan, baca, dan gagal dapat bernilai `null`. Pagination sama dengan endpoint percakapan; `page` berikutnya berisi pesan yang lebih lama. Balik urutan `list` untuk menampilkannya dari atas ke bawah. Kalau ada pesan baru masuk di antara dua permintaan, isi halaman bergeser satu posisi, jadi hilangkan duplikat berdasarkan `id` saat menggabungkan halaman.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: conv_id` | `conv_id` tidak dikirim atau bukan string |
| 400 | `BAD_REQUEST` | `conv_id is required` | `conv_id` kosong atau hanya spasi |
| 400 | `BAD_REQUEST` | `invalid request: page` atau `invalid request: page_size` | nilai pagination kurang dari 1 atau bukan integer |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, dicabut, atau pengguna nonaktif |
| 404 | `NOT_FOUND` | `conversation not found` | percakapan tidak ada atau tenant-nya di luar akses pengguna |
| 500 | `INTERNAL_SERVER_ERROR` | `an unexpected error occurred` | `JWT_SECRET` belum diatur atau kegagalan server |

## `POST /api/v1/whatsapp/update/conversation-as-read`

Menandai percakapan sudah dibaca sampai chat terbarunya, sehingga `unread_count` kembali `0` sampai chat `inbound` berikutnya masuk.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`.

**Request**

```json
{
  "conv_id": "CSzBhHYZH2h61r5eXoe6n"
}
```

| Field | Type | Required |
|---|---|---|
| `conv_id` | string | yes |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "conversation marked as read",
  "data": {
    "id": "CSzBhHYZH2h61r5eXoe6n",
    "last_read_id": "G8k2r6v5mPq9T4hN0sW3x",
    "unread_count": 0
  }
}
```

`last_read_id` diisi chat terbaru apa pun arahnya, dan tetap `null` kalau percakapan belum punya chat. Memanggilnya berulang kali aman.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: conv_id` | `conv_id` tidak dikirim atau bukan string |
| 400 | `BAD_REQUEST` | `conv_id is required` | `conv_id` kosong atau hanya spasi |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, dicabut, atau pengguna nonaktif |
| 404 | `NOT_FOUND` | `conversation not found` | percakapan tidak ada atau tenant-nya di luar akses pengguna |
| 500 | `INTERNAL_SERVER_ERROR` | `an unexpected error occurred` | `JWT_SECRET` belum diatur atau kegagalan server |

## `POST /api/v1/whatsapp/send`

Mengirim balasan teks ke kontak sebuah percakapan lewat WhatsApp Cloud API, lalu menyimpannya sebagai chat `outbound`.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`.

**Request**

```json
{
  "conv_id": "CSzBhHYZH2h61r5eXoe6n",
  "message": "Baik kak, kami cek dulu ya.",
  "reply_to_id": "G8k2r6v5mPq9T4hN0sW3x"
}
```

| Field | Type | Required |
|---|---|---|
| `conv_id` | string | yes |
| `message` | string, maksimum 4096 karakter | yes |
| `reply_to_id` | string, `id` chat di percakapan yang sama | no |

**Response** — `201 CREATED`

```json
{
  "success": true,
  "code": 201,
  "status": "CREATED",
  "message": "message sent successfully",
  "data": {
    "id": "Hx7c1QwE9rTz3LbV5nM2a",
    "conv_id": "CSzBhHYZH2h61r5eXoe6n",
    "wam_id": "wamid.HBgMNjI4MjIxMzk1MDAyMRUCABEYEjA4",
    "direction": "outbound",
    "sender_type": "admin",
    "reply_to_id": "G8k2r6v5mPq9T4hN0sW3x",
    "type": "text",
    "message": "Baik kak, kami cek dulu ya.",
    "attachment": null,
    "status": null,
    "sent_at": null,
    "delivered_at": null,
    "read_at": null,
    "failed_at": null,
    "created_at": "2026-09-02T10:05:12+00:00",
    "updated_at": "2026-09-02T10:05:12+00:00"
  }
}
```

Bentuk `data` sama dengan item `POST /api/v1/whatsapp/chats`. `201` berarti Meta sudah menerima pesannya, belum berarti terkirim ke kontak: `status` biasanya masih `null`, lalu diisi `sent`, `delivered`, `read`, atau `failed` oleh webhook status. Pesan dikirim dari nomor `meta_connections` yang ditunjuk oleh `wa_conversations.meta_connection_id`; koneksi tersebut harus aktif. `message` dipangkas spasinya di awal dan akhir sebelum dikirim. Saat ini hanya pesan teks yang didukung.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: conv_id` atau `invalid request: message` | field wajib tidak dikirim atau bukan string |
| 400 | `BAD_REQUEST` | `conv_id is required` | `conv_id` kosong atau hanya spasi |
| 400 | `BAD_REQUEST` | `message is required` | `message` kosong atau hanya spasi |
| 400 | `BAD_REQUEST` | `message exceeds 4096 characters` | `message` lebih dari 4096 karakter |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, dicabut, atau pengguna nonaktif |
| 404 | `NOT_FOUND` | `conversation not found` | percakapan tidak ada atau tenant-nya di luar akses pengguna |
| 404 | `NOT_FOUND` | `reply message not found` | `reply_to_id` tidak ada di percakapan ini |
| 409 | `CONFLICT` | `customer service window has expired` | chat `inbound` terakhir sudah 24 jam atau lebih, atau belum ada |
| 409 | `CONFLICT` | `tenant has no active whatsapp connection` | tenant tidak punya `meta_connections` aktif dengan `access_token` |
| 500 | `INTERNAL_SERVER_ERROR` | `failed to send message: <alasan dari Meta>` | Meta menolak pesan atau tidak bisa dihubungi |
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
