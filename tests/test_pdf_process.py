"""Pastikan optimasi di proses terpisah menghasilkan PDF yang tetap valid."""

import asyncio
import io
import unittest
from unittest.mock import patch

import pikepdf
from PIL import Image

from app.shared.pdf_process import shrink_pdf_isolated


class PdfProcessTest(unittest.IsolatedAsyncioTestCase):
    async def test_valid_pdf_remains_readable(self) -> None:
        original = io.BytesIO()
        Image.new("RGB", (600, 600), "red").save(original, format="PDF")

        result = await shrink_pdf_isolated(original.getvalue(), 45 * 1024 * 1024)

        with pikepdf.open(io.BytesIO(result)) as pdf:
            self.assertEqual(len(pdf.pages), 1)

    async def test_invalid_pdf_falls_back_to_original(self) -> None:
        original = b"not a pdf"

        result = await shrink_pdf_isolated(original, 45 * 1024 * 1024)

        self.assertEqual(result, original)

    async def test_stuck_worker_is_killed_and_original_is_returned(self) -> None:
        class StuckProcess:
            returncode = None

            async def communicate(self, content: bytes) -> None:
                await asyncio.sleep(10)

            def kill(self) -> None:
                self.returncode = -9

            async def wait(self) -> int:
                return self.returncode

        process = StuckProcess()
        with (
            patch("app.shared.pdf_process.asyncio.create_subprocess_exec", return_value=process),
            patch("app.shared.pdf_process.PDF_PROCESS_TIMEOUT_SECONDS", 0.001),
        ):
            result = await shrink_pdf_isolated(b"original", 45 * 1024 * 1024)

        self.assertEqual(result, b"original")
        self.assertEqual(process.returncode, -9)
