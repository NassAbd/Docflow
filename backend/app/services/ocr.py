"""Service OCR : conversion PDF → texte via pypdf (fallback) ou Tesseract."""
import logging
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class OcrResult:
    def __init__(self, text: str, page_count: int):
        self.text = text
        self.page_count = page_count

    def __bool__(self) -> bool:
        return bool(self.text.strip())


def extract_text_from_pdf_path(pdf_path: Path, lang: str = "fra") -> OcrResult:
    """
    Extrait le texte d'un fichier PDF.
    Utilise pypdf en priorité car Tesseract/Poppler ne sont pas installés sur l'hôte.
    """
    try:
        reader = PdfReader(str(pdf_path))
        pages_text = []
        for page in reader.pages:
            pages_text.append(page.extract_text() or "")
        
        full_text = "\n\n".join(pages_text)
        return OcrResult(text=full_text, page_count=len(reader.pages))
    except Exception as exc:
        logger.error("Erreur lors de l'extraction de texte PDF : %s", exc)
        return OcrResult(text="", page_count=0)


def extract_text_from_bytes(pdf_bytes: bytes, lang: str = "fra") -> OcrResult:
    """Extrait le texte d'un PDF en mémoire (bytes) via pypdf."""
    # Temporaire : on pourrait utiliser io.BytesIO avec pypdf
    import io
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for page in reader.pages:
            pages_text.append(page.extract_text() or "")
        
        full_text = "\n\n".join(pages_text)
        return OcrResult(text=full_text, page_count=len(reader.pages))
    except Exception as exc:
        logger.error("Erreur lors de l'extraction de texte PDF : %s", exc)
        return OcrResult(text="", page_count=0)
