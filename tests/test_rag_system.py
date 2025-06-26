import unittest
import tempfile
import shutil
import pathlib
from unittest.mock import patch

# Adjust the path to import from the src directory
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from llm_service.rag import RAGSystem

class TestRAGSystem(unittest.TestCase):
    """Unit tests for the RAGSystem class."""

    def setUp(self):
        """Set up a temporary directory for tests."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up the temporary directory after tests."""
        shutil.rmtree(self.test_dir)

    def test_default_db_path_creation(self):
        """Test that the default vector DB directory is created."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = pathlib.Path(self.test_dir)
            rag = RAGSystem()
            expected_dir = pathlib.Path(self.test_dir) / ".homellmcoder" / "vector_db"
            self.assertEqual(rag.db_path, expected_dir)
            self.assertTrue(expected_dir.exists())

    def test_custom_db_path_creation(self):
        """Test that a custom vector DB directory is created."""
        custom_dir = pathlib.Path(self.test_dir) / "custom_db"
        rag = RAGSystem(db_path=str(custom_dir))
        self.assertEqual(rag.db_path, custom_dir)
        self.assertTrue(custom_dir.exists())

    def test_index_stub(self):
        """Test the index method stub."""
        rag = RAGSystem(db_path=self.test_dir)
        documents = [
            {'id': 'doc1', 'content': 'Hello world'},
            {'id': 'doc2', 'content': 'This is a test'}
        ]
        success = rag.index(documents)
        self.assertTrue(success)
        # Check that a log file was created to simulate indexing
        self.assertTrue((pathlib.Path(self.test_dir) / "index.log").exists())

    def test_index_no_documents(self):
        """Test indexing with no documents."""
        rag = RAGSystem(db_path=self.test_dir)
        success = rag.index([])
        self.assertFalse(success)

    def test_query_stub(self):
        """Test the query method stub."""
        rag = RAGSystem(db_path=self.test_dir)
        results = rag.query("What is this?")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertIn("placeholder result", results[0])

    def test_query_empty(self):
        """Test querying with an empty string."""
        rag = RAGSystem(db_path=self.test_dir)
        results = rag.query("")
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
