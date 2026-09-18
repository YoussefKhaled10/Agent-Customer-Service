from __future__ import annotations

from pathlib import Path

import pymupdf

from src.helpers.config import settings
from src.exceptions.IngestionExceptions import (
    InvalidPDFError,
    PDFPageLimitError,
    PDFSizeLimitError,
    PDFTextNotFoundError,
)
from src.schemas.ModelChunkingSchemas import LayoutBlock, LayoutSpan


class LayoutPDFExtractor:
    """Extract source text and layout evidence without semantic classification."""

    def extract(self, file_path: str | Path) -> list[LayoutBlock]:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != ".pdf":
            raise InvalidPDFError("A valid PDF file is required.")

        max_bytes = settings.PDF_MAX_FILE_SIZE_MB * 1024 * 1024
        if path.stat().st_size > max_bytes:
            raise PDFSizeLimitError("PDF exceeds the configured file-size limit.")

        try:
            document = pymupdf.open(path)
        except Exception as error:
            raise InvalidPDFError(f"Unable to open PDF: {error}") from error

        try:
            if document.needs_pass:
                raise InvalidPDFError("Password-protected PDFs are not supported.")
            if document.page_count < 1:
                raise InvalidPDFError("The PDF contains no pages.")
            if document.page_count > settings.PDF_MAX_PAGES:
                raise PDFPageLimitError("PDF exceeds the configured page limit.")

            output: list[LayoutBlock] = []
            reading_order = 0
            extracted_characters = 0

            for page_index, page in enumerate(document):
                previous_bottom: float | None = None
                page_number = page_index + 1
                page_data = page.get_text("dict", sort=True)

                for block_index, raw_block in enumerate(page_data.get("blocks", [])):
                    if raw_block.get("type") != 0:
                        continue

                    spans: list[LayoutSpan] = []
                    lines: list[str] = []
                    font_sizes: list[float] = []

                    for raw_line in raw_block.get("lines", []):
                        line_parts: list[str] = []
                        for raw_span in raw_line.get("spans", []):
                            span_text = str(raw_span.get("text", ""))
                            if not span_text:
                                continue
                            font_name = str(raw_span.get("font", ""))
                            font_size = float(raw_span.get("size", 0.0))
                            flags = int(raw_span.get("flags", 0))
                            bbox = tuple(float(v) for v in raw_span.get("bbox", (0, 0, 0, 0)))
                            spans.append(LayoutSpan(
                                text=span_text,
                                font_name=font_name,
                                font_size=font_size,
                                is_bold="bold" in font_name.casefold(),
                                is_italic=bool(flags & 2) or any(
                                    marker in font_name.casefold()
                                    for marker in ("italic", "oblique")
                                ),
                                bbox=bbox,
                            ))
                            font_sizes.append(font_size)
                            line_parts.append(span_text)
                        line_text = "".join(line_parts).strip()
                        if line_text:
                            lines.append(line_text)

                    text = "\n".join(lines).strip()
                    if not text:
                        continue

                    block_bbox = tuple(float(v) for v in raw_block.get("bbox", (0, 0, 0, 0)))
                    distance = None if previous_bottom is None else max(0.0, block_bbox[1] - previous_bottom)
                    average_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0.0
                    maximum_size = max(font_sizes) if font_sizes else 0.0

                    output.append(LayoutBlock(
                        block_id=f"p{page_number}_b{block_index}",
                        page_number=page_number,
                        block_index=block_index,
                        reading_order=reading_order,
                        text=text,
                        bbox=block_bbox,
                        page_width=float(page.rect.width),
                        page_height=float(page.rect.height),
                        page_rotation=int(page.rotation),
                        distance_from_previous=distance,
                        average_font_size=average_size,
                        maximum_font_size=maximum_size,
                        spans=spans,
                    ))
                    reading_order += 1
                    extracted_characters += len(text)
                    previous_bottom = block_bbox[3]

            if extracted_characters < settings.PDF_MIN_EXTRACTED_CHARACTERS:
                raise PDFTextNotFoundError(
                    "The PDF contains insufficient extractable text and may require OCR."
                )
            return output
        finally:
            document.close()
