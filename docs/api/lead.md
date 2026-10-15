# Lead WhatsApp

Endpoint ini membaca dan memperbarui data lead dari percakapan WhatsApp yang sudah ada, serta menampilkan stage aktif untuk pilihan formulir. Pengguna harus memiliki akses ke tenant pemilik percakapan. Perubahan mode menentukan penanganan pesan berikutnya; mode `ai` memerlukan konfigurasi agent aktif agar balasan otomatis dapat berjalan.

## `POST /api/v1/lead-stages`

Mengambil stage aktif milik tenant sesuai urutan pipeline untuk pilihan pada formulir lead.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`; pengguna dengan akses tenant.

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
| `page` | integer, minimal 1; default 1 | no |
| `page_size` | integer, minimal 1; default 20, maksimum efektif 100 | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "lead stages retrieved successfully",
  "data": {
    "list": [
      {
        "id": "Qm3vX8pL2nR6tY9wK4sJd",
        "tenant_id": "8yuPA4qUjqC3OfizucQoH",
        "key": "qualified",
        "name": "Qualified",
        "description": "Lead sudah memenuhi kriteria awal.",
        "position": 2
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

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | tipe atau nilai pagination salah |
| 400 | `BAD_REQUEST` | `tenant_id is required` | tenant kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang atau tidak sah |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak punya akses tenant |

## `POST /api/v1/leads/details`

Mengambil data lead untuk satu percakapan WhatsApp.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`; pengguna dengan akses tenant percakapan.

**Request**

```json
{
  "conv_id": "fF4vJ2lA8sTrN0qLmP5xB"
}
```

| Field | Type | Required |
|---|---|---|
| `conv_id` | string ID percakapan | yes |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "lead retrieved successfully",
  "data": {
    "conv_id": "fF4vJ2lA8sTrN0qLmP5xB",
    "stage_id": "Qm3vX8pL2nR6tY9wK4sJd",
    "handler_id": null,
    "mode": "ai",
    "note": null,
    "created_at": "2026-10-15T09:00:00+00:00",
    "updated_at": "2026-10-15T09:00:00+00:00"
  }
}
```

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | field wajib hilang atau tipe salah |
| 400 | `BAD_REQUEST` | `conv_id is required` | ID percakapan kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang atau tidak sah |
| 404 | `NOT_FOUND` | `conversation not found` | percakapan tidak ada atau pengguna tidak punya akses tenant |
| 404 | `NOT_FOUND` | `lead not found` | percakapan belum memiliki baris lead |

## `POST /api/v1/leads/change-mode`

Mengubah mode lead secara eksplisit menjadi `ai` atau `human`.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`; pengguna dengan akses tenant percakapan.

**Request**

```json
{
  "conv_id": "fF4vJ2lA8sTrN0qLmP5xB",
  "mode": "human"
}
```

| Field | Type | Required |
|---|---|---|
| `conv_id` | string ID percakapan | yes |
| `mode` | `ai` atau `human` | yes |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "lead mode updated successfully",
  "data": {
    "conv_id": "fF4vJ2lA8sTrN0qLmP5xB",
    "stage_id": "Qm3vX8pL2nR6tY9wK4sJd",
    "handler_id": null,
    "mode": "human",
    "note": null,
    "created_at": "2026-10-15T09:00:00+00:00",
    "updated_at": "2026-10-15T09:05:00+00:00"
  }
}
```

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | field wajib hilang atau mode salah |
| 400 | `BAD_REQUEST` | `conv_id is required` | ID percakapan kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang atau tidak sah |
| 404 | `NOT_FOUND` | `conversation not found` | percakapan tidak ada atau pengguna tidak punya akses tenant |
| 404 | `NOT_FOUND` | `lead not found` | percakapan belum memiliki baris lead |

## `POST /api/v1/leads/update`

Memperbarui handler, catatan, atau stage lead; field yang tidak dikirim tetap seperti semula dan `null` mengosongkan field.

**Method:** `POST`

**Authorization:** `Bearer <jwt>` dari `POST /api/v1/auth/login`; pengguna dengan akses tenant percakapan.

**Request**

```json
{
  "conv_id": "fF4vJ2lA8sTrN0qLmP5xB",
  "handler_id": "c595537e-40f6-42a5-a629-dcd925cf87ca",
  "note": "Pasien menunggu jadwal konsultasi",
  "stage_id": "Qm3vX8pL2nR6tY9wK4sJd"
}
```

| Field | Type | Required |
|---|---|---|
| `conv_id` | string ID percakapan | yes |
| `handler_id` | UUID pengguna aktif dengan akses tenant, atau `null` | no |
| `note` | string atau `null` | no |
| `stage_id` | string ID stage aktif dalam tenant, atau `null` | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "lead updated successfully",
  "data": {
    "conv_id": "fF4vJ2lA8sTrN0qLmP5xB",
    "stage_id": "Qm3vX8pL2nR6tY9wK4sJd",
    "handler_id": "c595537e-40f6-42a5-a629-dcd925cf87ca",
    "mode": "human",
    "note": "Pasien menunggu jadwal konsultasi",
    "created_at": "2026-10-15T09:00:00+00:00",
    "updated_at": "2026-10-15T09:10:00+00:00"
  }
}
```

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | field wajib hilang atau format UUID salah |
| 400 | `BAD_REQUEST` | `conv_id is required` | ID percakapan kosong |
| 400 | `BAD_REQUEST` | `at least one field is required` | tidak ada field perubahan |
| 400 | `BAD_REQUEST` | `stage_id is required` | ID stage string kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang atau tidak sah |
| 404 | `NOT_FOUND` | `conversation not found` | percakapan tidak ada atau pengguna tidak punya akses tenant |
| 404 | `NOT_FOUND` | `lead not found` | percakapan belum memiliki baris lead |
| 404 | `NOT_FOUND` | `handler not found` | pengguna tidak aktif atau tidak punya akses tenant |
| 404 | `NOT_FOUND` | `lead stage not found` | stage tidak aktif atau berasal dari tenant lain |
