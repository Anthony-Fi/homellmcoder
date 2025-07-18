import json
import re
import logging
import re
from src.llm_service.manager import LocalLLMManager
from src.jedi_agent.json_repair_service import extract_and_repair_json

# Helper function to sanitize string values within JSON
def _escape_json_string_value(s):
    # Replace common invalid escape sequences and control characters
    # This is a heuristic and might need further refinement based on LLM output patterns
    s = s.replace('\\n', '\n')  # Replace literal \n with actual newline
    s = s.replace('\\t', '\t')  # Replace literal \t with actual tab
    s = s.replace('\\r', '\r')  # Replace literal \r with actual carriage return

    # Handle unescaped backslashes that are not part of a valid escape sequence
    s = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', s)

    # Escape all standard JSON control characters that might appear unescaped
    s = s.replace('\n', '\\n')
    s = s.replace('\t', '\\t')
    s = s.replace('\r', '\\r')
    s = s.replace('\f', '\\f')
    s = s.replace('\b', '\\b')

    # Remove any other invalid control characters (0x00-0x1f, excluding tab, newline, carriage return, form feed, backspace)
    # Remove any other invalid control characters (0x00-0x1f)
    # Encode to UTF-8 and then decode to ASCII with xmlcharrefreplace to handle problematic characters
    # This converts characters that cannot be represented in ASCII to XML character references (e.g., &#123;)
    # which are valid within JSON strings.
    s = s.encode('utf-8', 'xmlcharrefreplace').decode('ascii')
    return s

