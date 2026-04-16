"""
Document processor: extracts text from uploaded PDFs and TXT files,
chunks them for agent processing, and provides a domain-specific
default knowledge base for the viticulture domain.
"""
import os
import io
import logging
from typing import List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))

VITICULTURE_KB = """
VITICULTURE KNOWLEDGE BASE — CLIMATE EFFECTS ON WINE GRAPE QUALITY

Temperature Effects on Anthocyanin Synthesis:
High temperatures are one of the most significant factors affecting anthocyanin accumulation in wine grapes.
Research from Martinez et al. (2020) demonstrated that sustained temperatures above 35°C during ripening
significantly reduce anthocyanin synthesis by up to 45%. The enzyme chalcone synthase, responsible for
anthocyanin production, shows reduced activity at temperatures exceeding 35°C. However, Yamamoto et al. (2019)
reported conflicting findings, suggesting the critical threshold may be as low as 30°C in early ripening
varieties such as Pinot Noir. Anthocyanin degradation accelerates above 42°C causing irreversible quality loss.

Heat Shock Response:
When vine canopy temperatures exceed 38°C, heat shock proteins (HSPs) are upregulated to protect cellular
machinery. This protective response diverts metabolic resources away from secondary metabolite production,
including anthocyanins and tannins. Extended heat periods exceeding 3 days show HSP80 expression 400% above
baseline. Heat shock proteins are essential molecular chaperones but their overexpression competes with
flavonoid biosynthesis pathways.

Water Management and Berry Quality:
Drip irrigation applied during pre-dawn hours (02:00–05:00) achieves 25% higher efficiency compared to
midday irrigation due to reduced evaporation losses. Regulated deficit irrigation (RDI) at 50–70% of full
water requirements during berry development phase concentrates flavonoid compounds. Smith and Jones (2021)
demonstrated that water deficit during véraison increases tannin concentration by 22%, while Chen et al. (2022)
found even greater increases of up to 35% in water-stressed Cabernet Sauvignon — a significant conflict
with prior findings. Drip systems maintain soil moisture at 40–60% field capacity, the optimal range for
berry development. Below 25% field capacity triggers serious water stress.

UV Radiation and Secondary Metabolites:
UV-B radiation (280–315 nm) is a positive regulator of anthocyanin biosynthesis. Clear-sky conditions with
UV index above 8 consistently produce higher anthocyanin accumulation. Shading experiments reducing UV-B by
60% showed a 38% reduction in total phenolic content. UV-B activates the MYB transcription factors that
regulate the anthocyanin biosynthetic pathway.

Canopy Management:
Dense canopy configurations reduce temperature in the fruit zone by 2–4°C compared to open canopy systems.
Leaf removal on the east-facing side of rows allows morning sun exposure while protecting berries from
intense afternoon heat. This microclimate management can raise anthocyanin content by 15–20%.
Canopy management directly influences the vineyard microclimate.

Soil and Nutrition:
Optimal soil moisture for quality wine grape production is 40–60% of field capacity during ripening.
Below 25% field capacity triggers water stress responses that concentrate sugars (Brix increase) and
tannins but may negatively affect overall berry weight. Potassium plays a critical role in regulating
stomatal opening and vine water use efficiency. Soil pH between 5.5 and 7.0 optimises nutrient uptake.

Vine Transpiration and Water Use:
Vine transpiration increases linearly with temperature up to 38°C, where stomatal closure limits further
increases. Transpiration is tightly coupled to photosynthesis; stomatal closure to prevent water loss
also limits CO2 uptake and reduces photosynthetic efficiency. Photosynthesis requires light and CO2 as
essential inputs and is inhibited at temperatures above 40°C. Root systems supply water and nutrients;
their depth and distribution determine drought resilience.

Berry Development Timeline:
Berry development follows three phases: cell division (flowering to fruit set), cell expansion (fruit set
to véraison), and ripening (véraison to harvest). Each phase has specific water and temperature requirements.
Véraison is the transition point when berries begin to soften and accumulate sugars (Brix) and anthocyanins.
The Brix level is a primary indicator of sugar content and determines harvest timing.
"""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """Split text into overlapping chunks for processing."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current += "\n\n" + para if current else para
        else:
            if current:
                chunks.append(current.strip())
            current = para
    if current:
        chunks.append(current.strip())
    # Ensure minimum number of useful chunks
    if not chunks and text.strip():
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - 50)]
    return [c for c in chunks if len(c) > 50]


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from PDF or TXT file bytes."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    elif ext in (".txt", ".md", ".csv"):
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="replace")
    else:
        try:
            return file_bytes.decode("utf-8", errors="replace")
        except Exception:
            return ""


def _extract_pdf(file_bytes: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    pages_text.append(txt)
            return "\n\n".join(pages_text)
    except Exception as e:
        logger.warning("pdfplumber failed (%s), trying PyPDF2", e)
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            return "\n\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception as e2:
            logger.error("PDF extraction failed: %s", e2)
            return ""


def get_default_chunks(domain: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """Return pre-seeded domain knowledge chunks."""
    if domain == "viticulture":
        return chunk_text(VITICULTURE_KB, chunk_size)
    return []


def get_chunk_pairs(chunks: List[str]) -> List[Tuple[str, str]]:
    """Return non-redundant pairs of chunks for conflict detection."""
    pairs = []
    for i in range(len(chunks)):
        for j in range(i + 1, min(i + 3, len(chunks))):
            pairs.append((chunks[i], chunks[j]))
    return pairs
