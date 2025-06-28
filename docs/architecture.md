# HomeLLMCoder Architecture Overview

This document provides a high-level overview of the HomeLLMCoder application's architecture.

## Core Principles

- **Modularity:** The application is divided into distinct, reusable components (UI widgets, services) to promote separation of concerns.
- **Responsiveness:** Long-running tasks, such as communicating with the LLM, are performed in a background thread to keep the UI from freezing.
- **Extensibility:** The architecture is designed to be easily extendable with new features.

## Main Components

The application is built using the PyQt6 framework and is composed of several key components:

### 1. Application Entry Point (`src/main.py`)

- Initializes the Qt application.
- Creates the main window (`MainWindow`) and starts the event loop.

### 2. Main Window (`src/ui/main_window.py`)

- **`MainWindow`** is the central class of the application.
- It is responsible for:
  - Creating and assembling all the main UI components using `QSplitter` for a flexible layout.
  - Setting up the main menu bar and status bar.
  - Connecting signals and slots between different components to orchestrate their interactions.

### 3. UI Components (`src/ui/`)

- **`FileNavigator`**: A `QTreeView` combined with a `QFileSystemModel` that displays the file system. It emits signals when a file is selected or when the user sets a new project root.
- **`TabbedCodeEditor`**: A `QTabWidget` that hosts multiple instances of a custom code editor widget. It has a slot to open files provided by the `FileNavigator`.
- **`LLMChatWidget`**: Manages the entire chat interface, including the conversation display, user input, and model selection. It uses a `ChatWorker` to handle LLM communication.
- **`TerminalWidget`**: Integrates a system terminal (like PowerShell on Windows) into the application using `QProcess`.

### 4. Background Worker (`src/ui/components/chat_worker.py`)

- **`ChatWorker`**: A `QObject` that runs on a separate `QThread`. It takes the user's prompt and conversation history, sends the request to the `LLMManager`, and emits signals to update the UI with the response as it streams in. This prevents the UI from becoming unresponsive during LLM inference.

### 5. Services (`src/services/`)

- **`LLMManager`**: Handles all communication with the Ollama REST API. It can list available models, check model details, and stream chat responses.
- **`ProjectService`**: A simple service that tracks the current project root directory.
- **`ChatHistoryService`**: Manages loading and saving the chat history for a project to a JSON file.

## UI Layout

The UI is constructed using nested `QSplitter` widgets:

1.  A main **`QSplitter(Qt.Orientation.Vertical)`** divides the window into a top area and a bottom area.
2.  The **top area** contains a **`QSplitter(Qt.Orientation.Horizontal)`** which creates three columns for the `FileNavigator`, `TabbedCodeEditor`, and `LLMChatWidget`.
3.  The **bottom area** contains the `TerminalWidget`.

This structure allows the user to resize all sections of the UI independently.

## Communication

Communication between components is primarily handled through **PyQt's signal and slot mechanism**. This decouples the components, allowing them to interact without having direct references to each other.

- **Example:** When a user double-clicks a file in the `FileNavigator`, it emits a `file_selected` signal. The `MainWindow` connects this signal to the `open_file` slot of the `TabbedCodeEditor`.
