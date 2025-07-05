import ollama
import logging

logging.basicConfig(level=logging.INFO)

def list_ollama_models():
    try:
        client = ollama.Client()
        models_info = client.list()
        model_names = [model["name"] for model in models_info.get("models", [])]
        logging.info(f"Available Ollama models: {model_names}")
        if "deepseek-coder:8b" in model_names or "deepseek-r1:8b" in model_names:
            logging.info("deepseek-coder:8b or deepseek-r1:8b found!")
        else:
            logging.warning("deepseek-coder:8b or deepseek-r1:8b not found.")
        return model_names
    except Exception as e:
        logging.error(f"Failed to list Ollama models: {e}")
        return []

if __name__ == "__main__":
    list_ollama_models()
