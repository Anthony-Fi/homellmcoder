# HomeLLMCoder API Reference

This document provides an API reference for the core services used in the HomeLLMCoder application.

## 1. LocalLLMManager (`src/llm_service/manager.py`)

Handles all communication with the local Ollama instance.

### `__init__(self)`
- Initializes the Ollama client.

### `list_models(self)`
- **Description:** Fetches a list of all models available locally through Ollama.
- **Returns:** `list` - A list of model dictionaries.

### `get_model_details(self, model_name: str)`
- **Description:** Retrieves detailed information about a specific model.
- **Parameters:**
  - `model_name` (str): The name of the model to inspect.
- **Returns:** `dict` - A dictionary containing model details.

### `stream_chat(self, model_name: str, messages: list)`
- **Description:** Sends a chat request to the specified model and streams the response.
- **Parameters:**
  - `model_name` (str): The name of the model to use for the chat.
  - `messages` (list): A list of message dictionaries representing the conversation history.
- **Yields:** `str` - Chunks of the response content as they are received.

## 2. ProjectService (`src/services/project_service.py`)

Manages the state of the currently active project root.

### `set_project_root(self, path: str)`
- **Description:** Sets the active project directory.
- **Parameters:**
  - `path` (str): The absolute path to the project's root folder.

### `get_project_root(self)`
- **Description:** Retrieves the path of the current project root.
- **Returns:** `str` - The absolute path of the project root, or `None` if not set.

## 3. HistoryService (`src/services/history_service.py`)

Handles the loading and saving of chat history for a project.

### `get_history_path(self, project_root: str)`
- **Description:** Constructs the path to the chat history file within a project.
- **Parameters:**
  - `project_root` (str): The root directory of the project.
- **Returns:** `str` - The full path to the `chat_history.json` file.

### `load_history(self, project_root: str)`
- **Description:** Loads the chat history from the project's JSON file.
- **Parameters:**
  - `project_root` (str): The root directory of the project.
- **Returns:** `list` - A list of message dictionaries, or an empty list if the file doesn't exist.

### `save_history(self, project_root: str, history: list)`
- **Description:** Saves the current chat history to the project's JSON file.
- **Parameters:**
  - `project_root` (str): The root directory of the project.
  - `history` (list): The list of message dictionaries to save.

## 4. FileOperationService (`src/services/file_operation_service.py`)

Executes file system operations, such as creating or modifying files.

### `execute_actions(self, project_root: str, actions: list)`
- **Description:** Executes a list of file operations in a transactional manner.
- **Parameters:**
  - `project_root` (str): The absolute path to the project's root directory.
  - `actions` (list): A list of action dictionaries.

#### Action Format

Each action is a dictionary that specifies the operation to perform.

**`create_file`**

Creates a new file with the specified content.

```json
{
    "action": "create_file",
    "path": "path/to/your/file.txt",
    "content": "Your file content here."
}
```

**`edit_file`**

Modifies an existing file with the specified content. If the file does not exist, it will be created.

```json
{
    "action": "edit_file",
    "path": "path/to/your/existing_file.txt",
    "content": "New content for the file."
}
```

**`delete_file`**

Deletes a file.

```json
{
    "action": "delete_file",
    "path": "path/to/your/file.txt"
}
```

**`create_directory`**

Creates a new directory.

```json
{
    "action": "create_directory",
    "path": "path/to/your/new_directory"
}
```

**`run_command`**

Executes a shell command. The output of this command is streamed live to the integrated terminal. The system automatically detects the user's shell environment (e.g., PowerShell, CMD, Bash) and adapts commands, particularly virtual environment activation scripts, for compatibility.

```json
{
    "action": "run_command",
    "command": "echo \"Hello World\""
}
```

### `create_file(self, file_path: str, content: str)`
- **Description:** Creates a new file with the specified content. It also creates any necessary parent directories.
- **Parameters:**
  - `file_path` (str): The absolute path where the file should be created.
  - `content` (str): The content to write to the new file.

## 5. Jedi Agent (`src/jedi_agent/jedi_main.py`)

The Jedi Agent is an autonomous orchestration layer that programmatically controls other agents to generate entire projects without direct user intervention. It provides a hands-off approach for large-scale code generation tasks, managing the full lifecycle from planning to code creation, output organization, and version control.

### `JediWindow`

This class represents the main UI for the Jedi Agent, managing the workflow for automated project generation.

#### `__init__(self, llm_manager, parent=None)`
- **Description:** Initializes the JediWindow, setting up the UI components and connecting signals.
- **Parameters:**
  - `llm_manager`: An instance of `LocalLLMManager` for LLM interactions.
  - `parent`: The parent QWidget.

#### `_setup_ui(self)`
- **Description:** Configures the layout and widgets for the Jedi Agent UI, including project name input, output directory selection, LLM selection, and action buttons.

#### `_connect_signals(self)`
- **Description:** Connects UI element signals to their respective slots, enabling interactive behavior.

#### `_browse_output_directory(self)`
- **Description:** Opens a file dialog to allow the user to select an output directory for generated projects.

#### `_start_orchestration(self)`
- **Description:** Initiates the multi-agent orchestration process based on user input and selected LLMs. This method handles the sequential execution of Planner, Manager, and Coder agents, and manages post-generation tasks like Black formatting and Git initialization.

#### `_open_generated_project_in_explorer(self)`
- **Description:** Opens the selected generated project directory in the system's file explorer.

#### `_show_diff_viewer(self)`
- **Description:** Displays a diff viewer to compare generated files, if applicable.

#### `_update_status(self, message)`
- **Description:** Updates the status bar with progress or error messages during orchestration.

#### `_log_message(self, message)`
- **Description:** Logs messages to the internal text browser for user feedback.

#### `_run_post_generation_tasks(self, output_dir, llm_name)`
- **Description:** Executes post-generation tasks such as Black formatting and Git operations within the generated project directory.

#### `_create_project_subfolder(self, base_output_dir, project_name)`
- **Description:** Creates a uniquely named subfolder for each generated project to prevent overwrites.

#### `_execute_agent_workflow(self, llm_name, user_request, project_output_path)`
- **Description:** Manages the sequential execution of Planner, Manager, and Coder agents for a given LLM and user request, handling their JSON outputs and file operations.

#### `_get_agent_response(self, agent, messages)`
- **Description:** Helper method to get a JSON response from an agent, with retry logic and error handling for invalid JSON.

#### `_process_agent_actions(self, actions, project_output_path)`
- **Description:** Processes the list of actions (create_file, edit_file, run_command) returned by agents, executing them via `FileOperationService`.

#### `_update_llm_progress(self, llm_name, status)`
- **Description:** Updates the progress display for each LLM during orchestration.

#### `_display_generated_projects(self)`
- **Description:** Populates the list of generated projects in the UI, allowing users to select and view them.

#### `_on_project_selected(self)`
- **Description:** Handles the selection of a generated project from the list, updating the UI to show its files.

#### `_view_file_content(self, file_path)`
- **Description:** Displays the content of a selected file in the integrated code viewer.
