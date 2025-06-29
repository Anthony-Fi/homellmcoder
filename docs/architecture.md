# HomeLLMCoder Architecture

This document provides a high-level overview of the HomeLLMCoder application's architecture. The design emphasizes modularity, extensibility, and a clear separation of concerns.

## Core Philosophy

The application is built around a **plan-driven agentic workflow**. Instead of a single monolithic AI, a team of specialized agents collaborates to achieve a user's goal. This process is orchestrated through a central `project_plan.md` file, which serves as the single source of truth for the project.

## The Agentic Workflow

The workflow begins with the user providing a high-level goal to the `Manager Agent`.

```mermaid
graph TD
    A[User Goal] --> B(Manager Agent);
    B --> C{plan.md}; % Manager Agent's output
    C --> D(Planner Agent);
    D --> E{project_plan.md}; % Planner Agent's output
    E --> F(Coder Agent);
    F --> G{Code / Command Execution}; % Coder Agent's output
    G --> H(QA/Tester Agent);
    H --> I{Tests};
    I --> J(Docs Agent);
    J --> K{Documentation};
```

1.  **Manager Agent:** Acts as the project architect. It receives the user's goal and creates a `plan.md` file, which outlines the high-level project and assigns tasks to other agents. The Manager agent's output is strictly enforced to only allow the creation of `plan.md`.
2.  **Planner Agent:** Reads the `plan.md` file and refines it into a detailed, step-by-step execution plan. The Planner's output is strictly an updated `project_plan.md`. The Planner agent's output is strictly enforced to only allow modifications to `project_plan.md`.
3.  **Specialist Agents (Coder, Refactor, QA/Tester, Docs):** Execute the detailed steps provided by the Planner. The `Coder Agent` can now execute terminal commands (e.g., `pip install`, `npm install`, `composer create-project`), create directories, and create/edit code files directly from the plan. When generating `requirements.txt`, the Coder Agent is now instructed to only include third-party packages, explicitly excluding standard library modules. The output of these `run_command` actions is streamed live to the `TerminalWidget`. The Coder agent's output is strictly enforced to prevent any modifications to `plan.md` or `project_plan.md`. Each agent focuses on its specific area of expertise, ensuring high-quality output.

All specialist agents share a common chat history, allowing for seamless context transfer and collaboration throughout the workflow.

## Main Components

-   **`main.py`**: The application's entry point.
-   **`src/`**: The main source code directory.
    -   **`ui/`**: Contains all PyQt6 UI components, including `MainWindow`, `ChatWidget`, `PlanWidget`, and `TerminalWidget`. The `TerminalWidget` now includes robust shell detection (e.g., PowerShell, CMD, Bash) and adapts virtual environment activation commands accordingly. It also handles `run_command` execution with live streaming of output.
    -   **`llm_service/`**: Manages interaction with the local LLM. This is where the agents and their system prompts are defined.
    -   **`services/`**: Provides core application services, such as `FileOperationService` and `HistoryService`.

## Communication

Communication between the UI and the backend services is handled through a combination of direct method calls and Qt's signal and slot mechanism. This ensures a decoupled and maintainable codebase.
