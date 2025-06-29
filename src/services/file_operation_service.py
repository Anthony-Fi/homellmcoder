import os
import logging
import subprocess
import threading
import queue
from PyQt6.QtCore import QObject, pyqtSignal


class CommandOutputEmitter(QObject):
    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    command_finished = pyqtSignal(int)



class FileOperationService:
    def __init__(self, output_emitter: CommandOutputEmitter = None):
        self.output_emitter = output_emitter

    def execute_actions(self, project_root, actions):
        """Executes a list of file operations."""
        if not project_root or not os.path.isdir(project_root):
            logging.error(f"Invalid project root provided: {project_root}")
            raise ValueError("Invalid project root.")

        for action_data in actions:
            try:
                action_type = action_data.get("action")

                # Handle run_command separately
                if action_type == "run_command":
                    command_line = action_data.get("command_line")
                    if not command_line:
                        raise ValueError("'command_line' is a required field for run_command.")
                    logging.info(f"Executing command: {command_line}")
                    command_cwd = action_data.get("cwd", project_root)
                    if not os.path.isabs(command_cwd):
                        command_cwd = os.path.join(project_root, command_cwd)
                    logging.info(f"Executing command in CWD: {command_cwd}")

                    if self.output_emitter:
                        # Use Popen for streaming output
                        process = subprocess.Popen(
                            command_line,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            cwd=command_cwd
                        )

                        # Start threads to read stdout and stderr
                        def read_stdout(p, emitter):
                            for line in p.stdout:
                                logging.debug(f"Emitting stdout: {line.strip()}")
                                emitter.output_received.emit(line)
                            p.stdout.close()

                        def read_stderr(p, emitter):
                            for line in p.stderr:
                                logging.debug(f"Emitting stderr: {line.strip()}")
                                emitter.error_received.emit(line)
                            p.stderr.close()

                        stdout_thread = threading.Thread(target=read_stdout, args=(process, self.output_emitter))
                        stderr_thread = threading.Thread(target=read_stderr, args=(process, self.output_emitter))

                        stdout_thread.start()
                        stderr_thread.start()

                        # Wait for threads to finish, then for the process to finish
                        stdout_thread.join()
                        stderr_thread.join()
                        exit_code = process.wait()
                        self.output_emitter.command_finished.emit(exit_code)

                        if exit_code != 0:
                            logging.error(f"Command exited with code {exit_code}: {command_line}")
                            raise subprocess.CalledProcessError(exit_code, command_line)
                    else:
                        # Fallback to subprocess.run if no emitter is provided (e.g., for tests)
                        result = subprocess.run(command_line, shell=True, capture_output=True, text=True, check=True, cwd=command_cwd)
                        logging.info(f"Command stdout:\n{result.stdout}")
                        if result.stderr:
                            logging.warning(f"Command stderr:\n{result.stderr}")

                    continue

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
