from PyQt6.QtCore import QObject, pyqtSignal

class BuilderSignals(QObject):
    log_message = pyqtSignal(str)
    command_output = pyqtSignal(str)
    command_error = pyqtSignal(str)
    command_prompt = pyqtSignal(str, object)  # message, callback
