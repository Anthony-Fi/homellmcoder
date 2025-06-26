import os
import logging
from pathlib import Path
import ollama

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LocalLLMManager:
    """Manages the discovery and loading of local language models via Ollama."""

    def __init__(self):
        """Initializes the LLM manager."""
        self.loaded_model = None
        self.client = self._get_ollama_client()
        self.conversation_history = []

    def _get_ollama_client(self):
        """Establishes connection with the Ollama service."""
        try:
            client = ollama.Client()
            # The following line is a health check to see if the service is responsive
            client.list()
            logging.info("Successfully connected to Ollama service.")
            return client
        except Exception as e:
            logging.error(f"Failed to connect to Ollama service. Please ensure Ollama is running. Error: {e}")
            return None

    def discover_models(self) -> list[str]:
        """Discovers available models from the Ollama service."""
        if not self.client:
            logging.warning("Cannot discover models, Ollama client not available.")
            return []
        
        try:
            models = self.client.list()['models']
            model_names = [model['name'] for model in models]
            logging.info(f"Discovered models: {model_names}")
            return model_names
        except Exception as e:
            logging.error(f"An error occurred while discovering models: {e}")
            return []

    def load_model(self, model_name: str) -> dict:
        """'Loads' a model by verifying its existence and preparing for use."""
        if not self.client:
            return {"status": "error", "message": "Ollama client not available."}

        if not model_name:
            return {"status": "error", "message": "No model name provided."}

        try:
            # For Ollama, 'loading' is implicit. We just verify the model exists.
            # A more robust check might involve a quick interaction.
            self.client.show(model_name)
            self.loaded_model = model_name
            logging.info(f"Model '{model_name}' is ready for use.")
            return {"status": "success", "message": f"Model '{model_name}' loaded."}
        except ollama.ResponseError as e:
            logging.error(f"Failed to load model '{model_name}'. Error: {e.error}")
            return {"status": "error", "message": f"Model '{model_name}' not found or invalid."}
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading model '{model_name}': {e}")
            return {"status": "error", "message": "An unexpected error occurred."}

    def chat_stream(self, prompt: str, callback):
        """Sends a prompt to the model and streams the response via a callback."""
        if not self.loaded_model:
            callback({"status": "error", "message": "No model loaded."})
            return

        if not self.client:
            callback({"status": "error", "message": "Ollama client not available."})
            return

        self.conversation_history.append({'role': 'user', 'content': prompt})

        try:
            stream = self.client.chat(
                model=self.loaded_model,
                messages=self.conversation_history,
                stream=True
            )

            full_response = ""
            for chunk in stream:
                chunk_content = chunk['message']['content']
                full_response += chunk_content
                callback({"status": "chunk", "content": chunk_content})

            self.conversation_history.append({'role': 'assistant', 'content': full_response})
            callback({"status": "done"})

        except Exception as e:
            logging.error(f"Error during chat stream: {e}")
            # Reset history on error to avoid corruption
            self.conversation_history.pop()
            callback({"status": "error", "message": str(e)})

    def get_loaded_model(self):
        """Returns the name of the currently loaded model."""
        return self.loaded_model