AGENTS = {
    "fixer": {
        "name": "Fixer Agent",
        "description": "Repairs or rewrites outputs to ensure valid JSON with an actions list.",
        "system_prompt": r"""
You are a Fixer Agent. Your job is to repair or rewrite agent outputs that are not valid JSON.
You will receive:
- The original plan or instructions.
- The broken or malformed output.
- Any error messages or context.

Your output must be a single valid JSON object with an 'actions' list containing all required steps.
Do not include any text, explanations, or markdown outside the JSON.
If you must reconstruct missing actions, do so based on the plan and context.
"""
    },
    "manager": {
        "name": "Manager Agent",
        "description": "Creates a high-level project plan and assigns roles.",
        "system_prompt": r"""You are a software architect specializing in web development.
Your job is to refine the detailed project plan provided by the Planner agent, specifically for a web application.
Ensure the plan is comprehensive, actionable, and ready for code generation, explicitly detailing required HTML, CSS, and JavaScript files, their content (using `\\n` for newlines and properly escaping other special characters for JSON validity), and the overall structure.
Your output MUST be a JSON object representing the refined plan, which will then be passed to the Coder agent.
Do not include any other text or explanation outside of the JSON.
Example output: {\"refined_plan\": {\"steps\": [\"Step 1: Create index.html\", \"Step 2: Create style.css\", \"Step 3: Create script.js\"]}}"""
    },
    "planner": {
        "name": "Planner Agent",
        "description": "Refines a high-level goal into a detailed, step-by-step project plan in project_plan.md.",
        "system_prompt": r"""
You are an expert project planner for automated web application generation.

Your mission is to generate a step-by-step JSON plan that:
1. Create the main project directory (e.g., `my_project/`) using a `create_directory` action.
2. For Laravel projects, this MUST include a `run_command` action for `composer create-project laravel/laravel <project_name>` (e.g., `composer create-project laravel/laravel my_laravel_app`), ensuring the `cwd` is set to the parent directory where the project should be created (e.g., `.` or `laravel/`). For other frameworks, include the appropriate scaffolding `run_command`.
2. Immediately implements the main requested features in the scaffolded app using additional actions (e.g., create_file, edit_file, run_command).
3. Ensures the generated app is runnable and includes basic UI to demonstrate the requested features.
4. Avoids placeholder text or vague steps—each step must result in a concrete file or code change.
5. Before executing each step, analyze the planned action and proactively predict any likely requirements (such as PHP extensions, system packages, or environment variables). If any are missing, add installation or enablement steps to the plan before the affected action.
6. If any step fails during execution, analyze the error message and update the plan to resolve the issue. Suggest installation commands, alternative packages, or code changes as needed. Always output the updated plan as a single JSON object.
7. If the user requests QR code scanning and map plotting, your plan MUST include:
    - Installation of any required QR code and mapping packages (with `run_command`).
    - Creation of controllers, routes, and views to scan QR codes, store/track them, and plot them on a map (e.g., using Leaflet.js or Google Maps in the Laravel Blade template).
    - A basic UI to interact with these features.
8. Your output MUST be a single JSON object inside a ```json ... ``` block, with an `actions` list containing ALL file and command operations.
9. Do NOT include any text, explanations, or Markdown outside the JSON block.

Example output:
```json
{
  "actions": [
    {"action": "run_command", "command_line": "composer create-project laravel/laravel my-laravel-app"},
    {"action": "run_command", "cwd": "my-laravel-app", "command_line": "composer require simplesoftwareio/simple-qrcode"},
    {"action": "run_command", "cwd": "my-laravel-app", "command_line": "composer require guzzlehttp/guzzle"},
    {"action": "create_file", "path": "my-laravel-app/routes/web.php", "content": "// Laravel routes for QR and map features..."},
    {"action": "create_file", "path": "my-laravel-app/app/Http/Controllers/QRCodeController.php", "content": "// PHP controller for QR code scanning and tracking..."},
    {"action": "create_file", "path": "my-laravel-app/resources/views/map.blade.php", "content": "<!-- Blade template with Leaflet.js map and QR code UI -->"}
  ]
}
```

If you do not know how to implement a requested feature, still create a stub file and add a TODO comment explaining what should go there.
""",
    },

    "coder": {
        "name": "Coder Agent",
        "description": "A specialist that writes new code based on a plan.",
        "system_prompt": r"""You are an expert web developer. Your task is to write clean, efficient, and well-documented code for web projects (HTML, CSS, JavaScript). You MUST strictly adhere to the project plan provided in `project_plan.md`. Prioritize secure coding practices, industry standards, and maintainable code.

Your output MUST be a single JSON object inside a ````json ... ```` block. Do not include any other text or explanation outside of the JSON. If you output anything other than valid JSON, your response will be considered invalid and discarded, leading to system failure. Always output only the JSON.
The JSON object must contain one key: "actions". The "actions" key MUST be a SINGLE LIST containing ALL file operations and command executions required to fully implement the provided `refined_plan`. Each element in this list must be a file operation or a command execution. Do NOT create multiple "actions" keys or separate lists of actions. Ensure all actions are combined into this single list.

**IMPORTANT:** All path values for `create_file`, `edit_file`, and `create_directory` actions MUST be relative to the current project root. For web projects, place `index.html` and other HTML pages in the root directory. Place CSS files in a `css/` subdirectory and JavaScript files in a `js/` subdirectory.

**STRICTLY FORBIDDEN:** - Generating any Python files or any other non-web-related files. - Generating `run_command` actions for installing Python packages. - Generating `run_command` actions for backend frameworks. - Generating `run_command` actions like `composer install`, `composer create-project`, or `php artisan setup` for initial Laravel project creation.

**ALLOWED ACTIONS:** - `create_file`: Requires path and content. - `edit_file`: Requires path and content. - `create_directory`: Requires path. - `run_command`: Requires command_line and cwd. Use sparingly and only for front-end build tools.""",
    },
}


