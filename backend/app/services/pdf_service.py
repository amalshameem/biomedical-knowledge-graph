import os
import re
import tempfile
import logging
from typing import List

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_bytes: bytes, filename: str = "document.pdf", chunk_size: int = 1500, chunk_overlap: int = 200) -> List[str]:
    """
    Extracts markdown text from a PDF file using Docling with aggressive semantic cleaning
    and hierarchical markdown splitting.
    """
    if not file_bytes:
        return []

    markdown_text = ""

    # 1. Primary: IBM Docling using in-memory DocumentStream (no temp files, cross-platform)
    try:
        import io
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import DocumentStream
        from docling.datamodel.document import DocItemLabel

        converter = DocumentConverter()
        stream = DocumentStream(name=filename or "document.pdf", stream=io.BytesIO(file_bytes))
        result = converter.convert(stream)

        allowed_labels = {
            DocItemLabel.TITLE,
            DocItemLabel.SECTION_HEADER,
            DocItemLabel.TEXT,
            DocItemLabel.PARAGRAPH,
            DocItemLabel.LIST_ITEM,
            DocItemLabel.CODE,
            DocItemLabel.FORMULA,
        }

        markdown_text = result.document.export_to_markdown(labels=allowed_labels)
    except Exception as e:
        logger.warning(f"Docling in-memory conversion failed for {filename}: {e}. Falling back to pypdfium2 engine...")
        # 2. Secondary: pypdfium2 fallback (robust on Windows/Mac/Linux with 0 temp file IO)
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(file_bytes)
            pages_text = []
            for page in pdf:
                tp = page.get_textpage()
                txt = tp.get_text_range().strip()
                if txt:
                    pages_text.append(txt)
            pdf.close()
            markdown_text = "\n\n".join(pages_text)
        except Exception as fallback_err:
            logger.error(f"pypdfium2 fallback also failed for {filename}: {fallback_err}", exc_info=True)
            return []

    # If Docling returned empty text, try pypdfium2 extraction
    if not markdown_text or not markdown_text.strip():
        logger.info(f"Docling returned empty text for {filename}; attempting pypdfium2 extraction...")
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(file_bytes)
            pages_text = []
            for page in pdf:
                tp = page.get_textpage()
                txt = tp.get_text_range().strip()
                if txt:
                    pages_text.append(txt)
            pdf.close()
            markdown_text = "\n\n".join(pages_text)
        except Exception:
            pass

    if not markdown_text or not markdown_text.strip():
        logger.error(f"Both Docling and fallback extracted empty text for {filename}")
        return []



    # ---------------------------------------------------------
    # Aggressive Post-Processing
    # ---------------------------------------------------------
    # 0. Standardize Format: UTF-8 encoding, normalize newlines, and remove unicode artifacts
    markdown_text = markdown_text.encode('utf-8', 'ignore').decode('utf-8')
    markdown_text = markdown_text.replace('\r\n', '\n')
    markdown_text = markdown_text.replace('\u200b', '')  # Zero-width space
    markdown_text = markdown_text.replace('\ufffd', '')  # Replacement character
    markdown_text = markdown_text.replace('\xa0', ' ')   # Non-breaking space

    # 1. Promote bolded standalone lines to H3 Headers BEFORE we search for References
    markdown_text = re.sub(r'(?m)^\s*\*\*(.+?)\*\*\s*$', r'### \1', markdown_text)

    # 2. Truncate at References / Bibliography ONLY if it appears in the bottom 40% of the text
    ref_pattern = re.compile(r'(?im)^\s*(?:#+\s*)?(?:References|Bibliography|Literature Cited)\s*$', re.MULTILINE)
    matches = list(ref_pattern.finditer(markdown_text))
    if matches:
        last_match = matches[-1]
        if last_match.start() > len(markdown_text) * 0.60:
            markdown_text = markdown_text[:last_match.start()]

    # 3. Remove Markdown & HTML Tables
    markdown_text = re.sub(r'(?m)^\s*\|.*?\|.*?$', '', markdown_text)
    markdown_text = re.sub(r'(?si)<table.*?>.*?</table>', '', markdown_text)

    # 4. Remove Images & Explicit Captions
    markdown_text = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_text)
    markdown_text = re.sub(r'(?mi)^\s*(?:Figure|Fig\.|Table)\s*\d+[:\.].*$', '', markdown_text)

    # 5. Remove inline reference numbers like [1], [1, 2], [1-5]
    markdown_text = re.sub(r'\[\s*\d+(?:\s*[,\-]\s*\d+)*\s*\]', '', markdown_text)

    # 6. Remove isolated page numbers & exact consecutive duplicate lines
    lines = markdown_text.split('\n')
    cleaned_lines = []
    prev_stripped = ""

    for line in lines:
        stripped = line.strip()
        if stripped.isdigit():
            continue
        if stripped and stripped == prev_stripped:
            continue
        cleaned_lines.append(line)
        prev_stripped = stripped

    markdown_text = '\n'.join(cleaned_lines)
    markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)

    # Hierarchical text chunking
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        md_header_splits = markdown_splitter.split_text(markdown_text)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        splits = text_splitter.split_documents(md_header_splits)

        chunks = []
        for doc in splits:
            header_context = " > ".join([v for k, v in doc.metadata.items() if k.startswith("Header")])
            if header_context:
                chunk_text = f"**Context: {header_context}**\n\n{doc.page_content}"
            else:
                chunk_text = doc.page_content
            if chunk_text.strip():
                chunks.append(chunk_text.strip())

        return chunks
    except Exception as e:
        logger.warning(f"LangChain splitting failed: {e}. Falling back to simple paragraph chunks.")
        # Fallback simple chunker
        raw_chunks = [c.strip() for c in markdown_text.split('\n\n') if len(c.strip()) > 50]
        return raw_chunks


