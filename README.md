# HomeLLMCoder

HomeLLMCoder is a local-first, AI-powered integrated development environment (IDE) designed for offline, plan-driven software development. It provides a complete toolkit for creating and managing projects with the assistance of a local Large Language Model (LLM), enabling a fully autonomous, agentic workflow from concept to code.

## Features

- 🤖 **Agentic AI Workflow** - Leverage a local LLM to generate, execute, and refine development plans.
- 💡 **Plan-Driven Development** - The AI creates a `plan.md` (high-level) and `project_plan.md` (detailed) for each project, which it follows step-by-step.
- 🚀 **Automated Environment Setup & Command Execution** - Agents can now execute terminal commands (e.g., `pip install`, `npm install`), create directories, and manage files for environment setup, dependency installation, and project scaffolding. For Laravel projects, the Coder Agent strictly enforces `laravel new <project_name> --no-interaction` for initial project creation, followed by separate commands for `php artisan key:generate`, `npm install`, and `npm run build`. (Note: Some commands, like `python -m venv venv`, may not produce visible output during execution if successful, as they are often designed to be silent unless an error occurs.)
- ⚔️ **Jedi Automation Agent** - A specialized, isolated workflow for fully automated code generation. It operates independently from the main chat workflow, allowing for programmatic orchestration of multiple LLMs to generate projects into user-selected output directories without manual intervention. It provides a hands-off approach for large-scale code generation tasks, including dynamic subfolder creation, post-generation tasks (like Black formatting and Git initialization), and in-app review of generated files with diff comparison. Ideal for rapid prototyping and automated project scaffolding.
- ⚡ **Live Streaming Terminal Output** - See the real-time output of AI-executed terminal commands directly in the integrated terminal.
- 🔄 **Shared Agent Context** - All specialist agents share a common chat history, allowing for seamless context transfer and collaborative problem-solving.
- 🔒 **Strict Agent Role Enforcement** - Each agent's output is strictly filtered and enforced by the UI to ensure they adhere to their specific roles and prevent unintended actions or file modifications.
- 💻 **Integrated Development Environment** - A seamless interface with a file navigator, tabbed code editor, and integrated terminal.
- 💬 **Interactive LLM Chat** - Communicate with the AI to create plans, generate code, and manage your project.
- 🔒 **Offline & Secure** - Operates entirely on your local machine, ensuring your code and data remain private.
- 📂 **Project Management** - Easily create new projects, manage files, and switch between different project contexts.
- 🖥️ **Cross-Platform** - Built with PyQt6, aiming for compatibility with Windows, macOS, and Linux.

## The Agentic Workflow

HomeLLMCoder uses a team of specialized AI agents to handle your requests. This ensures that each step of the process is handled by an expert.

- **Manager Agent:** The project architect. It takes your high-level goal and creates a `plan.md` file that outlines the high-level project and assigns tasks. Its output is strictly enforced to only create `plan.md`.
- **Planner Agent:** The detail-oriented planner. It takes the `plan.md` and refines it into a detailed, step-by-step execution plan in `project_plan.md`. Its output is strictly enforced to only modify `project_plan.md`.
- **Coder Agent:** The programmer. It writes the code based on the detailed plan. It can execute terminal commands (e.g., `pip install`, `npm install`, `php artisan migrate`), create directories, and create/edit code files. Its output is strictly enforced to prevent any modifications to `plan.md` or `project_plan.md`.
- **Refactor Agent:** The code quality expert. It improves existing code without changing its functionality.
- **QA/Tester Agent:** The quality assurance specialist. It writes tests to ensure the code is bug-free.
- **Docs Agent:** The technical writer. It generates documentation for the code.
- **Jedi Agent:** The autonomous code generator. It orchestrates other agents programmatically to generate entire projects without direct user interaction, focusing on hands-off, isolated code generation. It manages the full lifecycle of project generation, from planning to code creation, and handles output organization and version control within dedicated subfolders.

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

4.  **Install Node.js dependencies (if using frontend features):**
    ```bash
    npm install
    ```

5.  **Run the application:**
    ```bash
    python -m src.main
    ```

---

## 📁 Project Structure

- `src/` – Main Python source code (agents, UI, services)
- `docs/` – Documentation (API reference, user guide, architecture)
- `public/` – Static assets (e.g., `index.html`)
- `tests/` – Test scripts and test data
- `requirements.txt` – Python dependencies
- `package.json` – Node.js dependencies (for frontend assets)
- `plan.md` – High-level project plan (generated by Manager agent)
- `.venv/`, `node_modules/` – (ignored) Virtual environment and node packages

## 📦 Dependencies

### Python (from requirements.txt)
```
# Core Application Dependencies
Flask==3.0.3
numpy==2.0.1
pandas
python-dotenv==1.0.0
requests==2.31.0

# LLM / AI
llama-cpp-python==0.2.27
json_repair

# GUI Framework
PyQt6==6.7.0

# Development Dependencies
pytest==8.2.2
black==24.4.2
flake8==7.1.0
mypy==1.10.0

# Packaging
PyInstaller==6.14.1
```

### Node.js (from package.json)
```
Dependencies:
  express: ^4.18.2
DevDependencies:
  eslint: ^8.56.0
  jest: ^29.7.0
```

## ▶️ How to Run the Generated Project

Depending on your agent-generated project (e.g., Python, Node.js, Laravel), follow these steps:

### For Python Projects
```bash
python -m venv venv
source venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m src.main
```

### For Node.js Projects
```bash
npm install
npm start
```

### For Laravel/PHP Projects
```bash
composer install
php artisan migrate
php artisan serve
```

Refer to the docs/user_guide.md for more detailed instructions and troubleshooting.

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

## 🤝 Contributing

Contributions are welcome! Please feel free to fork the repository, make your changes, and open a pull request.

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/YourAmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/YourAmazingFeature`).
5.  Open a Pull Request.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
