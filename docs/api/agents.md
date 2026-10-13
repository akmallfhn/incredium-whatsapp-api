# Agents

Endpoint ini mengelola agent balasan WhatsApp, sumber pengetahuan, dan pilihan agent aktif per tenant. Katalog provider dan model ada di [dokumentasi LLM](llm.md) dengan endpoint `/api/v1/llm`. Semua operasi memakai `POST` dengan JSON body dan JWT dari `auth/login`. Pengguna harus punya akses tenant untuk membaca atau mengubah agent; perubahan memerlukan peran `Administrator` atau `Super Admin`. Endpoint daftar memakai `page` default `1` dan `page_size` default `20` dengan batas `100`. `tenants.active_agent_id` adalah sumber kebenaran pilihan agent: `null` mematikan balasan AI tenant, sedangkan `is_active` pada respons agent adalah penanda turunan dari nilai tersebut. Agent baru dapat dibuat hanya dengan nama dan tenant; `model_id`, `system_prompt`, `transfer_conditions`, dan `personality` awalnya `null`.

## Daftar agent

Mengembalikan agent milik tenant, termasuk penanda agent yang sedang dipilih.

**Method:** `POST /api/v1/agents/list`  
**Authorization:** Bearer JWT, akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `page` | integer | no |
| `page_size` | integer | no |

