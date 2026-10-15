# Pasien

Endpoint ini mengelola kategori dan data pasien per tenant. Semua endpoint memakai JWT dari `auth/login`, memeriksa akses tenant, dan menerima JSON melalui `POST`. ID kategori bertambah otomatis, sedangkan ID pasien dibuat dengan nanoid(). Satu percakapan WhatsApp hanya dapat terhubung ke satu pasien dalam tenant yang sama.

## `POST /api/v1/patient-categories/create`

Membuat kategori pasien untuk satu tenant.

**Method:** `POST`

**Authorization:** `Bearer <jwt>`; pengguna dengan akses tenant.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "name": "Umum"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `name` | string, maksimal 255 karakter | yes |

**Response** — `201 CREATED`

```json
{
  "success": true,
  "code": 201,
  "status": "CREATED",
  "message": "patient category created successfully",
  "data": {
    "id": 1,
    "tenant_id": "8yuPA4qUjqC3OfizucQoH",
    "name": "Umum",
    "created_at": "2026-10-15T09:00:00+00:00",
    "updated_at": "2026-10-15T09:00:00+00:00"
  }
}
```

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | field wajib hilang atau tipe salah |
| 400 | `BAD_REQUEST` | `tenant_id is required` | tenant kosong |
| 400 | `BAD_REQUEST` | `name is required` | nama kosong |
| 400 | `BAD_REQUEST` | `name exceeds 255 characters` | nama terlalu panjang |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT tidak sah |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak memiliki akses tenant |
| 409 | `CONFLICT` | `patient category already exists` | nama kategori sudah terpakai di tenant |

## `POST /api/v1/patient-categories`

Mengambil kategori pasien dengan pagination untuk pilihan pada formulir.

**Method:** `POST`

