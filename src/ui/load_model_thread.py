from PyQt6.QtCore import QThread, pyqtSignal


class LoadModelThread(QThread):
    """A QThread to handle loading the LLM model in the background."""

    finished = pyqtSignal(dict)

    def __init__(self, llm_manager, model_name):
        super().__init__()
        self.llm_manager = llm_manager
        self.model_name = model_name

    def run(self):
        """Executes the model loading process."""
        result = self.llm_manager.load_model(self.model_name)
        self.finished.emit(result)
