import unittest
import tempfile
import shutil
import pathlib
from unittest.mock import patch, MagicMock

# Adjust the path to import from the src directory
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from llm_service.manager import LocalLLMManager

class TestLocalLLMManager(unittest.TestCase):
    """Unit tests for the LocalLLMManager class."""

    def setUp(self):
        """Set up a temporary directory for tests."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up the temporary directory after tests."""
        shutil.rmtree(self.test_dir)

    def test_default_model_dir_creation(self):
        """Test that the default model directory is created."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = pathlib.Path(self.test_dir)
            manager = LocalLLMManager()
            expected_dir = pathlib.Path(self.test_dir) / ".homellmcoder" / "models"
            self.assertEqual(manager.model_dir, expected_dir)
            self.assertTrue(expected_dir.exists())

    def test_custom_model_dir_creation(self):
        """Test that a custom model directory is created."""
        custom_dir = pathlib.Path(self.test_dir) / "custom_models"
        manager = LocalLLMManager(model_dir=str(custom_dir))
        self.assertEqual(manager.model_dir, custom_dir)
        self.assertTrue(custom_dir.exists())

    def test_discover_models_empty(self):
        """Test model discovery when the directory is empty."""
        manager = LocalLLMManager(model_dir=self.test_dir)
        self.assertEqual(manager.discover_models(), [])

    def test_discover_models_with_models(self):
        """Test model discovery with some models present."""
        manager = LocalLLMManager(model_dir=self.test_dir)
        (pathlib.Path(self.test_dir) / "model1").mkdir()
        (pathlib.Path(self.test_dir) / "model2").mkdir()
        # Create a file to ensure it's ignored
        (pathlib.Path(self.test_dir) / "a_file.txt").touch()

        discovered = manager.discover_models()
        self.assertIn("model1", discovered)
        self.assertIn("model2", discovered)
        self.assertEqual(len(discovered), 2)

    def test_download_model_stub(self):
        """Test the download_model stub functionality."""
        manager = LocalLLMManager(model_dir=self.test_dir)
        model_id = "test-model"
        
        success = manager.download_model(model_id)
        self.assertTrue(success)
        
        model_path = pathlib.Path(self.test_dir) / model_id
        self.assertTrue(model_path.exists())
        self.assertTrue((model_path / "config.json").exists())

    def test_load_model_not_found(self):
        """Test loading a model that does not exist."""
        manager = LocalLLMManager(model_dir=self.test_dir)
        model = manager.load_model("non_existent_model")
        self.assertIsNone(model)

    def test_load_model_stub(self):
        """Test the load_model stub functionality."""
        manager = LocalLLMManager(model_dir=self.test_dir)
        model_id = "test-model"
        (pathlib.Path(self.test_dir) / model_id).mkdir()
        
        model = manager.load_model(model_id)
        self.assertIsNotNone(model)
        self.assertIsInstance(model, object)

if __name__ == '__main__':
    unittest.main()
