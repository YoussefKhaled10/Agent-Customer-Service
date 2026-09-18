from __future__ import annotations

import json
from pathlib import Path

from src.ingestion.layout_block_refiner import LayoutBlockRefiner
from src.ingestion.layout_pdf_extractor import LayoutPDFExtractor
from src.schemas.ModelChunkingSchemas import FinalChunk, LayoutBlock
from src.ingestion.model_document_chunker import ModelDocumentChunker


class ModelIngestionPipeline:
    def __init__(
        self,
        extractor: LayoutPDFExtractor | None = None,
        refiner: LayoutBlockRefiner | None = None,
        chunker: ModelDocumentChunker | None = None,
    ) -> None:
        self.extractor = extractor or LayoutPDFExtractor()
        self.refiner = refiner or LayoutBlockRefiner()
        self.chunker = chunker or ModelDocumentChunker()

    def extract_and_refine(self, file_path: str | Path) -> list[LayoutBlock]:
        return self.refiner.refine(self.extractor.extract(file_path))

    def process_models(self, file_path: str | Path) -> list[FinalChunk]:
        return self.chunker.chunk(self.extract_and_refine(file_path))

    def process(self, file_path: str | Path) -> list[dict]:
        return [chunk.model_dump() for chunk in self.process_models(file_path)]

    @staticmethod
    def save_to_json(
        chunks: list[FinalChunk] | list[dict],
        output_path: str | Path,
    ) -> Path:
        output = Path(output_path).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        serialized = [
            chunk.model_dump() if isinstance(chunk, FinalChunk) else chunk
            for chunk in chunks
        ]
        output.write_text(
            json.dumps({"knowledge_chunks": serialized}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output

    def process_to_json(self, file_path: str | Path, output_path: str | Path) -> Path:
        return self.save_to_json(self.process_models(file_path), output_path)
