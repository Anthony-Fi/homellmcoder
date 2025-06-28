# HomeLLMCoder

HomeLLMCoder is a local-first, AI-powered integrated development environment (IDE) designed for offline, plan-driven software development. It provides a complete toolkit for creating and managing projects with the assistance of a local Large Language Model (LLM), enabling a fully autonomous, agentic workflow from concept to code.

## Features

- 🤖 **Agentic AI Workflow** - Leverage a local LLM to generate, execute, and refine development plans.
- � **Plan-Driven Development** - The AI creates a `plan.md` for each project, which it follows step-by-step.
- �️ **Integrated Development Environment** - A seamless interface with a file navigator, tabbed code editor, and integrated terminal.
- 💬 **Interactive LLM Chat** - Communicate with the AI to create plans, generate code, and manage your project.
- 🔒 **Offline & Secure** - Operates entirely on your local machine, ensuring your code and data remain private.
- 📂 **Project Management** - Easily create new projects, manage files, and switch between different project contexts.
- 🖥️ **Cross-Platform** - Built with PyQt6, aiming for compatibility with Windows, macOS, and Linux.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Git
- [Ollama](https://ollama.com/) running with a downloaded model (e.g., `ollama run llama3.2`)

### Installation & Running

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Anthony-Fi/homellmcoder
    cd homellmcoder
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    # For Windows
    python -m venv .venv
    .venv\Scripts\activate

    # For macOS/Linux
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python -m src.main
    ```

## 🛠 Building a Standalone Executable

To create a single-file executable for distribution:

1.  **Install build dependencies:**
    ```bash
    pip install pyinstaller
    ```

2.  **Run the build script:**
    ```bash
    # Note: The spec file may need adjustments depending on your OS and dependencies.
    pyinstaller HomeLLMCoder.spec
    ```

3.  The distributable will be created in the `dist` directory.

## Project Structure

The project follows a structured, service-oriented architecture:

```
homellmcoder/
├── .venv/              # Python virtual environment
├── docs/               # Documentation files (architecture, user guide, etc.)
├── src/                # Source code for the application
│   ├── __init__.py     # Makes 'src' a package
│   ├── llm_service/    # Logic for interacting with the LLM
│   │   └── manager.py  # Manages LLM connection, prompting, and conversation
│   ├── services/       # Core business logic services
│   │   ├── file_operation_service.py # Handles file system operations
│   │   ├── history_service.py        # Manages chat history persistence
│   │   └── project_service.py        # Manages project root state
│   ├── ui/               # User interface components and widgets
│   │   ├── components/   # Reusable UI widgets (chat bubble, status indicator)
│   │   ├── main_window.py# The main application window and layout
│   │   ├── file_navigator.py
│   │   ├── code_editor.py
│   │   ├── terminal_widget.py
│   │   └── chat_widget.py
│   └── main.py         # Main entry point to launch the application
├── tests/              # Test files
├── .gitignore          # Git ignore file
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## � Contributing

Contributions are welcome! Please feel free to fork the repository, make your changes, and open a pull request.

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/YourAmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/YourAmazingFeature`).
5.  Open a Pull Request.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
