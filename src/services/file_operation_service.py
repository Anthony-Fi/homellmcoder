import os
import logging


class FileOperationService:
    def execute_actions(self, project_root, actions):
        """Executes a list of file operations."""
        if not project_root or not os.path.isdir(project_root):
            logging.error(f"Invalid project root provided: {project_root}")
            raise ValueError("Invalid project root.")

        for action_data in actions:
            try:
                action_type = action_data.get("action")
                path = action_data.get("path")

                if not path:
                    raise ValueError("'path' is a required field for all actions.")

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

            except Exception as e:
                logging.error(f"Failed to execute action {action_data}: {e}")
                raise e