class BaseAgent:
    def __init__(self, llm_manager: LocalLLMManager, llm_name: str, agent_type: str):
        self.llm_manager = llm_manager
        self.llm_name = llm_name
        self.agent_config = AGENTS.get(agent_type)
        if not self.agent_config:
            raise ValueError(
                f"Agent type '{agent_type}' not found in AGENTS configuration."
            )
        self.agent_type = agent_type
        self.system_prompt = self.agent_config["system_prompt"]

    def _get_response(self, messages: list):
        # Ensure the model is loaded for this specific agent's LLM
        if self.llm_manager.loaded_model != self.llm_name:
            if not self.llm_manager.load_model(self.llm_name):
                raise RuntimeError(f"Failed to load LLM model: {self.llm_name}")
        
        full_messages = [{
            "role": "system",
            "content": self.system_prompt
        }]
        full_messages.extend(messages)
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            response_content = ""
            for chunk in self.llm_manager.stream_chat(full_messages):
                if "message" in chunk and "content" in chunk["message"]:
                    response_content += chunk["message"]["content"]
            
            logging.debug(f"Raw LLM response from {self.llm_name} on attempt {attempt+1}:\n{response_content}")
            
            parsed_data = extract_and_repair_json(response_content)
            if isinstance(parsed_data, dict) and 'error' not in parsed_data and parsed_data is not None:
                logging.debug(f"Successfully parsed JSON on attempt {attempt+1}")
                return parsed_data
            else:
                logging.error(f"JSON parsing failed on attempt {attempt+1}: {parsed_data.get('error', 'Unknown error')}")
                if attempt < max_retries:
                    # Re-prompt with a strict instruction for JSON output
                    retry_message = {"role": "user", "content": "Your response was not in valid JSON format. Please output ONLY a valid JSON object as per the system prompt. No markdown, explanations, or other text."}
                    full_messages.append(retry_message)
                else:
                    logging.error("Max retries reached for JSON parsing.")
                    return {"error": "Failed to get valid JSON after multiple attempts"}
        return {"error": "Unexpected end of retries"}

    def execute(self, user_request: str):
        messages = [{"role": "user", "content": user_request}]
        response = self._get_response(messages)
        # _get_response now returns a parsed dictionary, so no need for json.loads()
        if response and not response.get("error"):
            return response
        else:
            print(
                f"Warning: Planner Agent did not return valid JSON: {response.get('raw_response', 'N/A')}"
            )
            return {
                "error": "Invalid JSON response",
                "raw_response": response.get("raw_response", "N/A"),
            }


class PlannerAgent(BaseAgent):
    def __init__(self, llm_manager: LocalLLMManager, llm_name: str):
        super().__init__(llm_manager, llm_name, "planner")

    def execute(self, user_request: str):
        messages = [{"role": "user", "content": user_request}]
        response = self._get_response(messages)
        # _get_response now returns a parsed dictionary, so no need for json.loads()
        if response and not response.get("error"):
            return response
        else:
            print(
                f"Warning: Planner Agent did not return valid JSON: {response.get('raw_response', 'N/A')}"
            )
            return {
                "error": "Invalid JSON response",
                "raw_response": response.get("raw_response", "N/A"),
            }


class ManagerAgent(BaseAgent):
    def __init__(self, llm_manager: LocalLLMManager, llm_name: str):
        super().__init__(llm_manager, llm_name, "manager")

    def execute(self, current_plan: dict):
        # Manager agent might refine the plan or ask clarifying questions
        # For now, let's just pass the plan through and simulate refinement
        messages = [
            {
                "role": "user",
                "content": f"Refine the following plan: {json.dumps(current_plan)}",
            }
        ]
        response = self._get_response(messages)
        # _get_response now returns a parsed dictionary, so no need for json.loads()
        if response and not response.get("error"):
            return response
        else:
            print(
                f"Warning: Manager Agent did not return valid JSON: {response.get('raw_response', 'N/A')}"
            )
            return {
                "error": "Invalid JSON response",
                "raw_response": response.get("raw_response", "N/A"),
            }


class CoderAgent(BaseAgent):
    def __init__(self, llm_manager: LocalLLMManager, llm_name: str):
        super().__init__(llm_manager, llm_name, "coder")

    def execute(self, plan_actions: dict):
        messages = [
            {
                "role": "user",
                "content": f"Generate code based on the following plan: {json.dumps(plan_actions)}"
            }
        ]
        response = self._get_response(messages)
        if isinstance(response, dict) and "actions" in response and isinstance(response["actions"], list):
            valid_actions = []
            for action in response["actions"]:
                if action.get("action") in ["create_file", "edit_file"] and "content" not  in action:
                    logging.error(f"Invalid action: missing 'content' for action type {action.get('action')}")
                    return {"error": f"Invalid action structure: missing 'content' for {action.get('action')}", "raw_response": response}
                elif action.get("action") in ["run_command"] and "command_line" not in action:
                    logging.error(f"Invalid action: missing 'command_line' for run_command")
                    return {"error": f"Invalid action structure: missing 'command_line' for run_command", "raw_response": response}
                else:
                    valid_actions.append(action)
            return {"actions": valid_actions}
        else:
            logging.error(f"Coder Agent did not return expected structure: {response}")
            return {"error": "Invalid response structure from Coder Agent", "raw_response": response}
