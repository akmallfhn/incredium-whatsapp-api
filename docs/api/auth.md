# Auth

Login email + password untuk dashboard TRC, penerbitan JWT, pemeriksaan sesi, dan logout. Endpoint ini yang menentukan siapa penggunanya dan tenant mana saja yang boleh ia lihat — tapi belum ada endpoint untuk membuat atau mengubah user: baris `users`, `password_hash`, dan `users_access` masih diisi manual lewat SQL.

Ada dua jenis kredensial di API ini dan keduanya tidak saling menggantikan. `CLIENT_SECRET` adalah Bearer token statis milik aplikasi dashboard, dipakai `login` dan seluruh endpoint `stats/*` dan `knowledge/*`. JWT adalah token per pengguna hasil login, dipakai `check-session` dan `logout`. Endpoint `stats/*` dan `knowledge/*` **belum** memakai JWT — scope tenant di sana masih dikirim eksplisit lewat `tenant_id`, dan `tenant_ids` dari login-lah yang dipakai UI untuk menentukan tenant mana yang boleh dipilih.

JWT ditandatangani HS256 dengan `JWT_SECRET` dan berumur `JWT_TTL_DAYS` hari (default 365). Umur sepanjang itu hanya aman kalau token bisa dicabut, jadi tanda tangan yang sah saja tidak cukup: setiap pemakaian JWT dicocokkan ke baris `tokens` yang masih hidup. Logout menghapus baris itu, dan token yang sama langsung ditolak walau belum kedaluwarsa. Mengganti `JWT_SECRET` mematikan semua sesi sekaligus.

Kolom `tokens.token` menyimpan JWT apa adanya, bukan hash-nya. Artinya siapa pun yang bisa membaca tabel `tokens` bisa memakai sesi orang lain sampai sesi itu di-logout atau kedaluwarsa — dan RLS di tabel tersebut masih mati. Perlakukan isi tabel itu seperti daftar password.

Password di-hash bcrypt. Email dicocokkan tanpa memandang huruf besar-kecil, dan user dengan `status = 'inactive'` diperlakukan seperti tidak ada. Email yang tidak terdaftar dan password yang salah menghasilkan balasan yang persis sama — `401 invalid email or password` — supaya daftar email yang terdaftar tidak bisa ditebak dari respons.

Peran ada di `users.role` dengan tiga nilai: `Super Admin`, `Administrator`, `Member`. Peran ikut di dalam JWT dan dikembalikan tiap endpoint di halaman ini, tapi **belum ada endpoint yang membatasi akses berdasarkan peran** — penegakannya untuk sekarang ada di UI.

## Objek `user`

Bentuk yang sama dipakai `login`, `check-session`, dan sebagai sumber data profil di UI.

| Field | Type | Keterangan |
|---|---|---|
| `id` | string (UUID) | id user |
| `full_name` | string | nama tampilan |
| `email` | string | dipakai untuk login |
| `avatar` | string \| null | URL foto, boleh kosong |
| `role` | string | `Super Admin`, `Administrator`, atau `Member` |
| `status` | string | selalu `active` di respons; user `inactive` tidak bisa login |
| `tenant_ids` | string[] | tenant yang boleh diakses, urut waktu pemberian akses. Bisa kosong |

## Endpoints

### `POST {base_url}/api/v1/auth/login`

Menukar email + password dengan JWT. Dijaga `CLIENT_SECRET`, bukan JWT — ini satu-satunya endpoint auth yang bisa dipanggil tanpa sesi.

Setiap login menerbitkan token baru dan **tidak** mematikan token lama, jadi satu user boleh punya beberapa sesi sekaligus (misal laptop dan ponsel). Token yang sudah lewat masa berlakunya dibersihkan dari tabel di tiap login.

**Method:** `POST`

**Authorization:** `Bearer <client_secret>`

**Request**

```json
{
  "email": "akmalluthfiansyah@gmail.com",
  "password": "••••••••"
}
```

| Field | Type | Required |
|---|---|---|
| `email` | string (format email) | yes |
| `password` | string (1–128) | yes |

