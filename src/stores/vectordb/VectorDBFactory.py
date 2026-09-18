from src.stores.vectordb.VectorDBEnums import VectorDBProvider
from src.stores.vectordb.VectorDBInterface import VectorDBInterface
from src.stores.vectordb.providers import PGVectorProvider


class VectorDBFactory:
    @staticmethod
    def create(provider: str | VectorDBProvider = VectorDBProvider.PGVECTOR) -> VectorDBInterface:
        selected = VectorDBProvider(provider)
        if selected == VectorDBProvider.PGVECTOR:
            return PGVectorProvider()
        raise ValueError(f"Unsupported vector database provider: {selected}")
