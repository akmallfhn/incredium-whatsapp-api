"""Perkecil PDF sebelum naik ke Storage; gambar di dalamnya di-resample, strukturnya dipadatkan."""

import io
import logging

import pikepdf
from PIL import Image

logger = logging.getLogger(__name__)

# Dicoba berurutan, berhenti di tingkat pertama yang muat; (sisi terpanjang px, mutu JPEG).
QUALITY_TIERS = ((2200, 80), (1600, 72), (1200, 65))
# Gambar kecil dibiarkan: hasil re-encode-nya sering malah lebih besar dari aslinya.
MIN_IMAGE_PIXELS = 160_000
# Scan bilevel dan JPEG2000 justru membengkak kalau dijadikan JPEG.
SKIP_FILTERS = {"/JBIG2Decode", "/CCITTFaxDecode", "/JPXDecode"}


def _filters(obj: pikepdf.Object) -> set[str]:
    raw = obj.get("/Filter")
    if raw is None:
        return set()
    if isinstance(raw, pikepdf.Array):
        return {str(item) for item in raw}
    return {str(raw)}


def _image_objects(pdf: pikepdf.Pdf) -> list[pikepdf.Object]:
    """Semua XObject gambar, termasuk yang bersarang di Form XObject dan tak terlihat dari page."""
    images: dict[tuple[int, int], pikepdf.Object] = {}
    masks: set[tuple[int, int]] = set()
    for obj in pdf.objects:
        if not isinstance(obj, pikepdf.Stream) or str(obj.get("/Subtype", "")) != "/Image":
            continue
        images[obj.objgen] = obj
        smask = obj.get("/SMask")
        if isinstance(smask, pikepdf.Stream):
            masks.add(smask.objgen)
    # Soft mask dibiarkan utuh: dia kanal alpha milik gambar lain, bukan gambar tersendiri.
    return [obj for objgen, obj in images.items() if objgen not in masks]


def _recompress_image(obj: pikepdf.Object, max_edge: int, quality: int) -> None:
    """Tulis ulang satu XObject gambar sebagai JPEG yang lebih kecil, kalau memang lebih kecil."""
    if _filters(obj) & SKIP_FILTERS:
        return
    # /Mask menunjuk indeks warna di colorspace asli, jadi rusak kalau colorspace-nya diganti.
    if "/Mask" in obj:
        return
    if int(obj.get("/Width", 0)) * int(obj.get("/Height", 0)) < MIN_IMAGE_PIXELS:
        return

    image = pikepdf.PdfImage(obj).as_pil_image()
    if image.mode in ("1", "L"):
        image = image.convert("L")
        colorspace = "/DeviceGray"
    else:
        image = image.convert("RGB")
        colorspace = "/DeviceRGB"

    scale = max_edge / max(image.size)
    if scale < 1:
        target = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        image = image.resize(target, Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    encoded = buffer.getvalue()
    if len(encoded) >= len(obj.read_raw_bytes()):
        return

    obj.write(encoded, filter=pikepdf.Name("/DCTDecode"))
    obj.Width, obj.Height = image.size
    obj.ColorSpace = pikepdf.Name(colorspace)
    obj.BitsPerComponent = 8
    for key in ("/Decode", "/DecodeParms"):
        if key in obj:
            del obj[key]


def _pass(content: bytes, max_edge: int, quality: int) -> bytes:
    with pikepdf.open(io.BytesIO(content)) as pdf:
        for obj in _image_objects(pdf):
            try:
                _recompress_image(obj, max_edge, quality)
            except Exception:
                logger.debug(f"pdf: gambar {obj.objgen} dilewati", exc_info=True)

        buffer = io.BytesIO()
        pdf.save(
            buffer,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )
    return buffer.getvalue()


def shrink_pdf(content: bytes, ceiling: int) -> bytes:
    """Sinkron dan CPU-bound; panggil lewat thread. Selalu mengembalikan PDF yang bisa dipakai."""
    best = content
    for max_edge, quality in QUALITY_TIERS:
        try:
            candidate = _pass(content, max_edge, quality)
        except Exception:
            logger.exception("pdf: optimasi gagal, file asli yang dipakai")
            return best
        if len(candidate) < len(best):
            best = candidate
        # Tingkat berikutnya cuma dipakai kalau yang ini masih kebesaran untuk diupload.
        if len(best) <= ceiling:
            break
    return best
