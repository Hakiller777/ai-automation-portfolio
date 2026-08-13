"""Custom exception hierarchy for the RAG support chatbot pipeline."""


class IngestionError(Exception):
    """Raised when the knowledge base cannot be chunked, embedded, or stored."""


class RetrievalError(Exception):
    """Raised when the vector store cannot be queried."""


class AgentError(Exception):
    """Raised when answer generation fails unexpectedly."""
