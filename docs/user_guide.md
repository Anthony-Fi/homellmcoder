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
6.  **Execute with Specialist Agents:** Use the other specialist agents, like the `Coder Agent` or `Docs Agent`, to execute the steps provided in the `project_plan.md`. The `Coder Agent` is now capable of executing terminal commands (e.g., `pip install`, `npm install`, `composer create-project`), creating directories, and creating/editing code files directly from the plan. (Note: The Coder agent is strictly enforced to *not* modify `plan.md` or `project_plan.md`.) Each agent's proposed actions will be presented for your review with an "Apply Changes" button.

## Chatting with the AI

-   **Select a Model:** Use the dropdown menu at the top of the chat panel to select the LLM you want to use.
-   **Enter Your Prompt:** Type your message in the input box at the bottom and press Enter.
-   **View the Conversation:** The conversation is displayed in the main chat area, with your messages on the right and the AI's responses on the left.
