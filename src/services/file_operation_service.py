import os
import logging
import subprocess
import threading
import queue
from PyQt6.QtCore import QObject, pyqtSignal


# Removed global logging.basicConfig to allow central logging configuration


class CommandOutputEmitter(QObject):
    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    command_finished = pyqtSignal(int)



class FileOperationService:
    def __init__(self, output_emitter: CommandOutputEmitter = None):
        self.output_emitter = output_emitter

    def execute_actions(self, project_root, actions, capture_output=False):
        """Executes a list of file operations. If capture_output is True, returns (success, stdout, stderr) for the last command."""
        if not project_root or not os.path.isdir(project_root):
            logging.error(f"Invalid project root provided: {project_root}")
            raise ValueError("Invalid project root.")

        last_stdout = None
        last_stderr = None
        last_command = None
        for action_data in actions:
            if not isinstance(action_data, dict):
                logging.error(f"Skipping malformed action data: {action_data}. Expected a dictionary, but received {type(action_data).__name__}.")
                continue
            if "action" not in action_data:
                logging.error(f"Skipping malformed action data: {action_data}. Missing 'action' key.")
                continue

            try:
                action_type = action_data.get("action")

                # Handle run_command separately
                if action_type == "run_command":
                    command_line = action_data.get("command_line")
                    if not command_line:
                        raise ValueError("'command_line' is a required field for run_command.")
                    logging.info(f"Executing command: {command_line}")
                    # Force command_cwd to be project_root, ignoring any cwd from action_data
                    command_cwd = project_root
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
                            # No easy way to capture full output here, so just raise
                            raise subprocess.CalledProcessError(exit_code, command_line)
                    else:
                        # Fallback to subprocess.run if no emitter is provided (e.g., for tests)
                        try:
                            process = subprocess.run(command_line, shell=True, capture_output=True, text=True, cwd=command_cwd)
                            last_stdout = process.stdout
                            last_stderr = process.stderr
                            last_command = command_line
                            if process.returncode != 0:
                                logging.error(f"Command exited with code {process.returncode}: {command_line}\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}")
                                if capture_output:
                                    return False, process.stdout, process.stderr, command_line
                                raise subprocess.CalledProcessError(process.returncode, command_line, process.stdout, process.stderr)
                            logging.info(f"Command stdout:\n{process.stdout}")
                            if process.stderr:
                                logging.warning(f"Command stderr:\n{process.stderr}")

                        except subprocess.CalledProcessError as e:
                            stdout = e.stdout
                            stderr = e.stderr
                            success = False
                        except FileNotFoundError:
                            stdout = ""
                            stderr = f"Error: Command not found: {command_line}"
                            success = False
                        except Exception as e:
                            stdout = ""
                            stderr = f"An unexpected error occurred: {e}"
                            success = False

                        return success, stdout, stderr

                    continue

                # For all other actions, 'path' is required
                path = action_data.get("path")
                if not path:
                    logging.error(f"Skipping action {action_type} due to missing 'path' field: {action_data}")
                    continue

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
        if capture_output and last_command is not None:
            return True, last_stdout, last_stderr, last_command

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
