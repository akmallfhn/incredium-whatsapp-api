# Katalog LLM

Endpoint ini menampilkan provider dan model yang dapat dipilih agent. Semua endpoint memakai `POST` dengan JSON body dan JWT dari `auth/login`. Semua pengguna yang login dapat membaca katalog; hanya `Super Admin` yang dapat mengubahnya. `api_provider` adalah kunci integrasi LLM, `display_name` adalah nama yang ditampilkan kepada pengguna, dan `api_model` adalah ID model yang dikirim ke API provider. Daftar memakai `page` default `1` dan `page_size` default `20` dengan batas `100`.

## `POST /api/v1/llm/providers`

Mengembalikan daftar provider LLM beserta URL gambarnya.

**Method:** `POST`

**Authorization:** Bearer JWT.

**Request**

```json
{
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Required |
|---|---|---|
| `page` | integer | no |
| `page_size` | integer | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "providers retrieved successfully",
  "data": {
    "list": [
      {
        "id": 1,
        "api_provider": "openai",
        "display_name": "ChatGPT",
        "image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_gpt.svg",
        "created_at": "2026-10-13T00:00:00+00:00",
        "updated_at": "2026-10-13T00:00:00+00:00"
      },
      {
        "id": 7,
        "api_provider": "anthropic",
        "display_name": "Claude",
        "image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_claude.svg",
        "created_at": "2026-10-13T00:00:00+00:00",
        "updated_at": "2026-10-13T00:00:00+00:00"
      },
      {
        "id": 3,
        "api_provider": "deepseek",
        "display_name": "DeepSeek",
        "image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_deepseek.svg",
        "created_at": "2026-10-13T00:00:00+00:00",
        "updated_at": "2026-10-13T00:00:00+00:00"
      },
      {
        "id": 9,
        "api_provider": "google_genai",
        "display_name": "Gemini",
        "image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_gemini.svg",
        "created_at": "2026-10-13T00:00:00+00:00",
        "updated_at": "2026-10-13T00:00:00+00:00"
      },
      {
        "id": 8,
        "api_provider": "moonshot",
        "display_name": "Kimi",
        "image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_kimi.svg",
        "created_at": "2026-10-13T00:00:00+00:00",
        "updated_at": "2026-10-13T00:00:00+00:00"
      }
    ],
    "metapaging": {
      "total_data": 5,
      "total_page": 1,
      "current_page": 1,
      "page_size": 20
    }
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | Nilai pagination tidak sesuai |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |

## `POST /api/v1/llm/providers/create`

Menambahkan provider baru ke katalog tanpa mengubah agent yang sudah ada.

**Method:** `POST`

**Authorization:** Bearer JWT, `Super Admin`.

**Request**

```json
{
  "api_provider": "custom",
  "display_name": "Custom AI",
  "image_url": "https://example.com/custom.png"
}
```

| Field | Type | Required |
|---|---|---|
| `api_provider` | string, maksimal 20 karakter | yes |
| `display_name` | string, maksimal 100 karakter | yes |
| `image_url` | URL HTTP/HTTPS atau `null` | no |

**Response** — `201 CREATED`

```json
{
  "success": true,
  "code": 201,
  "status": "CREATED",
  "message": "provider created successfully",
  "data": {
    "id": 2,
    "api_provider": "custom",
    "display_name": "Custom AI",
    "image_url": "https://example.com/custom.png",
    "created_at": "2026-10-13T00:00:00+00:00",
    "updated_at": "2026-10-13T00:00:00+00:00"
  }
}
```

`api_provider` disimpan dengan huruf kecil. `openai`, `deepseek`, `anthropic`, dan `google_genai` mengikuti kunci provider LangChain. Kimi memakai `moonshot` sebagai identitas API karena LangChain belum menyediakan kunci bawaan untuknya. Agent saat ini hanya menjalankan `openai` dan `deepseek`.

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | Field wajib hilang, tipe salah, atau URL tidak valid |
| 400 | `BAD_REQUEST` | `<field> is required` | `api_provider` atau `display_name` kosong |
| 400 | `BAD_REQUEST` | `<field> exceeds <limit> characters` | Nama melampaui batas kolom |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | `FORBIDDEN` | `provider management denied` | Pengguna bukan `Super Admin` |
| 409 | `CONFLICT` | `provider already exists` | `api_provider` sudah dipakai |

## `POST /api/v1/llm/providers/update`

Mengubah nama tampilan atau URL gambar provider yang sudah ada.

**Method:** `POST`

**Authorization:** Bearer JWT, `Super Admin`.

**Request**

```json
{
  "id": 1,
  "display_name": "ChatGPT",
  "image_url": "https://example.com/openai.png"
}
```

| Field | Type | Required |
|---|---|---|
| `id` | integer | yes |
| `display_name` | string, maksimal 100 karakter | no |
| `image_url` | URL HTTP/HTTPS atau `null` | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "provider updated successfully",
  "data": {
    "id": 1,
    "api_provider": "openai",
    "display_name": "ChatGPT",
    "image_url": "https://example.com/openai.png",
    "created_at": "2026-10-13T00:00:00+00:00",
    "updated_at": "2026-10-13T01:00:00+00:00"
  }
}
```

