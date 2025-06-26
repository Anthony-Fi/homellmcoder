import os
import logging
from pathlib import Path
import ollama

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LocalLLMManager:
    """Manages the discovery and loading of local language models via Ollama."""

    def __init__(self):
        """Initializes the LLM manager."""
        logging.info("--- Initializing LocalLLMManager ---")
        self.loaded_model = None
        self.client = None  # Ensure client attribute always exists
        logging.info("--- self.client initialized to None ---")
        self.client = self._get_ollama_client()
        logging.info(f"--- self.client is now: {type(self.client)} ---")
        self.conversation_history = []
        logging.info("--- LocalLLMManager initialization complete ---")

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
            self.client.show(model_name)
            self.loaded_model = model_name
            self.conversation_history = []  # Reset history when a new model is loaded
            logging.info(f"Model '{model_name}' is ready for use.")
            return {"status": "success", "message": f"Model '{model_name}' loaded."}
        except Exception as e:
            logging.error(f"Failed to load model '{model_name}': {e}")
            return {"status": "error", "message": f"Failed to load model '{model_name}'."}

    def get_response(self, prompt: str, user_file_content: str = None):
        """Generates a response from the loaded model, streaming the output."""
        if not self.loaded_model:
            yield "No model is loaded. Please load a model first."
            return

        if not self.client:
            yield "Ollama client not available."
            return

        try:
            # Construct the full prompt with context
            full_prompt = self.construct_prompt_with_history(prompt, user_file_content)

            # Add the user's new message to the history
            self.conversation_history.append({'role': 'user', 'content': full_prompt})

            # Generate the response
            response = self.client.chat(
                model=self.loaded_model,
                messages=self.conversation_history,
                stream=True
            )

            # Process and yield the streaming response
            assistant_response = ""
            for chunk in response:
                content = chunk['message']['content']
                assistant_response += content
                yield content

            # Add the assistant's full response to the history
            self.conversation_history.append({'role': 'assistant', 'content': assistant_response})

        except Exception as e:
            logging.error(f"Error getting response from model: {e}")
            yield f"Error: {e}"

    def construct_prompt_with_history(self, new_prompt, file_content):
        """Constructs a prompt including conversation history and file context."""
        # This is a simplified example. A more robust implementation would manage token limits.
        if file_content:
            return f"File Content:\n```\n{file_content}\n```\n\nUser Request: {new_prompt}"
        return new_prompt

    def get_loaded_model(self):
        """Returns the name of the currently loaded model."""
        return self.loaded_model
