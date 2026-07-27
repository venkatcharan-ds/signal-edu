"""
Evidence Extraction Engine — Stage 2 of the pipeline.

Handles non-GitHub evidence:
- PDF text extraction (PyMuPDF)
- Portfolio URL content fetching (httpx + BeautifulSoup)

Output is raw text + structured metadata fed into CapabilityEngine.
No AI inference in this stage.
"""
import structlog
from dataclasses import dataclass

log = structlog.get_logger()


@dataclass
class ArtifactText:
    artifact_id: str
    type: str          # 'pdf' | 'link'
    title: str | None
    raw_text: str
    word_count: int
    metadata: dict


class EvidenceEngine:
    async def extract_pdf(self, file_bytes: bytes, filename: str) -> ArtifactText:
        """
        Extract text from a PDF using PyMuPDF.
        Detects scanned PDFs (no text layer) and returns empty with a warning flag.
        """
        # TODO: Phase 5
        raise NotImplementedError

    async def extract_url(self, url: str, title: str | None = None) -> ArtifactText:
        """
        Fetch a URL and extract meaningful text via BeautifulSoup.
        Strips navigation, headers, footers.
        """
        # TODO: Phase 5
        raise NotImplementedError
