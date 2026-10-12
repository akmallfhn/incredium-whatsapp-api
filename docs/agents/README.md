# Agents

Agent automation Incredium berjalan di pekerja terpisah dari respons webhook Meta. Database menyimpan pekerjaan dan hasilnya agar proses dapat dilanjutkan setelah restart.

| Agent | Pemicu | Yang diubah |
|---|---|---|
| [Balasan WhatsApp](whatsapp-reply-plan.md) | Chat inbound baru, setelah debounce dua detik | `agent_reply_jobs`, `wa_leads.mode`, `wa_chats` outbound |

## Aturan bersama

- Provider dan ID model agent balasan berasal dari `llm_models`; API key tetap dari environment. `app/modules/agents/llm.py` adalah factory bersama.
- Panggilan LLM tidak berjalan sebelum webhook menjawab Meta dan tidak memakai session transaksi webhook.
- Kegagalan node LangGraph dicatat di state atau status job tanpa membatalkan penyimpanan chat.
- Token keluaran dibatasi di kode dan perlu dievaluasi terhadap jawaban WhatsApp terpanjang yang realistis.
- Pemeriksaan akhir dan guard tulis berada di SQL agar konfigurasi, mode, atau generasi job yang berubah tidak menghasilkan balasan usang.
- Semua repository, service, dan pekerja dirakit di [app/server.py](../../app/server.py).
