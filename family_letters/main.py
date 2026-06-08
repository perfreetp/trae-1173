import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QFrame, QSizeGrip
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPainter, QLinearGradient, QColor, QPen

from database import init_db
from windows.archive_overview import ArchiveOverview
from windows.scan_import import ScanImportWindow
from windows.letter_editor import LetterEditor
from windows.relationship import RelationshipWindow
from windows.album import AlbumWindow
from windows.search_borrow import SearchBorrowWindow
from windows.backup_handover import BackupHandoverWindow


NAV_ITEMS = [
    ("档案总览", "📋"),
    ("扫描导入", "📷"),
    ("信件编辑", "✏️"),
    ("人物关系", "👨‍👩‍👧‍👦"),
    ("专题相册", "🖼️"),
    ("检索借阅", "🔍"),
    ("备份交接", "💾"),
]


class NavButton(QPushButton):
    clicked_index = pyqtSignal(int)

    def __init__(self, text, icon_str, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.icon_str = icon_str
        self.text_str = text
        self._active = False
        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        self.setText(f"  {icon_str}  {text}")
        self.clicked.connect(lambda: self.clicked_index.emit(self.index))
        self._update_style()

    def set_active(self, active):
        self._active = active
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet("""
                NavButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #E07A5F, stop:1 #D4684A);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 20px;
                    font-size: 15px;
                    font-weight: bold;
                }
            """)
        else:
            self.setStyleSheet("""
                NavButton {
                    background: transparent;
                    color: #C0C0D0;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 20px;
                    font-size: 14px;
                }
                NavButton:hover {
                    background: rgba(255, 255, 255, 30);
                    color: #FFFFFF;
                }
            """)


class SidebarWidget(QWidget):
    nav_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.buttons = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(6)

        title_label = QLabel("  🏠 家书收藏平台")
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #F2CC8F;
            padding: 16px 8px 24px 8px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,40); max-height: 1px; margin: 4px 8px 16px 8px;")
        layout.addWidget(sep)

        for i, (text, icon_str) in enumerate(NAV_ITEMS):
            btn = NavButton(text, icon_str, i)
            btn.clicked_index.connect(self._on_nav)
            self.buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        ver_label = QLabel("  v1.0.0")
        ver_label.setStyleSheet("color: #606080; font-size: 11px; padding: 8px;")
        ver_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver_label)

        if self.buttons:
            self.buttons[0].set_active(True)

    def _on_nav(self, index):
        for btn in self.buttons:
            btn.set_active(btn.index == index)
        self.nav_changed.emit(index)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("家书收藏平台")
        self.setMinimumSize(QSize(1200, 800))
        self.resize(1400, 900)
        self._setup_ui()
        self._apply_global_style()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = SidebarWidget()
        self.sidebar.setStyleSheet("""
            SidebarWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1E1F2E, stop:1 #2A2B3D);
            }
        """)
        self.sidebar.nav_changed.connect(self._switch_page)
        main_layout.addWidget(self.sidebar)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background: #D0D0D8; max-width: 1px;")
        main_layout.addWidget(sep)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: #F5F1EB;")

        self.pages = []
        page_classes = [
            ArchiveOverview,
            ScanImportWindow,
            LetterEditor,
            RelationshipWindow,
            AlbumWindow,
            SearchBorrowWindow,
            BackupHandoverWindow,
        ]
        for cls in page_classes:
            page = cls()
            self.pages.append(page)
            self.stack.addWidget(page)

        main_layout.addWidget(self.stack, 1)

        for page in self.pages:
            if hasattr(page, 'data_changed'):
                try:
                    page.data_changed.connect(self._refresh_all)
                except Exception:
                    pass
            if hasattr(page, 'letter_deleted'):
                try:
                    page.letter_deleted.connect(self._refresh_all)
                except Exception:
                    pass

    def _switch_page(self, index):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            page = self.pages[index]
            if hasattr(page, 'refresh'):
                page.refresh()

    def _refresh_all(self):
        for page in self.pages:
            if hasattr(page, 'refresh'):
                try:
                    page.refresh()
                except Exception:
                    pass

    def _apply_global_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background: #F5F1EB;
            }
            QTableWidget {
                background: #FFFFFF;
                alternate-background-color: #FBF8F4;
                border: 1px solid #E0D8CE;
                border-radius: 6px;
                gridline-color: #E8E0D6;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #E8E0D6;
            }
            QTableWidget::item:selected {
                background: #E07A5F;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F8F4EE, stop:1 #EDE6DC);
                color: #5A4A3A;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 10px;
                border: none;
                border-bottom: 2px solid #D4B896;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E07A5F, stop:1 #C9664A);
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C9664A, stop:1 #B05538);
            }
            QPushButton:pressed {
                background: #B05538;
            }
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox {
                background: #FFFFFF;
                border: 1px solid #D4B896;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 13px;
                color: #3D405B;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 2px solid #E07A5F;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #3D405B;
                border: 1px solid #D4B896;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }
            QTabWidget::pane {
                border: 1px solid #D4B896;
                border-radius: 6px;
                background: #FFFFFF;
            }
            QTabBar::tab {
                background: #EDE6DC;
                color: #5A4A3A;
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #E07A5F;
                font-weight: bold;
                border-bottom: 2px solid #E07A5F;
            }
            QScrollBar:vertical {
                background: #EDE6DC;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #C4B8A8;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #A89880;
            }
            QScrollBar:horizontal {
                background: #EDE6DC;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #C4B8A8;
                border-radius: 5px;
                min-width: 30px;
            }
            QLabel {
                color: #3D405B;
            }
            QCheckBox {
                color: #3D405B;
                font-size: 13px;
            }
            QListWidget {
                background: #FFFFFF;
                border: 1px solid #D4B896;
                border-radius: 6px;
                font-size: 13px;
            }
            QListWidget::item:selected {
                background: #E07A5F;
                color: #FFFFFF;
            }
        """)


def main():
    init_db()

    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
