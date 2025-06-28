import os
import json
import logging


class HistoryService:
    """Manages loading and saving chat history for projects."""

    def __init__(self):
        pass

    def get_history_path(self, project_root):
        """Constructs the path to the history file for a given project root."""
        return os.path.join(
            project_root, ".homellmcoder", "history", "chat_history.json"
        )

    def load_history(self, project_root):
        """Loads chat history from the project's history file."""
        history_path = self.get_history_path(project_root)
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    logging.info(f"Loaded chat history from {history_path}")
                    return history
            except (IOError, json.JSONDecodeError) as e:
                logging.error(f"Error loading history file {history_path}: {e}")
        return []

    def save_history(self, project_root, history):
        """Saves chat history to the project's history file."""
        history_path = self.get_history_path(project_root)
        history_dir = os.path.dirname(history_path)

        try:
            os.makedirs(history_dir, exist_ok=True)
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
            logging.info(f"Saved chat history to {history_path}")
        except IOError as e:
            logging.error(f"Error saving history file {history_path}: {e}")
