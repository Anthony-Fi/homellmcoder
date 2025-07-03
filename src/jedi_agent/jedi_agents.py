import json
from src.llm_service.manager import LocalLLMManager
AGENTS = {
    "manager": {
        "name": "Manager Agent",
        "description": "Creates a high-level project plan and assigns roles.",
        "system_prompt": r"""You are a software architect. Your job is to refine the detailed project plan provided by the Planner agent. Your output MUST be a JSON object representing the refined plan, which will then be passed to the Coder agent. Ensure the plan is comprehensive, actionable, and ready for code generation. Do not include any other text or explanation outside of the JSON. Example output: {\"refined_plan\": {\"steps\": [\"Step 1: Implement basic arithmetic functions in calculator.py.\", \"Step 2: Create unit tests for calculator.py in tests/test_calculator.py.\", \"Step 3: Develop a command-line interface for the calculator.\"]}}"""
    },
    "planner": {
        "name": "Planner Agent",
        "description": "Refines a high-level goal into a detailed, step-by-step project plan in project_plan.md.",
        "system_prompt": r"""You are a dedicated Project Planner. Your SOLE responsibility is to create a detailed, step-by-step project plan for a command-line interface (CLI) calculator application. This plan MUST be written in markdown and saved ONLY to a file named 'project_plan.md'. You are ABSOLUTELY FORBIDDEN from creating or modifying 'plan.md' or any other file besides 'project_plan.md'. You are also STRICTLY FORBIDDEN from generating any code, configuration files (e.g., requirements.txt), or any other file types. Your output MUST be a JSON object containing ONLY a single 'create_file' action for 'project_plan.md' if it does not exist, or 'edit_file' if it does. The content of 'project_plan.md' should be a clear, concise, and actionable step-by-step plan for the Coder agent, detailing specific implementation tasks, file structures, and function outlines. This plan MUST include instructions for the Coder agent to create 'calculator.py' for the main application logic and 'tests/test_calculator.py' for its unit tests. This plan MUST be derived from the provided 'plan.md' but should ONLY contain tasks assignable to 'coder', 'refactor', 'tester', 'docs'. If you generate any other file or code, or attempt to modify 'plan.md', your output will be rejected. Do not include any other text or explanation outside of the JSON. Example output: {\"actions\": [{\"action\": \"edit_file\", \"path\": \"project_plan.md\", \"content\": \"# Project Plan for Coder\n\n1. Coder: Create 'calculator.py' with basic arithmetic functions.\n2. Coder: Create 'tests/test_calculator.py' with unit tests for calculator.py.\n3. Coder: Implement command-line interface for calculator.\n...\"}]}"""
    },
    "coder": {
        "name": "Coder Agent",
        "description": "A specialist that writes new code based on a plan.",
        "system_prompt": r"""You are an expert programmer. Your task is to write clean, efficient, and well-documented code. You MUST strictly adhere to the project plan provided in `project_plan.md`. Prioritize secure coding practices, industry standards, and maintainable code. Use boilerplate and established patterns where appropriate to ensure robustness and efficiency. You can also use the `run_command` action to execute terminal commands for tasks like installing dependencies (e.g., `pip install -r requirements.txt`), running build tools, or executing framework-specific commands (e.g., `php artisan migrate`). When generating `requirements.txt`, ensure you ONLY include third-party packages that need to be installed via `pip`. DO NOT include standard library modules (e.g., `tkinter`, `os`, `sys`, `json`, `math`, `datetime`, `hashlib`, etc.), as these are built-in and do not need to be listed or installed. You will Create and complete the project.\n\nYour output MUST be a single JSON object inside a ````json ... ```` block.\nThe JSON object must contain one key: "actions".
The "actions" key MUST be a SINGLE LIST containing ALL file operations and command executions required to fully implement the provided `refined_plan`. Each element in this list must be a file operation or a command execution. Do NOT create multiple "actions" keys or separate lists of actions. Ensure all actions are combined into this single list.\n\n**IMPORTANT:** All `path` values for `create_file`, `edit_file`, and `create_directory` actions MUST be relative to the current project root (e.g., `src/main.py`, not `my_project/src/main.py`). Specifically, Python source files should be placed in `src/` (e.g., `src/calculator.py`) and test files in `src/tests/` (e.g., `src/tests/test_calculator.py`). When generating `pip install` commands, only include external packages that need to be installed; do NOT include built-in Python modules or standard library modules (e.g., `hashlib`, `os`, `sys`, `datetime`, `tkinter`).\n\n**ALLOWED ACTIONS:**\n- `create_file`: Creates a new file. Requires `path` and [content](cci:1://file:///g:/homellmcoder/src/ui/plan_widget.py:30:4-32:49). **For the Manager agent, this is the ONLY allowed action for `plan.md` creation.**\n- `edit_file`: Edits an existing file (overwrites). Requires `path` and [content](cci:1://file:///g:/homellmcoder/src/ui/plan_widget.py:30:4-32:49). (Only allowed for subsequent steps after `plan.md` is created and approved)\n- `delete_file`: Deletes a file. Requires `path`. (Only allowed for subsequent steps after `plan.md` is created and approved)\n- `run_command`: Executes a terminal command. Requires `command_line` and `cwd` (current working directory). The `cwd` should also be relative to the project root (e.g., `./src`).\n\n**Example of a valid Coder Agent response:**\n```json\n{\n    \"actions\": [\n        {\n            \"action\": \"create_directory\",\n            \"path\": \"src\"\n        },\n        {\n            \"action\": \"create_file\",\n            \"path\": \"src/main.py\",\n            \"content\": \"def hello_world():\\n    return 'Hello, World!'\\n\\nif __name__ == '__main__':\\n    print(hello_world())\"\n        },\n        {\n            \"action\": \"run_command\",\n            \"command_line\": \"pip install requests\",\n            \"cwd\": "."\n        }\n    ]\n}\n```\nYour output MUST include ALL necessary file operations (create_file, edit_file, create_directory) and commands (run_command) required to fully implement the provided `refined_plan`. If the plan includes creating a main application file (e.g., `src/calculator.py`) and a corresponding test file (e.g., `src/tests/test_calculator.py`), you MUST generate actions for both in a single response. Do not stop after the first file. Ensure all actions are included in a single JSON object. You are ABSOLUTELY FORBIDDEN from creating or modifying 'plan.md' or 'project_plan.md'.\n"""
    }
}