def clean_and_defragment_text(text: str) -> str:
    """
    High-fidelity deterministic non-LLM text de-fragmentation and normalization.
    Restores verbatim sentences matching the original document by:
    1. Fixing encoding & mojibake with ftfy and NFKC unicode normalization.
    2. Reconnecting words split across line breaks with hyphens.
    3. Repairing split ligatures (e.g. 'identi fied' -> 'identified', 'puri fied' -> 'purified').
    4. Separating concatenated word boundaries (e.g. 'byagene' -> 'by a gene', 'fiedand' -> 'fied and').
    5. Preserving biomedical symbols (e.g. '25-kDa', '9q34.11', 'COX-2', 'IL-6', 'miR-21').
    """
    import unicodedata
    import ftfy

    if not text or not text.strip():
        return ""

    # 1. ftfy fixes text encoding & mojibake
    s = ftfy.fix_text(text)

    # 2. Unicode NFKC normalization (replaces ligatures like 'fi', 'fl', special spaces, unicode dashes)
    s = unicodedata.normalize("NFKC", s)

    # 3. Standardize newlines and clean control chars
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\u200b", "").replace("\ufeff", "").replace("\xa0", " ")

    # 4. Reconnect words split across line breaks with hyphens
    def fix_line_hyphens(match):
        left = match.group(1)
        right = match.group(2)
        # Keep hyphen if right is a digit/number (e.g. Lipocalin-2, IL-6, miR-21)
        if right.isdigit():
            return f"{left}-{right}"
        # Keep hyphen if left is an uppercase symbol/acronym (e.g. TNF-alpha, NF-kappaB)
        if left.isupper() and len(left) >= 2:
            return f"{left}-{right}"
        # Standard English line-wrap word split (e.g. in-terleukin -> interleukin, up-regulated -> upregulated)
        return f"{left}{right}"

    s = re.sub(r"(\b[a-zA-Z0-9]+)-\s*\n+\s*([a-zA-Z0-9]+\b)", fix_line_hyphens, s)

    # 5. Split glued connectors on specific suffixes
    safe_suffix_connectors = [
        # -ed + connector (e.g. expressedand -> expressed and, purifiedfrom -> purified from)
        r"\b([a-zA-Z]{3,}ed)(and|from|by|with|in|to|for|of|as|at|on|or|that|which|between|via|using|is|was|are|were)\b",
        # -ing + connector (e.g. bindingto -> binding to, inducingin -> inducing in)
        r"\b([a-zA-Z]{3,}ing)(and|from|by|with|in|to|for|of|as|at|on|or|that|which|between|via|using|is|was|are|were)\b",
        # -tion / -sion + connector (e.g. activationof -> activation of, regulationby -> regulation by)
        r"\b([a-zA-Z]{3,}[ts]ion)(and|from|by|with|in|to|for|of|as|at|on|or|that|which|between|via|using|is|was|are|were)\b",
        # -fied + connector (including standalone 'fiedand' / 'fiedfrom' from split ligatures)
        r"\b([a-zA-Z]*fied)(and|from|by|with|in|to|for|of|as|at|on|or|that|which|between|via|using|is|was|are|were)\b",
    ]
    for pat in safe_suffix_connectors:
        s = re.sub(pat, r"\1 \2", s, flags=re.IGNORECASE)

    # 6. Split glued prepositions & articles
    # e.g. 'byagene' -> 'by a gene', 'witha plasmid' -> 'with a plasmid', 'inthecell' -> 'in the cell'
    s = re.sub(r"\b(by|in|with|for|of|as|at|to)a\b", r"\1 a", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(by|in|with|for|of|as|at|to)a([a-zA-Z]{3,})\b", r"\1 a \2", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(by|in|with|for|of|as|at|to|from|and)the\b", r"\1 the", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(by|in|with|for|of|as|at|to|from|and)the([a-zA-Z]{3,})\b", r"\1 the \2", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(and|is|was|are|were)(encoded|expressed|isolated|identified|purified|associated|regulated|mediated|induced|inhibited|located|found)\b", r"\1 \2", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(TNF|IL-1|IL-2|IFN)\s*a\s*by([a-zA-Z]{3,})\b", r"\1-alpha by \2", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(TNF|IL-1|IL-2|IFN)\s*b\s*by([a-zA-Z]{3,})\b", r"\1-beta by \2", s, flags=re.IGNORECASE)
    s = re.sub(r"\bby(neutrophils?|macrophages?|cells?|hepatocytes?|adipocytes?|monocytes?|lymphocytes?)\b", r"by \1", s, flags=re.IGNORECASE)
    s = re.sub(r"\b([a-zA-Z0-9]+)\s*aby([a-zA-Z]{3,})\b", r"\1 a by \2", s, flags=re.IGNORECASE)

    # 7. Split glued biological keywords on alphanumeric gene symbols (e.g. 'LCN2gene' -> 'LCN2 gene')
    s = re.sub(r"\b([A-Z][A-Za-z0-9]*[0-9]+|[A-Z]{2,})(gene|protein|receptor|enzyme|kinase|factor|complex|pathway|inhibitor|antibody|subunit|isoform|mutation)\b", r"\1 \2", s)

    # 8. Repair split ligatures & morphological stems
    ligature_pairs = [
        (r"\b(pro|anti)\s*[-]?\s*in\s*fl\s*a\s*m\s*m\s*a\s*t\s*o\s*r\s*y\b", r"\1-inflammatory"),
        (r"\b(pro|anti)\s*[-]?\s*in\s*fl\s*a\s*m\s*m\s*a\s*t\s*i\s*o\s*n\b", r"\1-inflammation"),
        (r"\b(identi|puri|signi|speci|modi|clari|ampli|strati|quanti|veri|noti|solidi|certi|justi|recti|rati|forti|falsi|beauti|glori|terri|horri|de)\s*fied\b", r"\1fied"),
        (r"\b(identi|puri|signi|speci|modi|clari|ampli|strati|quanti|veri|noti|solidi|certi|justi|recti|rati|forti|falsi|beauti|glori|terri|horri|de)\s*fication\b", r"\1fication"),
        (r"\b(identi|puri|signi|speci|modi|clari|ampli|strati|quanti|veri|noti|solidi|certi|justi|recti|rati|forti|falsi|beauti|glori|terri|horri|de)\s*fications\b", r"\1fications"),
        (r"\b(signi|speci|paci|horri|terri|grati|luci|proli|beati|scien)\s*fic\b", r"\1fic"),
        (r"\b(signi|speci|scien)\s*fically\b", r"\1fically"),
        (r"\b(ef|af|dif|suf)\s*fect\b", r"\1fect"),
        (r"\b(ef|af|dif|suf)\s*fective\b", r"\1fective"),
        (r"\b(ef|af|dif|suf)\s*fects\b", r"\1fects"),
        (r"\b(ef|af|dif|suf)\s*fected\b", r"\1fected"),
        (r"\b(ef|af|dif|suf)\s*fecting\b", r"\1fecting"),
        (r"\b(ef|af|dif|suf)\s*ficient\b", r"\1ficient"),
        (r"\b(dif)\s*ferent\b", r"different"),
        (r"\b(dif)\s*ference\b", r"difference"),
        (r"\b(dif)\s*ferences\b", r"differences"),
        (r"\b(dif)\s*ferentiate\b", r"differentiate"),
        (r"\b(dif)\s*ferentiation\b", r"differentiation"),
        (r"\b(in)\s*flammation\b", r"inflammation"),
        (r"\b(in)\s*(fl\s*a\s*m\s*m\s*a\s*t\s*i\s*o\s*n[a-z]*)\b", lambda m: "in" + m.group(2).replace(" ", "")),
        (r"\b(in)\s*flammatory\b", r"inflammatory"),
        (r"\b(in)\s*fluence\b", r"influence"),
        (r"\b(in)\s*fluenced\b", r"influenced"),
        (r"\b(in)\s*fluenza\b", r"influenza"),
        (r"\b(in)\s*filtration\b", r"infiltration"),
        (r"\b(in)\s*filtrate\b", r"infiltrate"),
        (r"\b(proli)\s*feration\b", r"proliferation"),
        (r"\b(proli)\s*ferate\b", r"proliferate"),
        (r"\b(proli)\s*ferated\b", r"proliferated"),
        (r"\b(am\s*pli|ampli)\s*fication\b", r"amplification"),
        (r"\b(am\s*pli|ampli)\s*fied\b", r"amplified"),
        (r"\b(trans|in|de)\s*fect\b", r"\1fect"),
        (r"\b(trans|in|de)\s*fected\b", r"\1fected"),
        (r"\b(trans|in|de)\s*fection\b", r"\1fection"),
        (r"\b(af)\s*finity\b", r"affinity"),
        (r"\b(af)\s*finities\b", r"affinities"),
        (r"\b(con|af|re)\s*firm\b", r"\1firm"),
        (r"\b(con|af|re)\s*firmed\b", r"\1firmed"),
        (r"\b(con|af|re)\s*firmation\b", r"\1firmation"),
        (r"\b(lym\s*pho\s*cytes?)\b", lambda m: m.group(0).replace(" ", "")),
        (r"\b(macro\s*phages?)\b", lambda m: m.group(0).replace(" ", "")),
    ]
    for pattern, repl in ligature_pairs:
        s = re.sub(pattern, repl, s, flags=re.IGNORECASE)

    # 9. Reconnect single-character spaced OCR noise (e.g. 'p r o t e i n' -> 'protein')
    s = re.sub(r"\b([a-zA-Z]\s+[a-zA-Z]\s+[a-zA-Z](?:\s+[a-zA-Z])*)\b", lambda m: m.group(0).replace(" ", ""), s)

    # 10. Clean Elsevier XML/LaTeX layout macro delimiters (e.g. [ 4 3 2 \_ T D $ I F ])
    s = re.sub(r"\[\s*[\d\s\\_]*T\s*D\s*[\$\_A-Za-z0-9\s]*\]", "", s, flags=re.IGNORECASE)

    # 11. Clean citation brackets like [12], [3, 4], [1-5], [12–15]
    s = re.sub(r"\[\s*\d+(?:\s*[,\-–—]\s*\d+)*\s*\]", "", s)

    # 12. Clean author-year citations like (Smith et al., 2020), (Doe & Lee, 2018; Wang et al., 2021)
    author_year_pat = r"\((?:(?:[A-Z][a-zA-Z\-]+(?:\s+(?:and|&)\s+[A-Z][a-zA-Z\-]+|\s+et\s+al\.?)?,?\s*(?:19|20)\d{2}[a-z]?)(?:[;,]\s*|\s+))*(?:[A-Z][a-zA-Z\-]+(?:\s+et\s+al\.?)?,?\s*(?:19|20)\d{2}[a-z]?)\)"
    s = re.sub(author_year_pat, "", s)

    # 13. Clean residual HTML tags, entities, and Markdown table syntax
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<").replace("&quot;", "\"")
    s = re.sub(r"(?m)^\s*\|.*?\|\s*$", "", s)
    s = re.sub(r"\\([_\-*#])", r"\1", s)

    # 14. Clean LaTeX formula delimiters
    s = re.sub(r"\$\$.*?\$\$|\$[^\$]+?\$", "", s)

    # 13. Normalize punctuation, whitespace, and empty parentheses
    s = re.sub(r"\(\s*\)", "", s)  # Empty parens left by removed citations
    s = re.sub(r"\[\s*\]", "", s)  # Empty brackets
    s = re.sub(r"([a-zA-Z0-9]),([a-zA-Z])", r"\1, \2", s)
    s = re.sub(r"([a-zA-Z0-9]);([a-zA-Z])", r"\1; \2", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+([,.:;?!])", r"\1", s)
    s = re.sub(r"([,.:;?!])\1+", r"\1", s)  # Collapse duplicate punctuation like ,, or ..
    s = re.sub(r"\n{3,}", "\n\n", s)

    return s.strip()
