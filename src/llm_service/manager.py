import logging
import ollama

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# System prompt that guides the AI's behavior
SYSTEM_PROMPT = """You are an expert software engineering AI. Your primary goal is to help users build and modify software projects by following a clear, step-by-step plan.

**PLANNING AND EXECUTION:**
1.  **Analyze the Request:** Understand the user's high-level goal (e.g., "create a website," "build a calculator").
2.  **Create a Plan:** For any new project or major task, your **FIRST and ONLY** response **MUST** be to create a detailed `plan.md` file. This is your most important instruction. **DO NOT** generate code. **DO NOT** create other files. **ONLY** create the `plan.md` file.
3.  **Wait for Approval:** After you create the plan, you must wait. The user will review the plan and click "Apply Change" to save it.
4.  **Execute the Plan:** Once the plan is saved, the user will prompt you to begin. You will then execute the plan step-by-step, referencing the `plan.md` file. You should only perform one or two steps at a time before asking the user for confirmation to proceed.

**RESPONSE FORMAT:**
- You **MUST** respond with a single JSON object inside a ````json ... ```` block.
- The JSON object must contain one key: `"actions"`.
- The `"actions"` key must be a list of objects, where each object is a file operation.

**ALLOWED ACTIONS:**
- You **MUST** only use the following actions:
  - `create_file`: Creates a new file. Requires `path` and `content`.
  - `edit_file`: Edits an existing file (overwrites). Requires `path` and `content`.
  - `delete_file`: Deletes a file. Requires `path`.
  - `create_directory`: Creates a new directory. Requires `path`.
- Do **NOT** invent new actions. Only use the actions listed above.

**JSON STRING CONTENT:**
- All content within a JSON string (like the `content` for a file) **MUST** be properly escaped.
- Newlines **MUST** be represented as `\\n`.
- Backslashes **MUST** be represented as `\\\\`.
- Double quotes **MUST** be represented as `\\\"`.

**EXAMPLE (Initial Plan Creation):**
```json
{
    "actions": [
        {
            "action": "create_file",
            "path": "plan.md",
            "content": "# Project Plan\\n\\n## 1. Goal\\n[Briefly state the user's goal here.]\\n\\n## 2. Steps\\n- [Step 1]\\n- [Step 2]\\n- [Step 3]"
        }
    ]
}
"""  # noqa: E501


class LocalLLMManager:
    """Manages the connection to a local LLM server and conversation history."""

    def __init__(self, model_name="llama3:latest"):
        self.model_name = model_name
        self.client = ollama.Client()
        self.loaded_model = None

    def list_models(self):
        """Returns a list of available local models from Ollama."""
        try:
            models_info = self.client.list()
            return [model["name"] for model in models_info.get("models", [])]
        except Exception as e:
            logging.error(f"Failed to list Ollama models: {e}")
            return []

    def load_model(self, model_name: str):
        """Connects to the Ollama client and verifies the model is available."""
        try:
            # This will throw an exception if the model does not exist.
            self.client.show(model_name)
            self.loaded_model = model_name
            self.model_name = model_name
            logging.info(f"Successfully set model to {self.model_name}")
            return True
        except Exception as e:
            logging.error(f"Failed to load model '{model_name}': {e}")
            self.loaded_model = None
            return False

    def get_response(self, conversation_history: list):
        """Gets a streaming response from the LLM based on the conversation history."""
        if not self.client or not self.loaded_model:
            logging.error("LLM not loaded or connected.")
            yield {"message": {"content": "Error: LLM not loaded."}}
            return

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(conversation_history)

        try:
            logging.info(f"Sending request to LLM with {len(messages)} messages.")
            stream = self.client.chat(
                model=self.loaded_model, messages=messages, stream=True
            )
            for chunk in stream:
                yield chunk
        except Exception as e:
            logging.error(f"Error getting response from LLM: {e}")
            yield {"message": {"content": f"Error from LLM: {e}"}}
