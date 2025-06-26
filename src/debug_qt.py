import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel

print("Attempting to start standalone Qt App...")

app = QApplication(sys.argv)

print("QApplication instance created.")

window = QWidget()
window.setWindowTitle('Standalone Test')
window.setGeometry(100, 100, 280, 80)

helloMsg = QLabel('<h1>Hello, World!</h1>', parent=window)
helloMsg.move(60, 15)

print("Window and label created.")

window.show()

print("window.show() called. Starting event loop...")

exit_code = app.exec()

print(f"Event loop finished with exit code: {exit_code}")

sys.exit(exit_code)
