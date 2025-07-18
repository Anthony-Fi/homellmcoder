# HomeLLMCoder User Guide

Welcome to HomeLLMCoder! This guide will help you get started with the application.

## Setting Up Your Project

1.  **Launch the application.**
2.  Use the **File Navigator** on the left to browse to your project's folder.
3.  **Right-click** on your project's root folder and select **"Set as Project Root"**. This tells HomeLLMCoder where your project is located.

## Using the Agentic Workflow

HomeLLMCoder uses a team of specialized AI agents to help you with your coding tasks. Here's how to use them:

1.  **Select the Manager Agent:** In the chat panel, use the dropdown menu to select the `Manager Agent`.
2.  **Give the Manager a Goal:** In the chat input, describe the high-level goal for your project. For example: `Create a simple Python web server using Flask.`
3.  **Review the Initial Plan (`plan.md`):** The Manager will propose a `plan.md` file in your project's root directory. This file outlines the high-level project and assigns tasks to other agents. Review the proposed `plan.md` in the chat window. If satisfied, click the **"Apply Changes"** button to create the file. (Note: The Manager agent is strictly enforced to only create `plan.md`.)
4.  **Switch to the Planner Agent:** Once `plan.md` is created, switch to the `Planner Agent`. In the chat input, you can prompt the Planner to refine the `plan.md` into a detailed `project_plan.md`. For example: `Refine the plan.md into a detailed project_plan.md.`
5.  **Review the Detailed Project Plan (`project_plan.md`):** The Planner will propose a detailed `project_plan.md`. Review the proposed `project_plan.md` in the chat window. If satisfied, click the **"Apply Changes"** button to update the file. (Note: The Planner agent is strictly enforced to only modify `project_plan.md`.)
6.  **Execute with Specialist Agents:** Use the other specialist agents, like the `Coder Agent` or `Docs Agent`, to execute the steps provided in the `project_plan.md`. The `Coder Agent` is now capable of executing terminal commands (e.g., `pip install`, `npm install`), creating directories, and creating/editing code files directly from the plan. This includes leveraging the enhanced `FixerAgent` which can now robustly identify and modify the correct `php.ini` file on Windows to enable missing PHP extensions (like GD), ensuring smoother Laravel project setup. For Laravel projects, the Coder Agent strictly enforces `laravel new <project_name> --no-interaction` for initial project creation, followed by separate commands for `php artisan key:generate`, `npm install`, and `npm run build`. (Note: The Coder agent is strictly enforced to *not* modify `plan.md` or `project_plan.md`.) Each agent's proposed actions will be presented for your review with an "Apply Changes" button.

### Live Terminal Output
When the AI executes `run_command` actions, the output is streamed live to the integrated terminal, allowing you to see the progress in real-time. Please note that some commands, like `python -m venv venv`, may not produce visible output during execution if successful, as they are often designed to be silent unless an error occurs.

### Improved Logging
Excessive debug logging has been reduced to improve terminal clarity and performance. Logs from internal components like `httpcore` and raw LLM responses are now suppressed, focusing on more relevant information.

### Adaptive Terminal Commands
The integrated terminal now intelligently detects your shell environment (e.g., PowerShell, CMD, Bash) and adapts virtual environment activation commands accordingly. This ensures commands like `venv\Scripts\activate` work correctly across different environments without manual intervention.

## Using the Jedi Automation Agent

The Jedi Automation Agent provides a fully autonomous workflow for generating code projects without direct user interaction. It operates in an isolated environment, making it ideal for large-scale, hands-off code generation tasks. Each generated project is placed in a uniquely named subfolder within your chosen output directory, ensuring no accidental overwrites. This agent now leverages the improved `FixerAgent` for more robust and OS-aware error handling during automated code generation, particularly for environment setup and dependency resolution.

1.  **Launch the Jedi Agent Window:** From the main application, navigate to `Tools` -> `Jedi Automation Agent`.
2.  **Configure Project Details:** In the Jedi Agent window, you can:
    -   Enter a **Project Name** for the new project. This will be used to create a unique subfolder for your generated project.
    -   Select an **Output Directory** where the generated code will be saved. Use the `Browse` button to choose a location.
    -   Choose the **LLM Models** you want the Jedi Agent to use for code generation. You can select multiple models, and the Jedi Agent will run the orchestration for each selected model sequentially.
3.  **Start Code Generation:** Click the `Start Agent` button to begin the automated code generation process. The Jedi Agent will orchestrate the planning, coding, and testing phases autonomously. During this process, it will also perform post-generation tasks such as Black formatting and Git initialization within each generated project's subfolder.
4.  **Review Generated Project:** Once the generation is complete, the Jedi Agent UI will display a list of all generated projects. You can select a project to:
    -   Use the `Open Generated Project` button to view the project in your system's file explorer.
    -   Browse the generated files directly within the Jedi Agent's integrated file viewer.
    -   Use the `Compare Outputs` button to see a detailed diff comparison of the generated code, if multiple LLMs were used or if you are comparing different versions.

## Chatting with the AI

-   **Select a Model:** Use the dropdown menu at the top of the chat panel to select the LLM you want to use.
-   **Enter Your Prompt:** Type your message in the input box at the bottom and press Enter.
-   **View the Conversation:** The conversation is displayed in the main chat area, with your messages on the right and the AI's responses on the left.

---

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