Domain special-use seperti `.test`, `.local`, dan `.invalid` ditolak validator sebagai `400`, jadi email user tidak bisa memakai domain itu.

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_at": "2027-09-15T09:47:21.553000+00:00",
    "user": {
      "id": "983850b5-2d36-4be7-bd83-c2e7f19892b1",
      "full_name": "Akmal Luthfiansyah",
      "email": "akmalluthfiansyah@gmail.com",
      "avatar": null,
      "role": "Super Admin",
      "status": "active",
      "tenant_ids": ["8yuPA4qUjqC3OfizucQoH"]
    }
  }
}
```

| Code | Message |
|---|---|
| `400` | `invalid request: email` |
| `401` | `missing or invalid authorization header` — `CLIENT_SECRET` salah atau tidak dikirim |
| `401` | `invalid email or password` — email tidak terdaftar, password salah, atau user nonaktif |
| `500` | `an unexpected error occurred` — `JWT_SECRET` kosong di server |

### `GET {base_url}/api/v1/auth/check-session`

Memastikan JWT masih berlaku dan mengembalikan profil pemiliknya. Dipakai saat halaman dimuat ulang, untuk memutuskan menampilkan dashboard atau melempar ke halaman login.

Datanya dibaca ulang dari database tiap panggilan, bukan dari isi JWT — jadi perubahan peran, avatar, atau akses tenant langsung terbaca tanpa perlu login ulang. Sebaliknya, user yang dinonaktifkan langsung kehilangan sesinya.

**Method:** `GET`

**Authorization:** `Bearer <jwt>`

**Request** — tanpa body.

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "session is valid",
  "data": {
    "id": "983850b5-2d36-4be7-bd83-c2e7f19892b1",
    "full_name": "Akmal Luthfiansyah",
    "email": "akmalluthfiansyah@gmail.com",
    "avatar": null,
    "role": "Super Admin",
    "status": "active",
    "tenant_ids": ["8yuPA4qUjqC3OfizucQoH"]
  }
}
```

| Code | Message |
|---|---|
| `401` | `missing or invalid authorization header` — header kosong, bukan `Bearer`, tanda tangan salah, token kedaluwarsa, sudah di-logout, atau usernya nonaktif |
| `500` | `an unexpected error occurred` — `JWT_SECRET` kosong di server |

`401` sengaja tidak membedakan sebab-sebab di atas. Perlakukan semuanya sama: hapus token di sisi klien dan kembalikan pengguna ke halaman login.

### `POST {base_url}/api/v1/auth/logout`

Mencabut JWT yang sedang dipakai dengan menghapus barisnya di `tokens`. Hanya sesi yang tokennya dikirim yang dicabut — sesi lain milik user yang sama tetap hidup.

Logout memvalidasi tokennya lebih dulu, jadi token yang sudah dicabut atau palsu dibalas `401`, bukan `200`. Klien boleh memperlakukan `401` di sini sebagai sukses: hasil akhirnya sama-sama tidak ada sesi.

**Method:** `POST`

**Authorization:** `Bearer <jwt>`

**Request** — tanpa body.

**Response** — `200 OK`

```json
{
  "success": true,
  "code": 200,
  "status": "OK",
  "message": "logout successful",
  "data": {
    "id": "983850b5-2d36-4be7-bd83-c2e7f19892b1",
    "email": "akmalluthfiansyah@gmail.com"
  }
}
```

| Code | Message |
|---|---|
| `401` | `missing or invalid authorization header` — token tidak dikirim, tidak sah, atau sudah dicabut |
| `500` | `an unexpected error occurred` — `JWT_SECRET` kosong di server |

## Environment

| Variable | Default | Keterangan |
|---|---|---|
| `CLIENT_SECRET` | — | Bearer statis untuk `login`, `stats/*`, dan `knowledge/*` |
| `JWT_SECRET` | kosong | Kunci tanda tangan HS256. Kosong = `login` dan `check-session` balas `500` |
| `JWT_TTL_DAYS` | `365` | Umur token sejak diterbitkan |