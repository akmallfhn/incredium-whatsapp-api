"""Gerbang SQL read-only agent Knowledge; lapis pertama, transaksi READ ONLY pagar terakhirnya."""

import re

# Hanya tabel percakapan WhatsApp. tenants sengaja tidak ikut: isinya tenant lain juga.
ALLOWED_TABLES = frozenset({"wa_conversations", "wa_chats"})

MAX_SQL_ROWS = 200
STATEMENT_TIMEOUT_MS = 10_000

# Nama CTE menang atas tabel dasar, jadi FROM wa_conversations mustahil lihat tenant lain.
_SCOPE_CTE = """
    wa_conversations AS (
        SELECT * FROM public.wa_conversations
        WHERE tenant_id = :tenant_id AND NOT is_internal
    ),
    wa_chats AS (
        SELECT c.* FROM public.wa_chats c
        JOIN public.wa_conversations v ON v.id = c.conv_id
        WHERE v.tenant_id = :tenant_id AND NOT v.is_internal
    )
"""

# Kata kunci yang tidak punya alasan muncul di SELECT dan jadi jalur eskalasi kalau muncul.
_FORBIDDEN = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|create|truncate|grant|revoke|comment|"
    r"copy|vacuum|analyze|reindex|cluster|refresh|merge|call|do|execute|prepare|"
    r"lock|set|reset|begin|start|commit|rollback|savepoint|listen|notify|discard|"
    r"pg_sleep|pg_read_file|pg_read_binary_file|pg_ls_dir|pg_stat_file|"
    r"lo_import|lo_export|dblink|pg_terminate_backend|pg_cancel_backend|"
    r"current_setting|set_config|pg_authid|pg_shadow|pg_user_mapping"
    r")\b",
    re.IGNORECASE,
)

_CTE_NAMES = re.compile(r"(?:\bwith\b|,)\s*([a-z_][a-z0-9_$]*)\s+as\s*(?:materialized\s*)?\(", re.I)
_SOURCES = re.compile(r"\b(?:from|join)\s+((?:[a-z_][a-z0-9_$]*\.)?[a-z_][a-z0-9_$]*)", re.I)
_COMMENT = re.compile(r"--|/\*")


class SqlRejected(Exception):
    """Query ditolak sebelum menyentuh database; pesannya dibalikkan ke agent apa adanya."""


def sanitize(sql: str) -> str:
    """Bungkus SQL agent dengan scope tenant dan batas baris, atau lempar SqlRejected."""
    cleaned = (sql or "").strip().rstrip(";").strip()
    if not cleaned:
        raise SqlRejected("sql kosong")

    if ";" in cleaned:
        raise SqlRejected("hanya boleh satu pernyataan; hapus tanda titik koma di tengah query")

    if _COMMENT.search(cleaned):
        raise SqlRejected("komentar SQL (-- atau /*) tidak diizinkan; tulis query tanpa komentar")

    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise SqlRejected("query harus diawali SELECT atau WITH")

    forbidden = _FORBIDDEN.search(cleaned)
    if forbidden:
        raise SqlRejected(
            f"kata kunci '{forbidden.group(1)}' tidak diizinkan; tool ini hanya untuk membaca"
        )

    refs = _SOURCES.findall(cleaned)
    qualified = sorted({r for r in refs if "." in r})
    if qualified:
        # public.wa_conversations melangkahi CTE scope dan membuka data tenant lain.
        raise SqlRejected(
            f"nama tabel berskema {qualified} tidak diizinkan; tulis nama tabelnya saja"
        )

    cte = {m.lower() for m in _CTE_NAMES.findall(cleaned)}
    clash = sorted(cte & ALLOWED_TABLES)
    if clash:
        raise SqlRejected(f"nama CTE {clash} bentrok dengan nama tabel; pakai nama lain")

    unknown = sorted({r.lower() for r in refs} - cte - ALLOWED_TABLES)
    if unknown:
        raise SqlRejected(
            f"tabel {unknown} tidak boleh dibaca; yang tersedia: {sorted(ALLOWED_TABLES)}"
        )

    # Subquery sekaligus jadi pagar: titik koma sisipan bikin sintaksnya gagal, bukan jalan.
    return (
        f"WITH {_SCOPE_CTE.strip()}\nSELECT * FROM (\n{cleaned}\n) AS agent_query LIMIT :max_rows"
    )