**Response:** `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "agents retrieved successfully",
  "data": {
    "list": [
      {
        "id": "agent-id",
        "tenant_id": "tenant-id",
        "model_id": 2,
        "model": {
          "id": 2,
          "provider_id": 1,
          "provider_name": "ChatGPT",
          "api_provider": "openai",
          "provider_image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_gpt.svg",
          "api_model": "gpt-4.1",
          "display_name": "GPT-4.1",
          "created_at": "2026-10-12T00:00:00+00:00",
          "updated_at": "2026-10-12T00:00:00+00:00"
        },
        "name": "Asisten Incredium",
        "personality": "Saya Nara, berpengalaman menangani pertanyaan produk dan berbicara dengan ramah.",
        "system_prompt": "Bantu pelanggan dengan sopan.",
        "transfer_conditions": "Alihkan jika meminta staf.",
        "config_version": 1,
        "is_active": true,
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
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 404 | NOT_FOUND | `tenant not found` | Tenant tidak ada |

## Detail agent

Mengembalikan satu konfigurasi agent milik tenant.

**Method:** `POST /api/v1/agents/details`  
**Authorization:** Bearer JWT, akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "id": "agent-id"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `id` | string | yes |

**Response:** `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "agent retrieved successfully",
  "data": {
    "id": "agent-id",
    "tenant_id": "tenant-id",
    "model_id": 2,
    "model": {
      "id": 2,
      "provider_id": 1,
      "provider_name": "ChatGPT",
      "api_provider": "openai",
      "provider_image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_gpt.svg",
      "api_model": "gpt-4.1",
      "display_name": "GPT-4.1",
      "created_at": "2026-10-12T00:00:00+00:00",
      "updated_at": "2026-10-12T00:00:00+00:00"
    },
    "name": "Asisten Incredium",
    "personality": "Saya Nara, berpengalaman menangani pertanyaan produk dan berbicara dengan ramah.",
    "system_prompt": "Bantu pelanggan dengan sopan.",
    "transfer_conditions": "Alihkan jika meminta staf.",
    "config_version": 1,
    "is_active": true,
    "created_at": "2026-10-12T00:00:00+00:00",
    "updated_at": "2026-10-12T00:00:00+00:00"
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `id is required` | ID agent atau sumber kosong |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 404 | NOT_FOUND | `agent not found` | Agent tidak ada pada tenant |

## Buat agent

Membuat draf agent dengan nama dan tenant tanpa langsung memilihnya sebagai agent aktif.

**Method:** `POST /api/v1/agents/create`  
**Authorization:** Bearer JWT, `Administrator` atau `Super Admin` dengan akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "name": "Asisten Incredium"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `name` | string | yes |

Tambahkan model, prompt, dan kondisi transfer melalui endpoint `update` sebelum memilih agent aktif.

**Response:** `201 CREATED`

```json
{
  "success": true,
  "code": 201,
  "status": "CREATED",
  "message": "agent created successfully",
  "data": {
    "id": "agent-id",
    "tenant_id": "tenant-id",
    "model_id": null,
    "model": null,
    "name": "Asisten Incredium",
    "personality": null,
    "system_prompt": null,
    "transfer_conditions": null,
    "config_version": 1,
    "is_active": false,
    "created_at": "2026-10-12T00:00:00+00:00",
    "updated_at": "2026-10-12T00:00:00+00:00"
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `name is required` | Nama kosong |
| 400 | BAD_REQUEST | `name exceeds 100 characters` | Nama terlalu panjang |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 403 | FORBIDDEN | `agent management denied` | Peran tidak boleh mengubah agent atau knowledge |

## Ubah agent

Memperbarui konfigurasi, termasuk kepribadian dan latar agent, serta menaikkan `config_version` agar cache lama tidak dipakai.

**Method:** `POST /api/v1/agents/update`  
**Authorization:** Bearer JWT, `Administrator` atau `Super Admin` dengan akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "id": "agent-id",
  "name": "Asisten Baru",
  "model_id": 2,
  "personality": "Saya Nara, berpengalaman menangani pertanyaan produk dan berbicara dengan ramah.",
  "system_prompt": "Bantu pelanggan dengan sopan.",
  "transfer_conditions": "Alihkan jika meminta staf."
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `id` | string | yes |
| `model_id` | integer atau `null` | no |
| `name` | string | no |
| `personality` | string atau `null` | no |
| `system_prompt` | string atau `null` | no |
| `transfer_conditions` | string atau `null` | no |

`model_id`, `system_prompt`, dan `transfer_conditions` boleh `null` pada agent yang belum aktif. Teks kosong dinormalisasi menjadi `null`. Jika agent sedang aktif, hasil perubahan wajib tetap memiliki model, prompt, dan kondisi transfer yang tidak kosong. `personality` tetap opsional dan dapat berisi identitas, pengalaman, serta gaya bicara agent. Nama dari field `name` dan isi `personality` masuk ke konteks LangGraph.

**Response:** `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "agent updated successfully",
  "data": {
    "id": "agent-id",
    "tenant_id": "tenant-id",
    "model_id": 2,
    "model": {
      "id": 2,
      "provider_id": 1,
      "provider_name": "ChatGPT",
      "api_provider": "openai",
      "provider_image_url": "https://zxsbslyyzdpkqwwelgzp.supabase.co/storage/v1/object/public/pureva/llm/provider/icon_gpt.svg",
      "api_model": "gpt-4.1",
      "display_name": "GPT-4.1",
      "created_at": "2026-10-12T00:00:00+00:00",
      "updated_at": "2026-10-12T00:00:00+00:00"
    },
    "name": "Asisten Baru",
    "personality": "Saya Nara, berpengalaman menangani pertanyaan produk dan berbicara dengan ramah.",
    "system_prompt": "Bantu pelanggan dengan sopan.",
    "transfer_conditions": "Alihkan jika meminta staf.",
    "config_version": 2,
    "is_active": true,
    "created_at": "2026-10-12T00:00:00+00:00",
    "updated_at": "2026-10-12T00:00:00+00:00"
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `id is required` | ID agent atau sumber kosong |
| 400 | BAD_REQUEST | `no fields to update` | Tidak ada field perubahan |
| 400 | BAD_REQUEST | `name cannot be null` | Nama dikirim bernilai `null` |
| 400 | BAD_REQUEST | `name is required` | Nama kosong |
| 400 | BAD_REQUEST | `<field> is required for active agent` | Agent aktif menjadi tidak lengkap |
| 400 | BAD_REQUEST | `model provider is not supported` | Integrasi provider model belum tersedia di worker |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 403 | FORBIDDEN | `agent management denied` | Peran tidak boleh mengubah agent atau knowledge |
| 404 | NOT_FOUND | `agent not found` | Agent tidak ada pada tenant |
| 404 | NOT_FOUND | `model not found` | ID model tidak ada di katalog |

## Hapus agent

Mengosongkan pilihan aktif bila perlu, melepas referensi chat, lalu menghapus knowledge dan agent dalam satu transaksi.

**Method:** `POST /api/v1/agents/delete`  
**Authorization:** Bearer JWT, `Administrator` atau `Super Admin` dengan akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "id": "agent-id"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `id` | string | yes |

Jika agent yang dihapus bukan agent aktif, `active_agent_id` pada respons tetap berisi ID agent aktif saat itu.

**Response:** `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "agent deleted successfully",
  "data": {
    "id": "agent-id",
    "tenant_id": "tenant-id",
    "active_agent_id": null
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `id is required` | ID agent atau sumber kosong |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 403 | FORBIDDEN | `agent management denied` | Peran tidak boleh mengubah agent atau knowledge |
| 404 | NOT_FOUND | `agent not found` | Agent tidak ada pada tenant |

## Pilih agent aktif

Memilih satu agent milik tenant atau mengirim `null` untuk mematikan balasan AI tenant.

**Method:** `POST /api/v1/agents/select-active`  
**Authorization:** Bearer JWT, `Administrator` atau `Super Admin` dengan akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "agent_id": "agent-id"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `agent_id` | string atau `null` | yes |

Field `agent_id` wajib dikirim. Nilai `null` menonaktifkan balasan AI untuk tenant. Agent yang dipilih wajib memiliki `model_id`, `system_prompt`, dan `transfer_conditions` yang tidak kosong; memilih agent tidak mengubah mode `human` pada percakapan yang sudah diambil alih staf.

**Response:** `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "active agent updated successfully",
  "data": {
    "tenant_id": "tenant-id",
    "active_agent_id": "agent-id"
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `<field> is required for active agent` | Model, prompt, atau kondisi transfer belum lengkap |
| 400 | BAD_REQUEST | `model provider is not supported` | Integrasi provider model belum tersedia di worker |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 403 | FORBIDDEN | `agent management denied` | Peran tidak boleh mengubah agent atau knowledge |
| 404 | NOT_FOUND | `tenant not found` | Tenant tidak ada |
| 404 | NOT_FOUND | `agent not found` | Agent tidak ada pada tenant |

## Daftar knowledge source

Mengembalikan sumber pengetahuan milik satu agent secara berpaginasi.

**Method:** `POST /api/v1/agents/knowledge/list`  
**Authorization:** Bearer JWT, akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "agent_id": "agent-id",
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `agent_id` | string | yes |
| `page` | integer | no |
| `page_size` | integer | no |

**Response:** `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "knowledge sources retrieved successfully",
  "data": {
    "list": [
      {
        "id": "source-id",
        "agent_id": "agent-id",
        "title": "FAQ",
        "kind": "text",
        "source_uri": null,
        "content": "Jam operasional 09.00-17.00.",
        "status": "active",
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
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `id is required` | ID agent atau sumber kosong |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 404 | NOT_FOUND | `agent not found` | Agent tidak ada pada tenant |

## Detail knowledge source

Mengembalikan satu sumber pengetahuan dari agent yang ditentukan.

**Method:** `POST /api/v1/agents/knowledge/details`  
**Authorization:** Bearer JWT, akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "agent_id": "agent-id",
  "id": "source-id"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `agent_id` | string | yes |
| `id` | string | yes |

**Response:** `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "knowledge source retrieved successfully",
  "data": {
    "id": "source-id",
    "agent_id": "agent-id",
    "title": "FAQ",
    "kind": "text",
    "source_uri": null,
    "content": "Jam operasional 09.00-17.00.",
    "status": "active",
    "created_at": "2026-10-12T00:00:00+00:00",
    "updated_at": "2026-10-12T00:00:00+00:00"
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `id is required` | ID agent atau sumber kosong |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 404 | NOT_FOUND | `agent not found` | Agent tidak ada pada tenant |
| 404 | NOT_FOUND | `knowledge source not found` | Sumber tidak ada pada agent |

## Buat knowledge source

Menyimpan teks atau hasil ekstraksi URL/file; pengambilan URL dan upload file belum dijalankan oleh endpoint ini.

**Method:** `POST /api/v1/agents/knowledge/create`  
**Authorization:** Bearer JWT, `Administrator` atau `Super Admin` dengan akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "agent_id": "agent-id",
  "title": "FAQ",
  "kind": "text",
  "source_uri": null,
  "content": "Jam operasional 09.00-17.00.",
  "status": "active"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `agent_id` | string | yes |
| `title` | string | yes |
| `kind` | `text`, `url`, atau `file` | yes |
| `source_uri` | string atau `null` | no; wajib untuk `url`/`file` |
| `content` | string atau `null` | no; wajib jika `status=active` |
| `status` | `active` atau `inactive` | no |

`status` default `inactive`. Untuk `kind=text`, kirim konten langsung dan kosongkan `source_uri`. Untuk `kind=url` atau `kind=file`, kirim `source_uri` dan hasil ekstraksi dalam `content`; agent hanya membaca sumber dengan `status=active` dan `content` terisi.

**Response:** `201 CREATED`

```json
{
  "success": true,
  "code": 201,
  "status": "CREATED",
  "message": "knowledge source created successfully",
  "data": {
    "id": "source-id",
    "agent_id": "agent-id",
    "title": "FAQ",
    "kind": "text",
    "source_uri": null,
    "content": "Jam operasional 09.00-17.00.",
    "status": "active",
    "created_at": "2026-10-12T00:00:00+00:00",
    "updated_at": "2026-10-12T00:00:00+00:00"
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `id is required` | ID agent atau sumber kosong |
| 400 | BAD_REQUEST | `title is required` | Judul kosong |
| 400 | BAD_REQUEST | `source_uri is required` | Jenis url/file tanpa URI |
| 400 | BAD_REQUEST | `source_uri must be empty for text` | Jenis text diberi URI |
| 400 | BAD_REQUEST | `content is required for active source` | Sumber aktif tanpa konten |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 403 | FORBIDDEN | `agent management denied` | Peran tidak boleh mengubah agent atau knowledge |
| 404 | NOT_FOUND | `agent not found` | Agent tidak ada pada tenant |

## Ubah knowledge source

Memperbarui field yang dikirim dan menaikkan versi konfigurasi agent.

**Method:** `POST /api/v1/agents/knowledge/update`  
**Authorization:** Bearer JWT, `Administrator` atau `Super Admin` dengan akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "agent_id": "agent-id",
  "id": "source-id",
  "content": "Jam operasional 08.00-17.00."
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `agent_id` | string | yes |
| `id` | string | yes |
| `title` | string | no |
| `kind` | `text`, `url`, atau `file` | no |
| `source_uri` | string atau `null` | no |
| `content` | string atau `null` | no |
| `status` | `active` atau `inactive` | no |

**Response:** `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "knowledge source updated successfully",
  "data": {
    "id": "source-id",
    "agent_id": "agent-id",
    "title": "FAQ",
    "kind": "text",
    "source_uri": null,
    "content": "Jam operasional 08.00-17.00.",
    "status": "active",
    "created_at": "2026-10-12T00:00:00+00:00",
    "updated_at": "2026-10-12T00:00:00+00:00"
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `id is required` | ID agent atau sumber kosong |
| 400 | BAD_REQUEST | `no fields to update` | Tidak ada field perubahan |
| 400 | BAD_REQUEST | `<field> cannot be null` | Judul, jenis, atau status dikirim null |
| 400 | BAD_REQUEST | `source_uri is required` | Jenis url/file tanpa URI |
| 400 | BAD_REQUEST | `source_uri must be empty for text` | Jenis text diberi URI |
| 400 | BAD_REQUEST | `content is required for active source` | Sumber aktif tanpa konten |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 403 | FORBIDDEN | `agent management denied` | Peran tidak boleh mengubah agent atau knowledge |
| 404 | NOT_FOUND | `agent not found` | Agent tidak ada pada tenant |
| 404 | NOT_FOUND | `knowledge source not found` | Sumber tidak ada pada agent |

## Hapus knowledge source

Menghapus satu sumber pengetahuan milik agent dalam transaksi.

**Method:** `POST /api/v1/agents/knowledge/delete`  
**Authorization:** Bearer JWT, `Administrator` atau `Super Admin` dengan akses tenant

**Request**

```json
{
  "tenant_id": "tenant-id",
  "agent_id": "agent-id",
  "id": "source-id"
}
```

| Field | Type | Required |
|---|---|---|
| `tenant_id` | string | yes |
| `agent_id` | string | yes |
| `id` | string | yes |

**Response:** `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "knowledge source deleted successfully",
  "data": {
    "id": "source-id",
    "agent_id": "agent-id"
  }
}
```

**Errors**

| Code | Status | Message | Kondisi |
|---|---|---|---|
| 400 | BAD_REQUEST | `invalid request: <field>` | Field wajib hilang atau tipe/nilai tidak sesuai |
| 400 | BAD_REQUEST | `tenant_id is required` | ID tenant kosong atau hanya spasi |
| 400 | BAD_REQUEST | `id is required` | ID agent atau sumber kosong |
| 401 | UNAUTHORIZED | `missing or invalid authorization header` | JWT hilang, tidak sah, kedaluwarsa, atau dicabut |
| 403 | FORBIDDEN | `tenant access denied` | Pengguna tidak punya akses tenant |
| 403 | FORBIDDEN | `agent management denied` | Peran tidak boleh mengubah agent atau knowledge |
| 404 | NOT_FOUND | `agent not found` | Agent tidak ada pada tenant |
| 404 | NOT_FOUND | `knowledge source not found` | Sumber tidak ada pada agent |
