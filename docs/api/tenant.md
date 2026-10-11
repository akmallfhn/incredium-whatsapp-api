# Tenant

Endpoint ini menampilkan data satu tenant beserta semua koneksi WhatsApp-nya di `meta_connections`. Setiap koneksi diperiksa langsung ke Graph API Meta pada saat permintaan, jadi hasilnya menunjukkan kondisi nyata nomor tersebut, bukan hanya isi database: apakah nomornya terhubung ke Cloud API, apakah juga dipakai di aplikasi WhatsApp Business (coexistence), dan apakah app Meta milik koneksi itu masih berlangganan webhook WABA-nya. Akses memakai JWT hasil `auth/login` dan dibatasi tenant yang tercatat di `users_access`.

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
