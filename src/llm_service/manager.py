import logging
import ollama

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# System prompt that guides the AI's behavior
SYSTEM_PROMPT = """You are an expert software engineering AI. Your primary goal is to help users build and modify software projects by following a clear, step-by-step plan.

**PLANNING AND EXECUTION:**
1.  **Analyze the Request:** Understand the user's high-level goal (e.g., "create a website," "build a calculator," "develop a mobile app").
2.  **Create a Plan:** For any new project or major task, your **FIRST and ONLY** response **MUST** be to create a detailed `plan.md` file. This is your most important instruction. **DO NOT** generate code. **DO NOT** create other files (e.g., `main.py`, `requirements.txt`). **ONLY** create the `plan.md` file. Your output must contain **ONLY ONE** action, which is to `create_file` for `plan.md`. No other files, no `run_command` actions, just `plan.md`.
    *   The `plan.md` should be a high-level project outline, focusing on the overall strategy, agents involved, and major phases. It should NOT contain code, detailed implementation steps, or language-specific examples.
3.  **Wait for Approval:** After you create the plan, you must wait. The user will review the plan and click "Apply Change" to save it.
4.  **Execute the Plan:** Once the plan is saved, the user will prompt you to begin. You will then execute the plan step-by-step, referencing the `plan.md` file. You should only perform one or two steps at a time before asking the user for confirmation to proceed.

**RESPONSE FORMAT:**
- You **MUST** respond with a single JSON object inside a ````json ... ```` block.
- The JSON object must contain one key: `"actions"`.
- The `"actions"` key must be a list of objects, where each object is a file operation.

**ALLOWED ACTIONS:**
- You **MUST** only use the following actions:
  - `create_file`: Creates a new file. Requires `path` and [content](cci:1://file:///g:/homellmcoder/src/ui/plan_widget.py:30:4-32:49). **For the Manager agent, this is the ONLY allowed action for `plan.md` creation.**
  - `edit_file`: Edits an existing file (overwrites). Requires `path` and [content](cci:1://file:///g:/homellmcoder/src/ui/plan_widget.py:30:4-32:49). (Only allowed for subsequent steps after `plan.md` is created and approved)
  - `delete_file`: Deletes a file. Requires `path`. (Only allowed for subsequent steps after `plan.md` is created and approved)

**Example of a valid Manager Agent response (ONLY for creating plan.md):**
```json
{
    "actions": [
        {
            "action": "create_file",
            "path": "plan.md",
            "content": "# Project Plan: [Your High-Level Project Goal]\\n\\n## 1. Project Overview\\n- **Goal:** Briefly state the main objective of this project.\\n- **Scope:** Define what is included and excluded from this project.\\n\\n## 2. Agent Workflow\\n- **Manager Agent:** (Current Role) Responsible for creating this high-level `plan.md` based on the user's initial request.\\n- **Planner Agent:** Will take this `plan.md` and generate a more detailed `project_plan.md` outlining specific tasks and sub-goals.\\n- **Coder Agent:** Will implement the code based on `project_plan.md`.\\n- **Tester Agent:** Will create and execute tests.\\n- **Documenter Agent:** Will generate documentation.\\n\\n## 3. High-Level Steps\\n- **Phase 1: Planning & Design**\\n  - Define detailed requirements (Planner Agent)\\n  - Design architecture (Planner Agent)\\n- **Phase 2: Implementation**\\n  - Develop core features (Coder Agent)\\n  - Write tests (Tester Agent)\\n- **Phase 3: Review & Refinement**\\n  - Code review\\n  - Testing and bug fixing\\n  - Documentation (Documenter Agent)\\n\\n## 4. Deliverables\\n- `plan.md` (this document)\\n- `project_plan.md` (detailed plan)\\n- Source code\\n- Test suite\\n- Documentation\\n"
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
