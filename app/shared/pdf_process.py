"""Jalankan optimasi PDF di proses singkat agar memori gambar segera dilepas."""

import asyncio
import logging
import sys
from contextlib import suppress

logger = logging.getLogger(__name__)
PDF_PROCESS_TIMEOUT_SECONDS = 120


async def shrink_pdf_isolated(content: bytes, ceiling: int) -> bytes:
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "app.shared.pdf_worker",
            str(ceiling),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError:
        logger.exception("pdf: proses optimasi tidak dapat dijalankan")
        return content
    try:
        result, stderr = await asyncio.wait_for(
            process.communicate(content), timeout=PDF_PROCESS_TIMEOUT_SECONDS
        )
    except asyncio.CancelledError:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()
        await process.wait()
        raise
    except TimeoutError:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()
        await process.wait()
        logger.error("pdf: proses optimasi melewati batas %s detik", PDF_PROCESS_TIMEOUT_SECONDS)
        return content
    except Exception:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.kill()
        await process.wait()
        logger.exception("pdf: komunikasi dengan proses optimasi gagal")
        return content

    if process.returncode != 0 or not result:
        logger.error("pdf: proses optimasi gagal: %s", stderr.decode(errors="replace")[:500])
        return content
    return result
