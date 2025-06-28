import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication # Import QApplication

# Import necessary components from the application
from src.ui.chat_widget import LLMChatWidget
from src.services.file_operation_service import FileOperationService
from src.llm_service.manager import LocalLLMManager
from src.agents import AGENTS

class TestAgentWorkflow:
    @pytest.fixture
    def temp_project_dir(self):
        """Creates a temporary directory for each test run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def chat_widget(self, temp_project_dir):
        """Fixture to provide an initialized LLMChatWidget for testing."""
        # Ensure QApplication is initialized for PyQt widgets
        if QApplication.instance() is None:
            app = QApplication([])
        else:
            app = QApplication.instance()

        # Mock LLMManager as we don't need a real LLM for this test
        with patch('src.llm_service.manager.ollama.Client') as MockOllamaClient:
            mock_ollama_instance = MockOllamaClient.return_value
            # Configure mock_ollama_instance if needed, e.g., for list() or show() methods
            mock_llm_manager = MagicMock(spec=LocalLLMManager)
            mock_llm_manager.loaded_model = True # Simulate a loaded model

            # Instantiate FileOperationService
            file_op_service = FileOperationService()

            # Instantiate LLMChatWidget
            widget = LLMChatWidget(mock_llm_manager, file_operation_service=file_op_service)
            widget.set_project_root(temp_project_dir)
            
            # Mock the thread attribute to prevent AttributeError during simulated worker finish
            widget.thread = MagicMock()
            widget.thread.quit.return_value = None # Ensure quit doesn't do anything

            # Mock the worker attribute to prevent AttributeError when deleteLater is called
            widget.worker = MagicMock()
            widget.worker.deleteLater.return_value = None # Ensure deleteLater doesn't do anything

            # Hide UI elements that are not relevant for testing backend logic
            widget.hide()

            yield widget

            # Cleanup
            widget.deleteLater()
            # If we created the app, clean it up
            if 'app' in locals() and app is not None and app.instance() is not None:
                app.quit()

    def simulate_agent_response(self, chat_widget, agent_key, user_prompt, llm_response_content):
        """Simulates sending a message and processing an LLM response."""
        # Set the current agent
        chat_widget.current_agent_key = agent_key

        # Simulate user sending a message
        # We need to directly call the internal methods that send the prompt to the worker
        # and then process the worker's finished signal.
        # This bypasses the QThread and actual LLM call.

        # Prepare messages for the worker, including the agent's system prompt
        system_prompt = AGENTS[agent_key]["system_prompt"]
        messages_for_worker = [{"role": "system", "content": system_prompt}] + \
                              chat_widget.conversation_history + \
                              [{"role": "user", "content": user_prompt}]

        # Simulate ChatWorker's response
        chat_widget.current_ai_response = llm_response_content

        # Print the actions for verbosity
        try:
            actions_data = json.loads(llm_response_content)
            if "actions" in actions_data:
                print(f"  {agent_key.capitalize()} Agent proposed actions:")
                for action in actions_data["actions"]:
                    action_type = action.get("action", "unknown")
                    path = action.get("path", "N/A")
                    print(f"    - {action_type}: {path}")
        except json.JSONDecodeError:
            print(f"  {agent_key.capitalize()} Agent response was not valid JSON.")

        chat_widget._on_worker_finished() # Directly call the processing method

        # If actions were proposed, apply them
        if chat_widget.pending_actions:
            chat_widget._apply_pending_changes()
            chat_widget.pending_actions = None # Clear pending actions after applying

    def test_end_to_end_workflow(self, chat_widget, temp_project_dir):
        """
        Tests the full Manager -> Planner -> Coder workflow.
        """
        print("\n--- Starting end-to-end workflow test ---")
        # --- Step 1: Manager Agent creates plan.md ---
        manager_user_prompt = "Create a high-level project plan for a 'Hello World' application."
        manager_llm_response_content = json.dumps({
            "actions": [
                {
                    "action": "create_file",
                    "path": "plan.md",
                    "content": "# Project: Hello World App\n\n## Overview\n- Create a simple 'Hello World' application.\n"
                }
            ]
        })
        self.simulate_agent_response(chat_widget, "manager", manager_user_prompt, manager_llm_response_content)

        plan_md_path = os.path.join(temp_project_dir, "plan.md")
        assert os.path.exists(plan_md_path)
        with open(plan_md_path, "r", encoding="utf-8") as f:
            assert f.read() == json.loads(manager_llm_response_content)["actions"][0]["content"]

        # --- Step 2: Planner Agent reads plan.md and creates project_plan.md ---
        planner_user_prompt = "Based on the plan.md, create a detailed project_plan.md for the 'Hello World' application."
        planner_llm_response_content = json.dumps({
            "actions": [
                {
                    "action": "create_file",
                    "path": "project_plan.md",
                    "content": "# Project Plan: Hello World App\n\n## 1. Goal\nCreate a simple 'Hello World' application.\n\n## 2. Steps\n- Create app.py with 'Hello, World!' print statement.\n- Create an empty requirements.txt file.\n"
                }
            ]
        })
        self.simulate_agent_response(chat_widget, "planner", planner_user_prompt, planner_llm_response_content)

        project_plan_md_path = os.path.join(temp_project_dir, "project_plan.md")
        assert os.path.exists(project_plan_md_path)
        with open(project_plan_md_path, "r", encoding="utf-8") as f:
            assert f.read() == json.loads(planner_llm_response_content)["actions"][0]["content"]

        # --- Step 3: Coder Agent reads project_plan.md and creates app.py and requirements.txt ---
        coder_user_prompt = "Implement the 'Hello World' application based on project_plan.md."
        coder_llm_response_content = json.dumps({
            "actions": [
                {
                    "action": "create_file",
                    "path": "app.py",
                    "content": "print('Hello, World!')\n"
                },
                {
                    "action": "create_file",
                    "path": "requirements.txt",
                    "content": ""
                }
            ]
        })
        self.simulate_agent_response(chat_widget, "coder", coder_user_prompt, coder_llm_response_content)

        # --- Step 4: Verify files are created ---
        assert os.path.exists(os.path.join(temp_project_dir, "app.py"))
        assert os.path.exists(os.path.join(temp_project_dir, "requirements.txt"))

        with open(os.path.join(temp_project_dir, "app.py"), "r") as f:
            content = f.read()
            assert content == "print('Hello, World!')\n"

        print("--- End-to-end workflow test passed ---")


    def test_duplicate_image_finder_workflow(self, chat_widget, temp_project_dir):
        """
        Tests the full Manager -> Planner -> Coder workflow for a Duplicate Image Finder application.
        """
        print("\n--- Starting Duplicate Image Finder workflow test ---")

        # --- Step 1: Manager Agent creates plan.md for Duplicate Image Finder ---
        manager_user_prompt = "Create a high-level project plan for a 'Duplicate Image Finder' application with a GUI, navigation, image viewing, selection, and deletion features."
        manager_llm_response_content = json.dumps({
            "actions": [
                {
                    "action": "create_file",
                    "path": "plan.md",
                    "content": "# Project: Duplicate Image Finder\n\n## Overview\n- Develop a GUI application to find, view, select, and delete duplicate images.\n\n## Key Features\n- GUI for user interaction.\n- Navigation to browse directories.\n- Image viewing capabilities.\n- Selection of duplicate images.\n- Deletion of selected duplicate images.\n\n## High-Level Plan\n1.  Manager creates initial plan.md.\n2.  Planner creates detailed project_plan.md specifying GUI components, image processing logic, and file operations.\n3.  Coder implements GUI, image hashing, and file management.\n4.  Tester verifies functionality.\n"
                }
            ]
        })
        self.simulate_agent_response(chat_widget, "manager", manager_user_prompt, manager_llm_response_content)

        plan_md_path = os.path.join(temp_project_dir, "plan.md")
        assert os.path.exists(plan_md_path)
        with open(plan_md_path, "r", encoding="utf-8") as f:
            assert f.read() == json.loads(manager_llm_response_content)["actions"][0]["content"]

        # --- Step 2: Planner Agent reads plan.md and creates project_plan.md ---
        planner_user_prompt = "Based on the plan.md, create a detailed project_plan.md for the 'Duplicate Image Finder' application."
        planner_llm_response_content = json.dumps({
            "actions": [
                {
                    "action": "create_file",
                    "path": "project_plan.md",
                    "content": "# Project Plan: Duplicate Image Finder (JavaScript)\n\n## 1. Goal\nDevelop a web-based GUI application to find, view, select, and delete duplicate images using JavaScript.\n\n## 2. Architecture\n- **GUI:** HTML, CSS, JavaScript (frontend)\n- **Image Processing:** Client-side image hashing (e.g., using a library like `js-image-hashing` or a simple checksum approach).\n- **File Operations:** JavaScript File API for local file access and deletion (with user confirmation).\n\n## 3. Detailed Steps\n### 3.1 GUI Development\n- Create `index.html`: Main application structure.\n- Create `style.css`: Styling for the application.\n- Create `script.js`: Core application logic, UI interactions.\n\n### 3.2 Image Processing\n- Create `imageHasher.js`: Module for generating image hashes.\n- Create `duplicateFinder.js`: Module to scan directories and identify duplicate images based on hashes.\n\n### 3.3 File Operations\n- Implement functions for safe deletion of selected images using JavaScript File API.\n\n## 4. Environment Setup\n- `package.json`: List necessary npm packages (if any, for development tools or polyfills).\n"
                }
            ]
        })
        self.simulate_agent_response(chat_widget, "planner", planner_user_prompt, planner_llm_response_content)

        project_plan_md_path = os.path.join(temp_project_dir, "project_plan.md")
        assert os.path.exists(project_plan_md_path)
        with open(project_plan_md_path, "r", encoding="utf-8") as f:
            assert f.read() == json.loads(planner_llm_response_content)["actions"][0]["content"]

        # --- Step 3: Coder Agent reads project_plan.md and creates application files ---
        coder_user_prompt = "Implement the 'Duplicate Image Finder' application based on project_plan.md."
        coder_llm_response_content = json.dumps({
            "actions": [
                {
                    "action": "create_file",
                    "path": "index.html",
                    "content": "<!DOCTYPE html>\n<html lang='en'>\n<head>\n    <meta charset='UTF-8'>\n    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n    <title>Duplicate Image Finder</title>\n    <link rel='stylesheet' href='style.css'>\n</head>\n<body>\n    <h1>Duplicate Image Finder</h1>\n    <div id='image-container'></div>\n    <script src='script.js'></script>\n</body>\n</html>\n"
                },
                {
                    "action": "create_file",
                    "path": "style.css",
                    "content": "body {\n    font-family: Arial, sans-serif;\n}\n\n#image-container {\n    width: 80%;\n    margin: 40px auto;\n    text-align: center;\n}\n"
                },
                {
                    "action": "create_file",
                    "path": "script.js",
                    "content": "// script.js\n// Core application logic and UI interactions\n"
                },
                {
                    "action": "create_file",
                    "path": "imageHasher.js",
                    "content": "// imageHasher.js\n// Module for generating image hashes\n"
                },
                {
                    "action": "create_file",
                    "path": "duplicateFinder.js",
                    "content": "// duplicateFinder.js\n// Module to scan directories and identify duplicate images based on hashes\n"
                },
                {
                    "action": "create_file",
                    "path": "package.json",
                    "content": "{}\n"
                }
            ]
        })
        self.simulate_agent_response(chat_widget, "coder", coder_user_prompt, coder_llm_response_content)

        # --- Step 4: Verify files are created and have correct content ---
        expected_files = {
            "index.html": "<!DOCTYPE html>\n<html lang='en'>\n<head>\n    <meta charset='UTF-8'>\n    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n    <title>Duplicate Image Finder</title>\n    <link rel='stylesheet' href='style.css'>\n</head>\n<body>\n    <h1>Duplicate Image Finder</h1>\n    <div id='image-container'></div>\n    <script src='script.js'></script>\n</body>\n</html>\n",
            "style.css": "body {\n    font-family: Arial, sans-serif;\n}\n\n#image-container {\n    width: 80%;\n    margin: 40px auto;\n    text-align: center;\n}\n",
            "script.js": "// script.js\n// Core application logic and UI interactions\n",
            "imageHasher.js": "// imageHasher.js\n// Module for generating image hashes\n",
            "duplicateFinder.js": "// duplicateFinder.js\n// Module to scan directories and identify duplicate images based on hashes\n",
            "package.json": "{}\n"
        }

        for filename, content in expected_files.items():
            file_path = os.path.join(temp_project_dir, filename)
            assert os.path.exists(file_path), f"File {filename} was not created."
            with open(file_path, "r", encoding="utf-8") as f:
                actual_content = f.read()
                assert actual_content == content, f"Content of {filename} does not match.\nExpected:\n{content}\nActual:\n{actual_content}"

        # --- Step 5: Refactorer Agent refactors code ---
        refactorer_user_prompt = "Refactor the existing code for the 'Duplicate Image Finder' application to improve readability and maintainability."
        refactorer_llm_response_content = json.dumps({
            "actions": [
                {
                    "action": "create_file",
                    "path": "__init__.py",
                    "content": "# This makes the directory a Python package."
                },
                {
                    "action": "edit_file",
                    "path": "main.cpp",
                    "content": "#include <iostream>\n\nint main() {\n    std::cout << \"Refactored code\" << std::endl;\n    return 0;\n}\n"
                }
            ]
        })
        self.simulate_agent_response(chat_widget, "refactorer", refactorer_user_prompt, refactorer_llm_response_content)

        init_py_path = os.path.join(temp_project_dir, "__init__.py")
        assert os.path.exists(init_py_path)
        with open(init_py_path, "r", encoding="utf-8") as f:
            assert f.read() == "# This makes the directory a Python package."

        with open(os.path.join(temp_project_dir, "main.cpp"), "r", encoding="utf-8") as f:
            # Check for the refactored content (simple check for now)
            assert "#include <iostream>" in f.read()

        # --- Step 6: Tester Agent creates tests ---
        tester_user_prompt = "Create a basic test file for the 'Duplicate Image Finder' application, focusing on the image hashing functionality."
        tester_llm_response_content = json.dumps({
            "actions": [
                {
                    "action": "create_file",
                    "path": "test_duplicate_finder.cpp",
                    "content": "// test_duplicate_finder.cpp\n#include <cassert>\n#include <iostream>\n#include 'DuplicateFinder.h'\n\nvoid testFindDuplicates() {\n    // This is a placeholder for a real test.\n    // In a real scenario, you'd create dummy image files and assert on the output of DuplicateFinder.\n    std::cout << 'Running testFindDuplicates...' << std::endl;\n    DuplicateFinder finder;\n    // assert(finder.findDuplicates('.').empty()); // Example assertion\n    std::cout << 'testFindDuplicates passed.' << std::endl;\n}\n\nint main() {\n    testFindDuplicates();\n    return 0;\n}\n"
                }
            ]
        })
        self.simulate_agent_response(chat_widget, "tester", tester_user_prompt, tester_llm_response_content)

        test_file_path = os.path.join(temp_project_dir, "test_duplicate_finder.cpp")      
        assert os.path.exists(test_file_path)
        with open(test_file_path, "r", encoding="utf-8") as f:
            assert "// test_duplicate_finder.cpp" in f.read()

        print("--- Duplicate Image Finder workflow test passed (Manager, Planner, Coder, Refactorer, and Tester steps) ---")
