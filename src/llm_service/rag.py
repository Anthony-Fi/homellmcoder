import logging
from pathlib import Path
from typing import Optional, List

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class RAGSystem:
    """Manages Retrieval-Augmented Generation.

    This includes document indexing and querying.
    """

    def __init__(self, vector_db_path: Optional[str] = None):
        """
        Initializes the RAG system.

        Args:
            vector_db_path: The path to the vector database. If None, uses a default.
        """
        if vector_db_path:
            self.vector_db_path = Path(vector_db_path)
        else:
            self.vector_db_path = Path.home() / ".homellmcoder" / "vector_db"

        self._create_vector_db_dir()
        self.indexed_documents: List[str] = []  # In-memory store for now

    def _create_vector_db_dir(self):
        """Creates the vector database directory if it doesn't exist."""
        try:
            self.vector_db_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Vector database directory is set to: {self.vector_db_path}")
        except OSError as e:
            logging.error(f"Failed to create vector database directory: {e}")
            raise

    def index(self, file_path: str) -> bool:
        """
        Indexes a document by reading its content into an in-memory list.

        Args:
            file_path: The path to the document to index.

        Returns:
            True if indexing was successful, False otherwise.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.indexed_documents.append(content)
            logging.info(f"Successfully indexed content from: {file_path}")
            logging.info(f"Total documents indexed: {len(self.indexed_documents)}")
            return True
        except FileNotFoundError:
            logging.error(f"File not found during indexing: {file_path}")
            return False
        except Exception as e:
            logging.error(f"An error occurred during indexing of {file_path}: {e}")
            return False

    def query(self, query_text: str) -> Optional[str]:
        """
        Queries the indexed documents. (This is a stub)

        Args:
            query_text: The query to search for.

        Returns:
            A relevant document snippet, or None if not found.
        """
        logging.info(f"Received query: '{query_text}'")
        if not self.indexed_documents:
            logging.warning("Query attempted, but no documents are indexed.")
            return "No documents have been indexed yet."

        # Stubbed search: return the first document that contains the query text
        for doc in self.indexed_documents:
            if query_text.lower() in doc.lower():
                logging.info("Found a matching document for the query.")
                return doc[:500] + "..."  # Return a snippet

        logging.info("No matching document found for the query.")
        return "No relevant document found."
