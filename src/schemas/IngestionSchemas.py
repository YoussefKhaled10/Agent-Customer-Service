from pydantic import BaseModel, Field


class IngestionResult(BaseModel):
    document_id: int
    title: str
    file_name: str
    file_hash: str
    pages_processed: int = Field(ge=1)
    blocks_extracted: int = Field(ge=1)
    chunks_created: int = Field(ge=0)
    embedding_dimension: int = Field(ge=1)
    index_status: str
    duplicate: bool = False
