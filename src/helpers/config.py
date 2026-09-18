from functools import lru_cache
from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


ENV_FILE_PATH = (
    Path(__file__).resolve().parents[1]
    / ".env"
)


class Settings(BaseSettings):
    # Application
    APP_NAME: str = (
        "PharmaCare AI Sales & Customer Service Agent"
    )
    
    # remove all default values for the following variables to force users to set them in the .env file
    
    APP_VERSION: str 
    APP_ENV: str
    APP_HOST: str
    APP_PORT: int
    DEBUG: bool
    SECRET_KEY: str

    # PostgreSQL
    POSTGRES_USER: str 
    POSTGRES_PASSWORD: str 
    POSTGRES_DB: str 
    POSTGRES_HOST: str 
    POSTGRES_PORT: int 
    POSTGRES_URL: str 

    # Cohere
    COHERE_API_KEY: str 
    COHERE_API_BASE_URL: str 
    
    DOCUMENT_CHUNKING_PROVIDER: str
    DOCUMENT_CHUNKING_MODEL: str

    # Embeddings
    EMBEDDING_BACKEND: str
    EMBEDDING_MODEL: str 
    EMBEDDING_DIMENSION: int 
    EMBEDDING_BATCH_SIZE: int 
    EMBEDDING_NORMALIZE: bool 
    EMBEDDING_TYPE: str 
    EMBEDDING_DOCUMENT_INPUT_TYPE: str 
    EMBEDDING_QUERY_INPUT_TYPE: str 

    # PDF limits
    PDF_MAX_FILE_SIZE_MB: int
    PDF_MAX_PAGES: int 
    PDF_MIN_EXTRACTED_CHARACTERS: int 

    # Model chunking
    MODEL_CHUNK_TARGET_TOKENS: int 
    MODEL_CHUNK_MAX_TOKENS: int
    MODEL_CHUNK_MAX_BLOCKS_PER_REQUEST: int
    MODEL_CHUNK_MAX_BLOCKS_PER_REQUEST: int 
    MODEL_CHUNK_BATCH_OVERLAP_BLOCKS: int 
    MODEL_CHUNK_TIMEOUT_SECONDS: int
    MODEL_CHUNK_PLANNER_WINDOW: int
    MODEL_CHUNK_PLANNER_CONCURRENCY: int
    MODEL_CHUNK_MAX_RETRIES: int 

    MODEL_CHUNK_INCLUDE_CAPTIONS: bool 
    MODEL_CHUNK_INCLUDE_TABLES: bool 
    MODEL_CHUNK_INCLUDE_REFERENCES: bool 
    
    MODEL_CHUNK_BATCH_OVERLAP_BLOCKS:int
    MODEL_CHUNK_MAX_RETRIES:int 
    
    
    LAYOUT_BLOCK_TARGET_TOKENS: int 
    LAYOUT_BLOCK_MAX_TOKENS: int
    
    QUERY_REWRITE_PROVIDER:str
    RETRIEVAL_QUERY_REWRITE_MODEL:str
    RERANK_MODEL:str
    
    # Final answer generation
    ANSWER_PROVIDER: str
    GROQ_API_KEY: str
    GROQ_ANSWER_MODEL: str
    GEMINI_API_KEY: str
    GEMINI_ANSWER_MODEL: str
    
    # Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    AGENT_PROVIDER:str 
    AGENT_MODEL:str
    AGENT_MAX_TOOL_ITERATIONS:int
    
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()