# Agents

Agent automation yang jalan di atas database Incredium. Semuanya LangGraph, dipicu dari alur yang sudah ada (webhook, endpoint, atau scheduler), dan menulis balik ke Postgres yang sama.

| Agent | Pemicu | Yang diubah |
|---|---|---|
| [Lead Evaluation](lead-evaluation.md) | Webhook WhatsApp: pesan masuk dan echo pesan keluar | `wa_conversations.brand_name`, `project_value`, `lead_status`, `note` |

## Tata letak

```
app/modules/agents/
├── llm.py                  # factory LLM bersama + is_configured()
└── <nama_agent>/
    ├── schema.py           # state graph + skema keluaran LLM
    ├── prompts.py
    ├── repository.py       # baca konteks, tulis hasil
    ├── llm.py              # model, batas token, dan pemanggilan LLM agent ini
    ├── graph.py            # node + wiring StateGraph
    └── service.py          # entry point yang dipanggil dari luar
```

## Aturan bersama

- **Provider utama bisa dipilih**: `LLM_PROVIDER` di `app/core/constants.py` (`openai` atau `deepseek`) menentukan jalur utama, key-nya `OPENAI_API_KEY` atau `DEEPSEEK_API_KEY`, dan `ANTHROPIC_API_KEY` selalu jadi cadangannya. DeepSeek sudah tersambung penuh tapi belum dipakai; menyalakannya harus disengaja, tidak pernah terjadi sendiri. Batas token tetap konstanta di kode karena menempel pada perilaku agent.
- **Call site menyebut tier, bukan nama model.** `build_llm(tier=Tier.FAST)` untuk node yang cuma memilih tool atau mengisi kolom, `Tier.FULL` untuk jawaban yang dibaca orang. Peta tier ke nama model vendor cuma ada di satu tempat, `PROVIDER_MODELS`, jadi ganti provider tidak menyentuh modul agent mana pun.
- **Gagal tanpa menjatuhkan apa pun.** Setiap node menangkap exception-nya sendiri dan menaruh pesannya di `state["error"]`. Agent yang gagal berakhir sebagai baris log, tidak pernah membatalkan alur yang memicunya.
- **Mati kalau tidak dikonfigurasi.** Tanpa satu pun API key, `is_configured()` mengembalikan `False` dan service berhenti di awal.
- **Fallback provider, bukan retry provider yang sama.** `build_llm()` menaruh Anthropic Haiku di belakang OpenAI. Yang dialihkan hanya kegagalan yang tidak akan berubah kalau diulang ke OpenAI lagi — kuota habis, rate limit, key ditolak, OpenAI down. Prompt salah atau schema invalid tetap naik sebagai error, karena provider lain pun akan gagal dengan sebab yang sama.
- **Session database sendiri.** Agent jalan di session terpisah dari alur pemicunya, supaya panggilan LLM tidak menahan koneksi tulis.
- **Batas token diukur, bukan ditebak.** Ukur keluaran terpanjang yang realistis, lalu ambil 3x lipatnya sebagai plafon.
- **Guard tulis ada di SQL, bukan di Python.** Agent bisa jalan berkali-kali secara paralel untuk baris yang sama. Aturan seperti "sekali isi" atau "hanya boleh maju" harus jadi ekspresi di dalam `UPDATE` (`COALESCE`, `GREATEST`, atau klausa `WHERE`) supaya Postgres yang mengurutkan penulisannya. Read-modify-write di Python akan kalah balapan.

## Menambah agent baru

Buat folder di `app/modules/agents/`, pakai `build_llm()` dari `llm.py` bersama, rakit graph-nya, lalu sambungkan factory-nya di [app/server.py](../../app/server.py) — satu-satunya tempat wiring di repo ini.