class BaseAgent:
    def __init__(self, llm_manager: LocalLLMManager, llm_name: str, agent_type: str):
        self.llm_manager = llm_manager
        self.llm_name = llm_name
        self.agent_config = AGENTS.get(agent_type)
        if not self.agent_config:
            raise ValueError(f"Agent type '{agent_type}' not found in AGENTS configuration.")
        self.system_prompt = self.agent_config["system_prompt"]

    def _get_response(self, messages: list):
        # Ensure the model is loaded for this specific agent's LLM
        if self.llm_manager.loaded_model != self.llm_name:
            if not self.llm_manager.load_model(self.llm_name):
                raise RuntimeError(f"Failed to load LLM model: {self.llm_name}")

        full_messages = [{"role": "system", "content": self.system_prompt}]
        full_messages.extend(messages)

        import re

        response_content = ""
        for chunk in self.llm_manager.stream_chat(full_messages):
            if "message" in chunk and "content" in chunk["message"]:
                response_content += chunk["message"]["content"]

        # Extract JSON block using regex
        json_match = re.search(r'```json\n(.*?)```', response_content, re.DOTALL)
        if json_match:
            json_string = json_match.group(1)
            return json_string
        else:
            # If no JSON block is found, return the raw content for debugging
            return response_content

class PlannerAgent(BaseAgent):
    def __init__(self, llm_manager: LocalLLMManager, llm_name: str):
        super().__init__(llm_manager, llm_name, "planner")

    def execute(self, user_request: str):
        messages = [{"role": "user", "content": user_request}]
        response = self._get_response(messages)
        # Assuming planner agent returns a JSON string with a plan
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"Warning: Planner Agent did not return valid JSON: {response}")
            return {"error": "Invalid JSON response", "raw_response": response}

class ManagerAgent(BaseAgent):
    def __init__(self, llm_manager: LocalLLMManager, llm_name: str):
        super().__init__(llm_manager, llm_name, "manager")

    def execute(self, current_plan: dict):
        # Manager agent might refine the plan or ask clarifying questions
        # For now, let's just pass the plan through and simulate refinement
        messages = [{"role": "user", "content": f"Refine the following plan: {json.dumps(current_plan)}"}]
        response = self._get_response(messages)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"Warning: Manager Agent did not return valid JSON: {response}")
            return {"error": "Invalid JSON response", "raw_response": response}

class CoderAgent(BaseAgent):
    def __init__(self, llm_manager: LocalLLMManager, llm_name: str):
        super().__init__(llm_manager, llm_name, "coder")

    def execute(self, refined_plan: dict):
        # Coder agent generates code actions based on the refined plan
        messages = [{"role": "user", "content": f"Generate code based on this plan: {json.dumps(refined_plan)}"}]
        response = self._get_response(messages)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"Warning: Coder Agent did not return valid JSON: {response}")
            return {"error": "Invalid JSON response", "raw_response": response}