Kirim minimal salah satu dari `display_name` atau `image_url`. Kirim `image_url: null` untuk menghapus gambar. `api_provider` tidak dapat diubah karena dipakai untuk memilih integrasi LLM.

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | ID hilang atau URL tidak valid |
| 400 | `BAD_REQUEST` | `display_name is required` | Nama tampilan kosong atau `null` |
| 400 | `BAD_REQUEST` | `display_name exceeds 100 characters` | Nama tampilan terlalu panjang |
| 400 | `BAD_REQUEST` | `no fields to update` | Tidak ada field perubahan |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | `FORBIDDEN` | `provider management denied` | Pengguna bukan `Super Admin` |
| 404 | `NOT_FOUND` | `provider not found` | ID provider tidak ada |

## `POST /api/v1/llm/models`

Mengembalikan katalog model dengan `provider_id`, `provider_name` (nama tampilan), `api_provider` (kunci integrasi), dan `provider_image_url` langsung pada setiap model.

**Method:** `POST`

**Authorization:** Bearer JWT.

**Request**

```json
{
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Required |
|---|---|---|
| `page` | integer | no |
| `page_size` | integer | no |

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "models retrieved successfully",
  "data": {
    "list": [
      {
        "id": 2,
        "provider_id": 1,
        "provider_name": "ChatGPT",
        "api_provider": "openai",
        "provider_image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_gpt.svg",
        "api_model": "gpt-4.1",
        "display_name": "GPT-4.1",
        "description": null,
        "created_at": "2026-10-12T00:00:00+00:00",
        "updated_at": "2026-10-12T00:00:00+00:00"
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

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | Nilai pagination tidak sesuai |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |

## `POST /api/v1/llm/models/create`

Mendaftarkan ID model yang tersedia di satu provider agar dapat dipilih agent.

**Method:** `POST`

**Authorization:** Bearer JWT, `Super Admin`.

**Request**

```json
{
  "provider_id": 1,
  "api_model": "model-api-id",
  "display_name": "Model Baru",
  "description": "Model cepat untuk balasan singkat."
}
```

| Field | Type | Required |
|---|---|---|
| `provider_id` | integer | yes |
| `api_model` | string, maksimal 100 karakter | yes |
| `display_name` | string, maksimal 100 karakter | yes |
| `description` | string atau `null` | no |

**Response** — `201 CREATED`

```json
{
  "success": true,
  "code": 201,
  "status": "CREATED",
  "message": "model created successfully",
  "data": {
    "id": 3,
    "provider_id": 1,
    "provider_name": "ChatGPT",
    "api_provider": "openai",
    "provider_image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_gpt.svg",
    "api_model": "model-api-id",
    "display_name": "Model Baru",
    "description": "Model cepat untuk balasan singkat.",
    "created_at": "2026-10-13T00:00:00+00:00",
    "updated_at": "2026-10-13T00:00:00+00:00"
  }
}
```

Pasangan `provider_id` dan `api_model` harus unik. `description` kosong disimpan sebagai `null`.

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | `BAD_REQUEST` | `invalid request: <field>` | Field wajib hilang atau tipe salah |
| 400 | `BAD_REQUEST` | `api_model is required` | ID API model kosong |
| 400 | `BAD_REQUEST` | `display_name is required` | Nama tampilan kosong |
| 400 | `BAD_REQUEST` | `<field> exceeds 100 characters` | ID API model atau nama tampilan terlalu panjang |
| 401 | `UNAUTHORIZED` | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | `FORBIDDEN` | `model management denied` | Pengguna bukan `Super Admin` |
| 404 | `NOT_FOUND` | `provider not found` | ID provider tidak ada |
| 409 | `CONFLICT` | `model already exists` | Pasangan provider dan ID API model sudah ada |
