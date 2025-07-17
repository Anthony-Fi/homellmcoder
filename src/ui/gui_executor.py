import subprocess
from PyQt6.QtCore import QThread

class GuiExecutor(QThread):
    def __init__(self, command, cwd, signals):
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.signals = signals

    def run(self):
        self.signals.log_message.emit(f"Running: {self.command} (cwd={self.cwd})")
        try:
            proc = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Read stdout and stderr as the process runs
            while True:
                output = proc.stdout.readline()
                if output:
                    self.signals.command_output.emit(output.rstrip())
                elif proc.poll() is not None:
                    break
            # After process ends, read remaining stderr
            for line in proc.stderr:
                self.signals.command_error.emit(line.rstrip())
            proc.wait()
            if proc.returncode == 0:
                self.signals.log_message.emit(f"Command finished successfully: {self.command}")
            else:
                self.signals.command_error.emit(f"Command failed: {self.command}")
        except Exception as e:
            self.signals.command_error.emit(f"Exception: {e}")
