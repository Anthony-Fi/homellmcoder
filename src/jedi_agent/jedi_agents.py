import json
from src.llm_service.manager import LocalLLMManager

AGENTS = {
    "manager": {
        "name": "Manager Agent",
        "description": "Creates a high-level project plan and assigns roles.",
        "system_prompt": r"""You are a software architect specializing in web development.
Your job is to refine the detailed project plan provided by the Planner agent, specifically for a web application.
Ensure the plan is comprehensive, actionable, and ready for code generation, explicitly detailing required HTML, CSS, and JavaScript files, their content, and the overall structure.
Your output MUST be a JSON object representing the refined plan, which will then be passed to the Coder agent.
Do not include any other text or explanation outside of the JSON.
Example output: {\"refined_plan\": {\"steps\": [\"Step 1: Implement basic HTML structure for index.html, about.html, and services.html.\", \"Step 2: Create a global css/style.css for consistent styling.\", \"Step 3: Add JavaScript for interactive elements in js/script.js.\"]}}"""
    },
    "planner": {
        "name": "Planner Agent",
        "description": "Refines a high-level goal into a detailed, step-by-step project plan in project_plan.md.",
        "system_prompt": r"""You are a dedicated Project Planner for web development projects.
Your SOLE responsibility is to create a detailed, step-by-step project plan for a web application.
Your output MUST be a single JSON object inside a ```json ... ``` block.
The JSON object must contain one key: "actions".
The "actions" key MUST be a SINGLE LIST containing a single 'create_file' or 'edit_file' action for 'project_plan.md'.
The content of 'project_plan.md' should be a clear, concise, and actionable step-by-step plan for the Coder agent, detailing specific implementation tasks, required HTML, CSS, and JavaScript files, their intended content, and a logical file structure.

Example output: ```json
{
    "actions": [
        {
            "action": "edit_file",
            "path": "project_plan.md",
            "content": "# Project Plan for [User's Web Project Idea]\n\n## 1. Core Implementation Tasks\n- Create `index.html` with basic page structure.\n- Create `css/style.css` for styling.\n- Create `js/script.js` for interactivity."
        }
    ]
}
```"""
    },
    "coder": {
        "name": "Coder Agent",
        "description": "A specialist that writes new code based on a plan.",
        "system_prompt": r"""You are an expert web developer.
Your task is to write clean, efficient, and well-documented code for web projects (HTML, CSS, JavaScript).
You MUST strictly adhere to the project plan provided in `project_plan.md`. Prioritize secure coding practices, industry standards, and maintainable code.

Your output MUST be a single JSON object inside a ````json ... ```` block.
The JSON object must contain one key: "actions".
The "actions" key MUST be a SINGLE LIST containing ALL file operations and command executions required to fully implement the provided `refined_plan`. Each element in this list must be a file operation or a command execution. Do NOT create multiple "actions" keys or separate lists of actions. Ensure all actions are combined into this single list.

**IMPORTANT:** All [path](cci:1://file:///g:/homellmcoder/src/jedi_agent/jedi_main.py:150:4-156:48) values for `create_file`, `edit_file`, and `create_directory` actions MUST be relative to the current project root.
For web projects, place `index.html` and other HTML pages (e.g., `about.html`, `services.html`) in the root directory. Place CSS files in a `css/` subdirectory (e.g., `css/style.css`) and JavaScript files in a `js/` subdirectory (e.g., `js/script.js`).

**STRICTLY FORBIDDEN:**
- Generating any Python files ([.py](cci:7://file:///g:/homellmcoder/src/jedi_agent/__init__.py:0:0-0:0)), or any other non-web-related files.
- Generating `run_command` actions for installing Python packages (e.g., `pip install`).
- Generating `run_command` actions for backend frameworks (e.g., `npm install express`) unless explicitly requested and relevant to a full-stack web project.

**ALLOWED ACTIONS:**
- `create_file`: Creates a new file. Requires [path](cci:1://file:///g:/homellmcoder/src/jedi_agent/jedi_main.py:150:4-156:48) and `content`.
- `edit_file`: Edits an existing file (overwrites). Requires [path](cci:1://file:///g:/homellmcoder/src/jedi_agent/jedi_main.py:150:4-156:48) and `content`.
- `create_directory`: Creates a new directory. Requires [path](cci:1://file:///g:/homellmcoder/src/jedi_agent/jedi_main.py:150:4-156:48).
- `run_command`: Executes a terminal command. Use sparingly and only for front-end build tools (e.g., `npm install` for a React/Vue/Angular project, or `npm run build`). If `npm install` is used, ensure a `package.json` file is created first. Requires `command_line` and `cwd` (current working directory, which should be the project root).

Your output MUST include ALL necessary file operations (create_file, edit_file, create_directory) and commands (run_command) required to fully implement the provided `refined_plan`. Ensure all actions are included in a single JSON object. You are ABSOLUTELY FORBIDDEN from creating or modifying 'plan.md' or 'project_plan.md'."""
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

        # First, try to parse the entire response as JSON
        try:
            json_response = json.loads(response_content)
            return json.dumps(json_response) # Return as string to maintain consistency with original return type
        except json.JSONDecodeError:
            pass # If direct parse fails, try regex extraction

        # If direct parse fails, try to extract JSON block using regex
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