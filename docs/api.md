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

Executes a shell command.

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
