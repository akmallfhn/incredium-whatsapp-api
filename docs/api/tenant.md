# Tenant

Endpoint ini menampilkan data satu tenant beserta semua koneksi WhatsApp-nya di `meta_connections`, serta dapat mendaftarkan app Meta milik koneksi ke webhook WABA. Detail koneksi diperiksa langsung ke Graph API Meta pada saat permintaan, jadi hasilnya menunjukkan kondisi nyata nomor tersebut, bukan hanya isi database: apakah nomornya terhubung ke Cloud API, apakah juga dipakai di aplikasi WhatsApp Business (coexistence), dan apakah app Meta milik koneksi itu masih berlangganan webhook WABA-nya. Akses memakai JWT hasil `auth/login` dan dibatasi tenant yang tercatat di `users_access`.

## `POST /api/v1/tenants/details`

Mengembalikan detail satu tenant dan status setiap koneksi WhatsApp-nya menurut Meta.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`.

**Request**

```json
{
  "id": "8yuPA4qUjqC3OfizucQoH"
}
```

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "tenant retrieved successfully",
  "data": {
    "id": "8yuPA4qUjqC3OfizucQoH",
    "name": "TRC Brand Manager",
    "slug": "trc-brand-manager",
    "status": "active",
    "active_agent_id": null,
    "connections": [
      {
        "id": "NcejwmWLTX1N3_uyJWDZ5",
        "waba_id": "1752524935415356",
        "phone_number_id": "981890488339995",
        "display_number": "+62 813-2881-1777",
        "app_id": "1372054147774697",
        "status": "active",
        "token_expires_at": null,
        "meta": {
          "connected": true,
          "phone_status": "CONNECTED",
          "platform_type": "CLOUD_API",
          "is_on_biz_app": true,
          "coexistence": true,
          "webhook_subscribed": true,
          "display_phone_number": "+62 813-2881-1777",
          "verified_name": "Vanessa Valensia",
          "quality_rating": "UNKNOWN",
          "error": null
        }
      }
    ]
  }
}
```

`status` di level tenant dan koneksi adalah status di database (`active` atau `inactive`); koneksi `inactive` tetap ditampilkan dan tetap diperiksa ke Meta. `connections` urut dari koneksi tertua dan bisa kosong. `display_number` diambil dari database dan memakai `meta.display_phone_number` kalau kolomnya masih kosong.

`active_agent_id` adalah agent balasan WhatsApp yang dipilih tenant; `null` berarti balasan AI mati.

Isi `meta` berasal dari dua panggilan Graph API per koneksi: `GET /{phone_number_id}` dan `GET /{waba_id}/subscribed_apps`.

| Field `meta` | Arti |
|---|---|
| `connected` | `true` hanya kalau `phone_status` `CONNECTED` dan `webhook_subscribed` `true`, yaitu nomor aktif dan event-nya benar-benar sampai ke app ini |
| `phone_status` | status nomor menurut Meta, misalnya `CONNECTED`, `PENDING`, `DISCONNECTED`, `FLAGGED`, `RESTRICTED` |
| `platform_type` | `CLOUD_API` kalau nomor terdaftar di Cloud API |
| `is_on_biz_app` | `true` kalau nomor juga aktif di aplikasi WhatsApp Business |
| `coexistence` | `true` kalau `platform_type` `CLOUD_API` dan `is_on_biz_app` `true` |
| `webhook_subscribed` | `true` kalau `app_id` koneksi ini ada di daftar app yang berlangganan webhook WABA; `false` berarti event dari nomor ini tidak dikirim ke app ini |
| `quality_rating` | `GREEN`, `YELLOW`, `RED`, atau `UNKNOWN` |
| `error` | alasan dari Meta kalau salah satu panggilan gagal, misalnya token kedaluwarsa; field yang gagal diambil bernilai `null` |

Kegagalan ke Meta tidak menggagalkan endpoint: respons tetap `200` dengan `meta.error` terisi dan `connected` bernilai `false`. Karena memanggil Meta setiap kali, endpoint ini tidak cocok dipanggil berulang dalam interval pendek.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: id` | `id` tidak dikirim atau bukan string |
| 400 | `BAD_REQUEST` | `id is required` | `id` kosong atau hanya spasi |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, dicabut, atau pengguna nonaktif |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak punya akses ke tenant ini, atau tenant-nya `inactive` |
| 404 | `NOT_FOUND` | `tenant not found` | tenant tidak ada |
| 500 | `INTERNAL_SERVER_ERROR` | `an unexpected error occurred` | `JWT_SECRET` belum diatur atau kegagalan server |

## `POST /api/v1/tenants/connections/subscribe`

Mendaftarkan app Meta yang terhubung ke satu koneksi WhatsApp tenant sebagai penerima webhook WABA.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`; peran `Administrator` atau `Super Admin` dengan akses tenant.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "connection_id": "NcejwmWLTX1N3_uyJWDZ5"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `connection_id` | string | yes |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "whatsapp app subscribed successfully",
  "data": {
    "tenant_id": "8yuPA4qUjqC3OfizucQoH",
    "connection_id": "NcejwmWLTX1N3_uyJWDZ5",
    "waba_id": "1752524935415356",
    "app_id": "1372054147774697",
    "webhook_subscribed": true,
    "already_subscribed": false
  }
}
```

Endpoint mengambil WABA, app, dan access token dari koneksi yang tersimpan; klien tidak dapat mengganti tujuan subscription lewat body. Sebelum mengirim `POST /{waba_id}/subscribed_apps` ke Meta, backend memastikan token berasal dari app yang tercatat di koneksi. Setelahnya, backend membaca ulang daftar app subscribed untuk memastikan app tersebut muncul. Jika sudah subscribed, endpoint tidak mengirim `POST` lagi dan mengembalikan `already_subscribed: true`.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | field wajib hilang atau bukan string |
| 400 | `BAD_REQUEST` | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | `BAD_REQUEST` | `connection_id is required` | ID koneksi kosong atau hanya spasi |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak punya akses tenant |
| 403 | `FORBIDDEN` | `connection management denied` | peran pengguna tidak boleh mengubah subscription |
| 404 | `NOT_FOUND` | `connection not found` | koneksi tidak ada pada tenant |
| 409 | `CONFLICT` | `connection or Meta app is inactive` | koneksi atau app tidak aktif |
| 409 | `CONFLICT` | `connection access token is empty` | koneksi tidak punya token |
| 409 | `CONFLICT` | `access token belongs to another Meta app` | token berasal dari app lain |
| 502 | `BAD_GATEWAY` | `Meta subscription failed: ...` | Graph API Meta menolak atau tidak dapat dihubungi |
| 502 | `BAD_GATEWAY` | `Meta did not list the app after subscription` | Meta mengakui permintaan tetapi verifikasi daftar belum berhasil |
