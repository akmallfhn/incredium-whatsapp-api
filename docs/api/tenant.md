# Tenant

Endpoint ini membuat dan memperbarui tenant, menampilkan detail koneksi WhatsApp, serta mendaftarkan app Meta milik koneksi ke webhook WABA. Semua endpoint memakai JWT hasil `auth/login`. Pengguna yang login dapat membuat tenant dan langsung mendapat akses melalui `users_access`; endpoint lain dibatasi ke tenant yang dapat diaksesnya. Detail koneksi diperiksa langsung ke Graph API Meta pada saat permintaan.

## `POST /api/v1/tenants/create`

Membuat tenant aktif dan memberikan akses ke pengguna yang membuatnya dalam satu transaksi.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`; semua pengguna yang login.

**Request**

```json
{
  "name": "TRC Brand Manager",
  "image_url": "https://example.com/trc-logo.png",
  "legal_name": "PT TRC Brand Manager"
}
```

| Field | Type | Required |
|---|---|---|
| `name` | string, maksimal 255 karakter setelah trim | yes |
| `image_url` | URL HTTP/HTTPS atau `null` | no |
| `legal_name` | string, maksimal 255 karakter setelah trim, atau `null` | no |

**Response** — `201 CREATED`

```json
{
  "success": true,
  "code": 201,
  "status": "CREATED",
  "message": "tenant created successfully",
  "data": {
    "id": "8yuPA4qUjqC3OfizucQoH",
    "name": "TRC Brand Manager",
    "slug": "trc-brand-manager",
    "image_url": "https://example.com/trc-logo.png",
    "legal_name": "PT TRC Brand Manager",
    "status": "active",
    "active_agent_id": null,
    "created_at": "2026-10-13T09:00:00+00:00",
    "updated_at": "2026-10-13T09:00:00+00:00"
  }
}
```

`slug` dibuat otomatis dari `name`. Jika sudah terpakai, backend menambahkan akhiran unik. `image_url` dan `legal_name` bernilai `null` bila tidak dikirim. `legal_name` kosong disimpan sebagai `null`.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | field wajib hilang, tipe salah, atau URL gambar tidak valid |
| 400 | `BAD_REQUEST` | `name is required` | nama kosong atau hanya spasi |
| 400 | `BAD_REQUEST` | `name exceeds 255 characters` | nama terlalu panjang |
| 400 | `BAD_REQUEST` | `legal_name exceeds 255 characters` | nama legal terlalu panjang |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, dicabut, atau pengguna nonaktif |
| 409 | `CONFLICT` | `tenant slug is unavailable` | slug masih bertabrakan setelah beberapa percobaan |
| 500 | `INTERNAL_SERVER_ERROR` | `an unexpected error occurred` | konfigurasi autentikasi atau database bermasalah |

## `POST /api/v1/tenants/update`

Memperbarui satu atau beberapa informasi tenant yang dapat diakses pengguna.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`; semua pengguna yang punya akses tenant.

**Request**

```json
{
  "id": "8yuPA4qUjqC3OfizucQoH",
  "name": "TRC Creative",
  "image_url": null,
  "legal_name": "PT TRC Creative Indonesia"
}
```

| Field | Type | Required |
|---|---|---|
| `id` | string | yes |
| `name` | string, maksimal 255 karakter setelah trim | no |
| `image_url` | URL HTTP/HTTPS atau `null` | no |
| `legal_name` | string, maksimal 255 karakter setelah trim, atau `null` | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "tenant updated successfully",
  "data": {
    "id": "8yuPA4qUjqC3OfizucQoH",
    "name": "TRC Creative",
    "slug": "trc-brand-manager",
    "image_url": null,
    "legal_name": "PT TRC Creative Indonesia",
    "status": "active",
    "active_agent_id": null,
    "created_at": "2026-10-13T09:00:00+00:00",
    "updated_at": "2026-10-13T09:10:00+00:00"
  }
}
```

Field yang tidak dikirim tetap seperti sebelumnya. Kirim `null` untuk menghapus `image_url` atau `legal_name`. `name` tidak boleh `null`. Perubahan `name` tidak mengubah `slug`, karena slug dipakai sebagai folder media di Storage.

**Errors**

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | field wajib hilang, tipe salah, atau URL gambar tidak valid |
| 400 | `BAD_REQUEST` | `id is required` | ID kosong atau hanya spasi |
| 400 | `BAD_REQUEST` | `at least one field is required` | hanya `id` yang dikirim |
| 400 | `BAD_REQUEST` | `name is required` | `name` dikirim sebagai `null`, kosong, atau hanya spasi |
| 400 | `BAD_REQUEST` | `name exceeds 255 characters` | nama terlalu panjang |
| 400 | `BAD_REQUEST` | `legal_name exceeds 255 characters` | nama legal terlalu panjang |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, dicabut, atau pengguna nonaktif |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak punya akses ke tenant ini atau tenant nonaktif |
| 404 | `NOT_FOUND` | `tenant not found` | tenant yang dapat diakses tidak ditemukan |
| 500 | `INTERNAL_SERVER_ERROR` | `an unexpected error occurred` | konfigurasi autentikasi atau database bermasalah |

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
    "image_url": "https://example.com/trc-logo.png",
    "legal_name": "PT TRC Brand Manager",
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
