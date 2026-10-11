"""
SEC EDGAR Filing Section Extractor
Extracts and isolates key sections from 10-Q and 10-K filings:
- Item 1: Financial Statements
- Item 2 / Item 7: Management's Discussion and Analysis (MD&A)
- Item 1A: Risk Factors
- Guidance & Segment revenue mentions
"""
import re
from typing import Dict, Any, Optional


class FilingSectionExtractor:

    # 10-Q Item patterns
    ITEM_PATTERNS_10Q = {
        "financial_statements": {
            "title": "Item 1. Financial Statements",
            "start": r"(?:item\s+1[\.\:\s]+financial\s+statements)",
            "end": r"(?:item\s+2[\.\:\s]+management['’]s\s+discussion|part\s+ii)"
        },
        "mda": {
            "title": "Item 2. Management's Discussion & Analysis (MD&A)",
            "start": r"(?:item\s+2[\.\:\s]+management['’]s\s+discussion\s+and\s+analysis)",
            "end": r"(?:item\s+3[\.\:\s]+quantitative\s+and\s+qualitative|item\s+4[\.\:\s]+controls|part\s+ii)"
        },
        "risk_factors": {
            "title": "Item 1A. Risk Factors",
            "start": r"(?:item\s+1a[\.\:\s]+risk\s+factors)",
            "end": r"(?:item\s+2[\.\:\s]+unregistered\s+sales|item\s+5[\.\:\s]+other|item\s+6[\.\:\s]+exhibits|signatures)"
        }
    }

    # 10-K Item patterns
    ITEM_PATTERNS_10K = {
        "business": {
            "title": "Item 1. Business",
            "start": r"(?:item\s+1[\.\:\s]+business)",
            "end": r"(?:item\s+1a[\.\:\s]+risk\s+factors|item\s+1b)"
        },
        "risk_factors": {
            "title": "Item 1A. Risk Factors",
            "start": r"(?:item\s+1a[\.\:\s]+risk\s+factors)",
            "end": r"(?:item\s+1b|item\s+2[\.\:\s]+properties|item\s+3[\.\:\s]+legal)"
        },
        "mda": {
            "title": "Item 7. Management's Discussion & Analysis (MD&A)",
            "start": r"(?:item\s+7[\.\:\s]+management['’]s\s+discussion\s+and\s+analysis)",
            "end": r"(?:item\s+7a[\.\:\s]+quantitative|item\s+8[\.\:\s]+financial\s+statements)"
        },
        "financial_statements": {
            "title": "Item 8. Financial Statements and Supplementary Data",
            "start": r"(?:item\s+8[\.\:\s]+financial\s+statements\s+and\s+supplementary\s+data)",
            "end": r"(?:item\s+9[\.\:\s]+changes\s+in|item\s+9a[\.\:\s]+controls)"
        }
    }

    @classmethod
    def extract_sections(cls, raw_text: str, form_type: str = "10-Q") -> Dict[str, Any]:
        """
        Extract isolated sections from full filing text using robust regex slicing.
        Skips Table of Contents false-positives by searching after character offset 1000.
        """
        if not raw_text:
            return {}

        is_10k = "10-K" in form_type.upper()
        patterns = cls.ITEM_PATTERNS_10K if is_10k else cls.ITEM_PATTERNS_10Q

        extracted = {}

        # Search beyond initial TOC (Table of Contents)
        search_start_offset = 2000 if len(raw_text) > 8000 else 0

        for sec_key, pat in patterns.items():
            start_regex = re.compile(pat["start"], re.IGNORECASE)
            end_regex = re.compile(pat["end"], re.IGNORECASE)

            # Find all start candidate positions
            matches = list(start_regex.finditer(raw_text))
            best_candidate = None
            best_candidate_len = -1

            for m in matches:
                start_pos = m.start()
                end_match = end_regex.search(raw_text, start_pos + 100)
                end_pos = end_match.start() if end_match else min(len(raw_text), start_pos + 40000)
                sec_slice = raw_text[start_pos:end_pos].strip()
                slice_len = len(sec_slice)

                # Prioritize candidates that have substantial content (> 1,000 chars)
                if slice_len > 1000:
                    best_candidate = (start_pos, end_pos, sec_slice)
                    best_candidate_len = slice_len
                    break  # First substantial match is the actual section body
                elif slice_len > best_candidate_len:
                    best_candidate = (start_pos, end_pos, sec_slice)
                    best_candidate_len = slice_len

            if best_candidate and best_candidate_len > 0:
                sec_text = best_candidate[2]
                sec_text = re.sub(r'\n{3,}', '\n\n', sec_text)

                extracted[sec_key] = {
                    "title": pat["title"],
                    "length": len(sec_text),
                    "text": sec_text[:40000],  # Max safe display size
                    "preview": sec_text[:1200]
                }
            else:
                extracted[sec_key] = {
                    "title": pat["title"],
                    "length": 0,
                    "text": "",
                    "preview": "(해당 섹션 위치를 자동 분할하지 못했습니다. 원문 전문 탭에서 확인하세요.)"
                }

        # Key highlight extraction (e.g. Guidance, Segments)
        extracted["highlights"] = cls._extract_highlights(raw_text)

        return extracted

    @classmethod
    def _extract_highlights(cls, raw_text: str) -> Dict[str, str]:
        """Extract quick mentions of outlook, guidance, or segment performance."""
        highlights = {
            "guidance_mentions": [],
            "segment_mentions": []
        }

        # Look for guidance paragraphs
        guidance_patterns = [
            r"(?:for\s+the\s+(?:third|fourth|first|second)\s+quarter\s+of\s+fiscal\s+\d{4}[^\.]*\.)",
            r"(?:revenue\s+is\s+expected\s+to\s+be[^\.]*\.)",
            r"(?:gross\s+margins\s+are\s+expected\s+to\s+be[^\.]*\.)"
        ]
        for p in guidance_patterns:
            matches = re.findall(p, raw_text, re.IGNORECASE)
            for m in matches[:3]:
                if len(m) > 30 and m not in highlights["guidance_mentions"]:
                    highlights["guidance_mentions"].append(m.strip())

        return highlights
