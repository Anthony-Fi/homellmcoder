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
    "manager": {
        "name": "Manager Agent",
        "description": "Creates a high-level project plan and assigns roles.",
        "system_prompt": r"""You are a software architect specializing in web development.
Your job is to refine the detailed project plan provided by the Planner agent, specifically for a web application.
Ensure the plan is comprehensive, actionable, and ready for code generation, explicitly detailing required HTML, CSS, and JavaScript files, their content (using `\\n` for newlines and properly escaping other special characters for JSON validity), and the overall structure.
Your output MUST be a JSON object representing the refined plan, which will then be passed to the Coder agent.
Do not include any other text or explanation outside of the JSON.
Example output: {\"refined_plan\": {\"steps\": [\"Step 1: Create index.html\", \"Step 2: Create style.css\", \"Step 3: Create script.js\"]}}""",
    },
    "planner": {
        "name": "Planner Agent",
        "description": "Refines a high-level goal into a detailed, step-by-step project plan in project_plan.md.",
        "system_prompt": r"""You are a highly experienced project planner and architect. Your role is to create a detailed project plan based on the user's request. This plan will guide the subsequent agents (Manager, Coder, Tester, Documenter) in their tasks.

Your output MUST be a single JSON object inside a ````json ... ```` block. Do not include any other text or explanation outside of the JSON.
The JSON object must contain one key: "actions". The "actions" key MUST be a SINGLE LIST containing ALL file operations required to create the project plan. Each element in this list must be a file operation (e.g., create_file, edit_file).

When the user requests a new Laravel project, your plan MUST include a `run_command` action with `command_line`: `laravel new <project_name>`.

Example output:
````json
{
    "actions": [
        {
            "action": "create_file",
            "path": "project_plan.md",
            "content": "# Project Plan\n\n## 1. Overview\nThis is a sample project plan.\n"
        }
    ]
}
````

Your output MUST include ALL necessary file operations (create_file, edit_file) to create the project plan. You are ABSOLUTELY FORBIDDEN from creating or modifying any files other than 'project_plan.md' or 'plan.md'."""
    },

    "coder": {
        "name": "Coder Agent",
        "description": "A specialist that writes new code based on a plan.",
        "system_prompt": r"""You are an expert web developer.
Your task is to write clean, efficient, and well-documented code for web projects (HTML, CSS, JavaScript).
You MUST strictly adhere to the project plan provided in `project_plan.md`. Prioritize secure coding practices, industry standards, and maintainable code.

Your output MUST be a single JSON object inside a ````json ... ```` block.
Do not include any other text or explanation outside of the JSON.
The JSON object must contain one key: "actions".
The "actions" key MUST be a SINGLE LIST containing ALL file operations and command executions required to fully implement the provided `refined_plan`. Each element in this list must be a file operation or a command execution. Do NOT create multiple "actions" keys or separate lists of actions. Ensure all actions are combined into this single list.

**IMPORTANT:** All [path](cci:1://file:///g:/homellmcoder/src/jedi_agent/jedi_main.py:150:4-156:48) values for `create_file`, `edit_file`, and `create_directory` actions MUST be relative to the current project root.
For web projects, place `index.html` and other HTML pages (e.g., `about.html`, `services.html`) in the root directory. Place CSS files in a `css/` subdirectory (e.g., `css/style.css`) and JavaScript files in a `js/` subdirectory (e.g., `js/script.js`).

**STRICTLY FORBIDDEN:**
- Generating any Python files ([.py](cci:7://file:///g:/homellmcoder/src/jedi_agent/__init__.py:0:0-0:0)), or any other non-web-related files.
- Generating `run_command` actions for installing Python packages (e.g., `pip install`).
- Generating `run_command` actions for backend frameworks (e.g., `npm install express`).
- Generating `run_command` actions like `composer install`, `composer create-project`, or `php artisan setup` for initial Laravel project creation. These are strictly forbidden.


**ALLOWED ACTIONS:**
- `create_file`: Creates a new file. Requires [path](cci:1://file:///g:/homellmcoder/src/jedi_agent/jedi_main.py:150:4-156:48) and `content` (use `\\n` for newlines and `\\"` for double quotes, and properly escape other special characters for JSON validity).
- `edit_file`: Edits an existing file (overwrites). Requires [path](cci:1://file:///g:/homellmcoder/src/jedi_agent/jedi_main.py:150:4-156:48) and `content` (use `\\n` for newlines and `\\"` for double quotes, and properly escape other special characters for JSON validity).
- `create_directory`: Creates a new directory. Requires [path](cci:1://file:///g:/homellmcoder/src/jedi_agent/jedi_main.py:150:4-156:48).
- `run_command`: Executes a terminal command. Use sparingly and only for front-end build tools (e.g., `npm install` for a React/Vue/Angular project, or `npm run build`). If `npm install` is used, ensure a `package.json` file is created first. **For new Laravel projects, you MUST use `laravel new <project_name> --no-interaction` to create the project. This is the ONLY allowed command for initial Laravel project creation. After this, you MUST include separate `run_command` actions for `php artisan key:generate`, `npm install`, and `npm run build` for post-installation setup.** Each `run_command` action requires `command_line` and `cwd` (current working directory, which should be the project root). The key for the command must be `command_line`, not `command`.

Example `create_file` action (for `composer.json`):
```json
{
    "action": "create_file",
    "path": "composer.json",
    "content": "{\\n  \\\"name\\\": \\\"laravel/laravel\\\",\\n  \\\"description\\\": \\\"A Laravel project.\\\",\\n  \\\"type\\\": \\\"project\\\",\\n  \\\"license\\\": \\\"MIT\\\",\\n  \\\"autoload\\\": {\\n    \\\"psr-4\\\": {\\n      \\\"App\\\\\\\\\\\": \\\"app/\\\\\\\\\\\"\\n    }\\n  },\\n  \\\"require\\\": {\\n    \\\"php\\\": \\\"^8.2\\\",\\n    \\\"laravel/framework\\\": \\\"^11.0\\\"\\n  },\\n  \\\"config\\\": {\\n    \\\"optimize-autoloader\\\": true,\\n    \\\"preferred-install\\\": \\\"dist\\\",\\n    \\\"sort-packages\\\": true\\n  }\\n}\\n\"
}
For example, if the refined plan requires a composer.json file with a specific configuration, you should generate a create_file action with the correct content. Make sure to escape any special characters in the content string.

Your output MUST include ALL necessary file operations (create_file, edit_file, create_directory) and commands (run_command) required to fully implement the provided `refined_plan`. Ensure all actions are included in a single JSON object. You are ABSOLUTELY FORBIDDEN from creating or modifying 'plan.md' or 'project_plan.md'.""",
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

        response_content = ""
        for chunk in self.llm_manager.stream_chat(full_messages):
            if "message" in chunk and "content" in chunk["message"]:
                response_content += chunk["message"]["content"]

        logging.debug(f"Raw LLM response from {self.llm_name}:\n{response_content}")

        # Use the new json_repair_service to extract and repair JSON

        parsed_data = extract_and_repair_json(response_content)

        if parsed_data is None:
            logging.error(f"Failed to extract and parse JSON from LLM response: {response_content}")
            return None

        logging.debug(f"Successfully parsed JSON from LLM: {parsed_data}")
        if self.agent_type == "coder":
            logging.debug(f"Coder Agent parsed data: {json.dumps(parsed_data, indent=2)}")
        return parsed_data


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
        # Coder agent generates code actions based on the refined plan
        messages = [
            {
                "role": "user",
                "content": f"Generate code based on the following plan: {json.dumps(plan_actions)}",
            }
        ]
        response = self._get_response(messages)
        # _get_response now returns a parsed dictionary, so no need for json.loads()
        # If the response is a list containing a single dictionary, extract that dictionary
        if isinstance(response, list) and len(response) == 1 and isinstance(response[0], dict):
            response = response[0]

        if isinstance(response, dict) and "actions" in response and isinstance(response["actions"], list):
            processed_actions = []
            laravel_new_found = False
            project_name = ""

            for action in response["actions"]:
                if action.get("action") == "run_command":
                    command_line = action.get("command_line", "").lower()
                    if "laravel new" in command_line and "--no-interaction" in command_line:
                        laravel_new_found = True
                        # Extract project name from the command_line
                        try:
                            project_name = command_line.split('laravel new ')[1].split(' --no-interaction')[0].strip()
                        except IndexError:
                            project_name = "laravel-project" # Default if parsing fails
                        processed_actions.append(action)
                    elif "composer install" in command_line or "composer create-project" in command_line or "php artisan setup" in command_line:
                        logging.warning(f"Forbidden command detected and removed: {command_line}")
                        continue # Skip forbidden commands
                    else:
                        processed_actions.append(action)
                else:
                    processed_actions.append(action)
            
            # If laravel new was found, ensure post-installation steps are present and separate
            if laravel_new_found:
                # Define the required post-installation commands
                required_post_install_commands = [
                    f"cd {project_name} && php artisan key:generate",
                    f"cd {project_name} && npm install",
                    f"cd {project_name} && npm run build"
                ]
                
                # Check if they are already in processed_actions and add if not
                for cmd in required_post_install_commands:
                    if not any(a.get("command_line", "").lower() == cmd.lower() for a in processed_actions):
                        processed_actions.append({
                            "action": "run_command",
                            "command_line": cmd,
                            "cwd": project_name # Use the project name as cwd for these commands
                        })

            response["actions"] = processed_actions
            return response
        else:
            error_message = f"Coder Agent did not return valid JSON or expected 'actions' structure. Response: {response}"
            logging.error(f"Warning: {error_message}")
            return {
                "error": "Invalid JSON response or structure",
                "details": error_message,
                "raw_response": response,
            }