**Authorization:** `Bearer <jwt>`; pengguna dengan akses tenant.

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
| `page_size` | integer, minimal 1; default 20, maksimal efektif 100 | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "patient categories retrieved successfully",
  "data": {
    "list": [
      {
        "id": 1,
        "tenant_id": "8yuPA4qUjqC3OfizucQoH",
        "name": "Umum",
        "created_at": "2026-10-15T09:00:00+00:00",
        "updated_at": "2026-10-15T09:00:00+00:00"
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
| 400 | `BAD_REQUEST` | `invalid request: <field>` | nilai halaman atau tipe salah |
| 400 | `BAD_REQUEST` | `tenant_id is required` | tenant kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT tidak sah |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak memiliki akses tenant |

## `POST /api/v1/patients`

Mengambil pasien dengan filter nama, telepon, dan kategori.

**Method:** `POST`

**Authorization:** `Bearer <jwt>`; pengguna dengan akses tenant.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "search": "Siti",
  "category_id": 1,
  "conversation_id": null,
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `search` | string atau `null` | no |
| `category_id` | integer atau `null` | no |
| `conversation_id` | string ID percakapan atau `null` | no |
| `page` | integer, minimal 1; default 1 | no |
| `page_size` | integer, minimal 1; default 20, maksimal efektif 100 | no |

Kirim `conversation_id` untuk menemukan pasien yang sudah terhubung ke satu percakapan; hilangkan field atau kirim `null` untuk mencari seluruh pasien tenant.

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "patients retrieved successfully",
  "data": {
    "list": [
      {
        "id": "pR8vK2nT5xQaL7mZ0cYhJ",
        "tenant_id": "8yuPA4qUjqC3OfizucQoH",
        "category_id": 1,
        "conversation_id": null,
        "name": "Siti Aminah",
        "satu_sehat_id": null,
        "birth_date": "1995-04-12",
        "birth_place": "Bandung",
        "national_id": null,
        "bpjs_number": null,
        "address": null,
        "phone_number": null,
        "email": null,
        "gender": "female",
        "blood_type": null,
        "allergy_history": null,
        "created_at": "2026-10-15T09:00:00+00:00",
        "updated_at": "2026-10-15T09:00:00+00:00"
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
| 400 | `BAD_REQUEST` | `invalid request: <field>` | filter atau halaman salah |
| 400 | `BAD_REQUEST` | `tenant_id is required` | tenant kosong |
| 400 | `BAD_REQUEST` | `conversation_id is required` | filter ID percakapan berupa string kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT tidak sah |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak memiliki akses tenant |

## `POST /api/v1/patients/create`

Membuat pasien baru; `conversation_id` boleh langsung diisi dengan percakapan milik tenant yang sama, atau dibiarkan `null`.

**Method:** `POST`

**Authorization:** `Bearer <jwt>`; pengguna dengan akses tenant.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "category_id": 1,
  "name": "Siti Aminah",
  "conversation_id": "fF4vJ2lA8sTrN0qLmP5xB",
  "satu_sehat_id": null,
  "birth_date": "1995-04-12",
  "birth_place": "Bandung",
  "national_id": null,
  "bpjs_number": null,
  "address": null,
  "phone_number": null,
  "email": null,
  "gender": "female",
  "blood_type": null,
  "allergy_history": null
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `category_id` | integer, ID kategori dalam tenant | yes |
| `name` | string, maksimal 255 karakter | yes |
| `conversation_id` | string ID percakapan tenant atau `null`; default `null` | no |
| `satu_sehat_id` | string atau `null` | no |
| `birth_date` | tanggal `YYYY-MM-DD` atau `null` | no |
| `birth_place` | string atau `null` | no |
| `national_id` | string atau `null` | no |
| `bpjs_number` | string atau `null` | no |
| `address` | string atau `null` | no |
| `phone_number` | string atau `null` | no |
| `email` | alamat email atau `null` | no |
| `gender` | `male`, `female`, atau `null` | no |
| `blood_type` | `A`, `B`, `AB`, `O`, atau `null` | no |
| `allergy_history` | string atau `null` | no |

**Response** — `201 CREATED`

```json
{
  "success": true,
  "code": 201,
  "status": "CREATED",
  "message": "patient created successfully",
  "data": {
    "id": "pR8vK2nT5xQaL7mZ0cYhJ",
    "tenant_id": "8yuPA4qUjqC3OfizucQoH",
    "category_id": 1,
    "conversation_id": "fF4vJ2lA8sTrN0qLmP5xB",
    "name": "Siti Aminah",
    "satu_sehat_id": null,
    "birth_date": "1995-04-12",
    "birth_place": "Bandung",
    "national_id": null,
    "bpjs_number": null,
    "address": null,
    "phone_number": null,
    "email": null,
    "gender": "female",
    "blood_type": null,
    "allergy_history": null,
    "created_at": "2026-10-15T09:00:00+00:00",
    "updated_at": "2026-10-15T09:00:00+00:00"
  }
}
```

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | field wajib hilang atau format salah |
| 400 | `BAD_REQUEST` | `tenant_id is required` | tenant kosong |
| 400 | `BAD_REQUEST` | `name is required` | nama kosong |
| 400 | `BAD_REQUEST` | `name exceeds 255 characters` | nama terlalu panjang |
| 400 | `BAD_REQUEST` | `conversation_id is required` | ID percakapan berupa string kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT tidak sah |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak memiliki akses tenant |
| 404 | `NOT_FOUND` | `patient category not found` | kategori tidak ada di tenant |
| 404 | `NOT_FOUND` | `conversation not found` | percakapan tidak ada di tenant |
| 409 | `CONFLICT` | `conversation is already connected to another patient` | percakapan sudah dipakai pasien lain |

## `POST /api/v1/patients/details`

Mengambil satu pasien berdasarkan ID dan tenant.

**Method:** `POST`

**Authorization:** `Bearer <jwt>`; pengguna dengan akses tenant.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "id": "pR8vK2nT5xQaL7mZ0cYhJ"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `id` | string nanoid | yes |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "patient retrieved successfully",
  "data": {
    "id": "pR8vK2nT5xQaL7mZ0cYhJ",
    "tenant_id": "8yuPA4qUjqC3OfizucQoH",
    "category_id": 1,
    "conversation_id": null,
    "name": "Siti Aminah",
    "satu_sehat_id": null,
    "birth_date": "1995-04-12",
    "birth_place": "Bandung",
    "national_id": null,
    "bpjs_number": null,
    "address": null,
    "phone_number": null,
    "email": null,
    "gender": "female",
    "blood_type": null,
    "allergy_history": null,
    "created_at": "2026-10-15T09:00:00+00:00",
    "updated_at": "2026-10-15T09:00:00+00:00"
  }
}
```

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | ID salah |
| 400 | `BAD_REQUEST` | `tenant_id is required` | tenant kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT tidak sah |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak memiliki akses tenant |
| 404 | `NOT_FOUND` | `patient not found` | pasien tidak ada di tenant |

## `POST /api/v1/patients/update`

Memperbarui field pasien yang dikirim; `null` mengosongkan field opsional.

**Method:** `POST`

**Authorization:** `Bearer <jwt>`; pengguna dengan akses tenant.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "id": "pR8vK2nT5xQaL7mZ0cYhJ",
  "name": "Siti A."
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `id` | string nanoid | yes |
| `category_id` | integer kategori tenant | no |
| `name` | string, maksimal 255 karakter | no |
| `satu_sehat_id` | string atau `null` | no |
| `birth_date` | tanggal `YYYY-MM-DD` atau `null` | no |
| `birth_place` | string atau `null` | no |
| `national_id` | string atau `null` | no |
| `bpjs_number` | string atau `null` | no |
| `address` | string atau `null` | no |
| `phone_number` | string atau `null` | no |
| `email` | alamat email atau `null` | no |
| `gender` | `male`, `female`, atau `null` | no |
| `blood_type` | `A`, `B`, `AB`, `O`, atau `null` | no |
| `allergy_history` | string atau `null` | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "patient updated successfully",
  "data": {
    "id": "pR8vK2nT5xQaL7mZ0cYhJ",
    "tenant_id": "8yuPA4qUjqC3OfizucQoH",
    "category_id": 1,
    "conversation_id": null,
    "name": "Siti A.",
    "satu_sehat_id": null,
    "birth_date": "1995-04-12",
    "birth_place": "Bandung",
    "national_id": null,
    "bpjs_number": null,
    "address": null,
    "phone_number": null,
    "email": null,
    "gender": "female",
    "blood_type": null,
    "allergy_history": null,
    "created_at": "2026-10-15T09:00:00+00:00",
    "updated_at": "2026-10-15T09:05:00+00:00"
  }
}
```

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | format field salah |
| 400 | `BAD_REQUEST` | `tenant_id is required` | tenant kosong |
| 400 | `BAD_REQUEST` | `at least one field is required` | tidak ada field perubahan |
| 400 | `BAD_REQUEST` | `name is required` | nama kosong |
| 400 | `BAD_REQUEST` | `name exceeds 255 characters` | nama terlalu panjang |
| 400 | `BAD_REQUEST` | `category_id is required` | kategori diberi `null` |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT tidak sah |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak memiliki akses tenant |
| 404 | `NOT_FOUND` | `patient not found` | pasien tidak ada di tenant |
| 404 | `NOT_FOUND` | `patient category not found` | kategori tidak ada di tenant |

## `POST /api/v1/patients/delete`

Menghapus pasien; percakapan WhatsApp tetap tersimpan dan tautannya lepas.

**Method:** `POST`

**Authorization:** `Bearer <jwt>`; pengguna dengan akses tenant.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "id": "pR8vK2nT5xQaL7mZ0cYhJ"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `id` | string nanoid | yes |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "patient deleted successfully",
  "data": {
    "id": "pR8vK2nT5xQaL7mZ0cYhJ"
  }
}
```

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | ID salah |
| 400 | `BAD_REQUEST` | `tenant_id is required` | tenant kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT tidak sah |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak memiliki akses tenant |
| 404 | `NOT_FOUND` | `patient not found` | pasien tidak ada di tenant |

## `POST /api/v1/patients/connect-conversation`

Menghubungkan percakapan WhatsApp milik tenant ke pasien yang sudah ada; kirim `null` untuk melepasnya.

**Method:** `POST`

**Authorization:** `Bearer <jwt>`; pengguna dengan akses tenant.

**Request**

```json
{
  "tenant_id": "8yuPA4qUjqC3OfizucQoH",
  "id": "pR8vK2nT5xQaL7mZ0cYhJ",
  "conversation_id": "fF4vJ2lA8sTrN0qLmP5xB"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `id` | string nanoid pasien | yes |
| `conversation_id` | string ID percakapan atau `null` | yes |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "patient conversation updated successfully",
  "data": {
    "id": "pR8vK2nT5xQaL7mZ0cYhJ",
    "tenant_id": "8yuPA4qUjqC3OfizucQoH",
    "category_id": 1,
    "conversation_id": "fF4vJ2lA8sTrN0qLmP5xB",
    "name": "Siti A.",
    "satu_sehat_id": null,
    "birth_date": "1995-04-12",
    "birth_place": "Bandung",
    "national_id": null,
    "bpjs_number": null,
    "address": null,
    "phone_number": null,
    "email": null,
    "gender": "female",
    "blood_type": null,
    "allergy_history": null,
    "created_at": "2026-10-15T09:00:00+00:00",
    "updated_at": "2026-10-15T09:10:00+00:00"
  }
}
```

| Code | Status | Message | When |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | field wajib hilang atau tipe salah |
| 400 | `BAD_REQUEST` | `tenant_id is required` | tenant kosong |
| 400 | `BAD_REQUEST` | `conversation_id is required` | ID percakapan string kosong |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT tidak sah |
| 403 | `FORBIDDEN` | `tenant access denied` | pengguna tidak memiliki akses tenant |
| 404 | `NOT_FOUND` | `patient not found` | pasien tidak ada di tenant |
| 404 | `NOT_FOUND` | `conversation not found` | percakapan tidak ada di tenant |
| 409 | `CONFLICT` | `conversation is already connected to another patient` | percakapan sudah dipakai pasien lain |
