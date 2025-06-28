import os
import shutil
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeView,
    QMenu,
    QMessageBox,
    QInputDialog,
)
from PyQt6.QtCore import QModelIndex, Qt, QDir, pyqtSignal
from PyQt6.QtGui import QAction, QFileSystemModel


class FileNavigator(QWidget):
    """
    A widget that displays a file system tree view, allowing navigation and interaction.
    """

    file_selected = pyqtSignal(str)
    project_root_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QFileSystemModel()
        self.model.setRootPath("")  # Setting empty root shows computer's drives
        self.model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.AllEntries
        )

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setAnimated(False)
        self.tree.setIndentation(20)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        # Hide all columns except for the name
        for i in range(1, self.model.columnCount()):
            self.tree.hideColumn(i)

        self.tree.doubleClicked.connect(self.on_double_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def on_double_clicked(self, index: QModelIndex):
        path = self.model.filePath(index)
        if not self.model.isDir(index):
            self.file_selected.emit(path)

    def set_root_path(self, path):
        """Sets the root directory for the file navigator's view."""
        self.tree.setRootIndex(self.model.setRootPath(path))

    def open_context_menu(self, position):
        index = self.tree.indexAt(position)
        path = self.model.filePath(index)

        menu = QMenu()

        if self.model.isDir(index):
            set_root_action = QAction("Set as Project Root", self)
            set_root_action.triggered.connect(
                lambda: self.project_root_changed.emit(path)
            )
            menu.addAction(set_root_action)
            menu.addSeparator()

        new_file_action = QAction("New File...", self)
        new_file_action.triggered.connect(
            lambda: self.create_new_file(path)
        )
        menu.addAction(new_file_action)

        new_folder_action = QAction("New Folder...", self)
        new_folder_action.triggered.connect(
            lambda: self.create_new_folder(path)
        )
        menu.addAction(new_folder_action)

        menu.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_item(path))
        menu.addAction(delete_action)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def get_base_path(self, path):
        if self.model.isDir(self.model.index(path)):
            return path
        return os.path.dirname(path)

    def create_new_file(self, path):
        base_path = self.get_base_path(path)
        name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and name:
            file_path = os.path.join(base_path, name)
            if not os.path.exists(file_path):
                try:
                    with open(file_path, "w") as _:
                        pass  # Create an empty file
                except IOError as e:
                    QMessageBox.critical(self, "Error", f"Failed to create file: {e}")
            else:
                QMessageBox.warning(self, "Exists", f"File '{name}' already exists.")

    def create_new_folder(self, path):
        base_path = self.get_base_path(path)
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name:
            folder_path = os.path.join(base_path, name)
            if not os.path.exists(folder_path):
                try:
                    os.makedirs(folder_path)
                except OSError as e:
                    QMessageBox.critical(self, "Error", f"Failed to create folder: {e}")
            else:
                QMessageBox.warning(self, "Exists", f"Folder '{name}' already exists.")

    def delete_item(self, path):
        if not path or not os.path.exists(path):
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete '{os.path.basename(path)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.model.isDir(self.model.index(path)):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except (OSError, IOError) as e:
                QMessageBox.critical(self, "Error", f"Failed to delete item: {e}")
