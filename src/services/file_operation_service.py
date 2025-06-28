import os
import logging
import subprocess


class FileOperationService:
    def execute_actions(self, project_root, actions):
        """Executes a list of file operations."""
        if not project_root or not os.path.isdir(project_root):
            logging.error(f"Invalid project root provided: {project_root}")
            raise ValueError("Invalid project root.")

        for action_data in actions:
            try:
                action_type = action_data.get("action")

                # Handle run_command separately as it doesn't require a path
                if action_type == "run_command":
                    command = action_data.get("command")
                    if not command:
                        raise ValueError("'command' is a required field for run_command.")
                    logging.info(f"Executing command: {command}")
                    try:
                        # Use subprocess.run to execute the command
                        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
                        logging.info(f"Command stdout:\n{result.stdout}")
                        if result.stderr:
                            logging.warning(f"Command stderr:\n{result.stderr}")
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Command failed with error: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
                        raise e
                    except FileNotFoundError:
                        logging.error(f"Command not found: {command.split()[0]}")
                        raise
                    continue # Move to the next action

                # For all other actions, 'path' is required
                path = action_data.get("path")
                if not path:
                    raise ValueError("'path' is a required field for all actions except run_command.")

                full_path = os.path.join(project_root, path)

                if action_type == "create_file":
                    content = action_data.get("content", "")
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    logging.info(f"Created file: {full_path}")

                elif action_type == "edit_file":
                    content = action_data.get("content")
                    if content is None:
                        raise ValueError("'content' is required for edit_file.")
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    logging.info(f"Edited file: {full_path}")

                elif action_type == "delete_file":
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        logging.info(f"Deleted file: {full_path}")
                    else:
                        logging.warning(
                            f"Attempted to delete non-existent file: {full_path}"
                        )

                elif action_type == "create_directory":
                    os.makedirs(full_path, exist_ok=True)
                    logging.info(f"Created directory: {full_path}")

                else:
                    raise ValueError(f"Invalid action type: {action_type}")

                logging.info(f"Action {action_type} on {path} successful.")

            except Exception as e:
                logging.error(f"Failed to execute action {action_data}: {e}")
                raise e

        logging.info("All file operations executed successfully.")

    def read_file(self, project_root: str, path: str) -> str:
        """Reads the content of a file within the project root."""
        full_path = os.path.join(project_root, path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {full_path}")

        if not os.path.isfile(full_path):
            raise IsADirectoryError(f"Path is a directory, not a file: {full_path}")

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            logging.info(f"Successfully read file: {path}")
            return content
        except Exception as e:
            logging.error(f"Error reading file {path}: {e}")
            raise
