import logging


class ProjectService:
    """Manages the application's active project context."""

    def __init__(self):
        self._project_root = None

    def set_project_root(self, path):
        """Sets the active project root directory."""
        logging.info(f"Project root set to: {path}")
        self._project_root = path

    def get_project_root(self):
        """Returns the active project root directory."""
        return self._project_root
