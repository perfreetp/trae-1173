import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTableWidget,
    QTableWidgetItem, QTabWidget, QFormLayout, QLineEdit,
    QComboBox, QTextEdit, QLabel, QPushButton, QCheckBox,
    QToolBar, QAction, QScrollArea, QGridLayout, QFileDialog,
    QMessageBox, QSpinBox, QSizePolicy, QGraphicsOpacityEffect,
    QFrame
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor
from database import execute_query, execute_query_returning, execute_update

WARM_STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei", "SimSun", sans-serif;
    font-size: 13px;
    color: #4a3728;
}
QSplitter::handle {
    background: #d4b896;
    width: 3px;
}
QTableWidget {
    background-color: #fdf8f0;
    alternate-background-color: #f7efe3;
    gridline-color: #e0d0bc;
    border: 1px solid #d4b896;
    selection-background-color: #e8cfa0;
    selection-color: #4a3728;
}
QTableWidget::item {
    padding: 4px 8px;
}
QHeaderView::section {
    background-color: #d4b896;
    color: #4a3728;
    padding: 6px 8px;
    border: 1px solid #c4a882;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #d4b896;
    background: #fdf8f0;
}
QTabBar::tab {
    background: #f0e4d4;
    color: #4a3728;
    padding: 8px 18px;
    border: 1px solid #d4b896;
    border-bottom: none;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #fdf8f0;
    font-weight: bold;
    border-bottom: 2px solid #b8784e;
}
QTabBar::tab:hover {
    background: #e8cfa0;
}
QLineEdit, QComboBox, QTextEdit, QSpinBox {
    background-color: #fdf8f0;
    border: 1px solid #d4b896;
    border-radius: 4px;
    padding: 4px 8px;
    color: #4a3728;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QSpinBox:focus {
    border: 2px solid #b8784e;
}
QPushButton {
    background-color: #d4b896;
    color: #4a3728;
    border: 1px solid #c4a882;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #c4a882;
}
QPushButton:pressed {
    background-color: #b8784e;
    color: #fdf8f0;
}
QToolBar {
    background: #f0e4d4;
    border: 1px solid #d4b896;
    spacing: 6px;
    padding: 4px;
}
QCheckBox {
    spacing: 6px;
    color: #4a3728;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QLabel {
    color: #4a3728;
}
QScrollArea {
    background: #fdf8f0;
    border: none;
}
"""

RESTORATION_STATUSES = ["良好", "轻微损毁", "需修复", "已修复"]


class PrivateOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.label = QLabel("🔒 私密内容", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        self.label.setStyleSheet("color: rgba(74, 55, 40, 120); background: transparent;")
        self._visible = False

    def set_overlay_visible(self, visible):
        self._visible = visible
        self.setVisible(visible)
        if visible:
            self.raise_()
            self.update_geometry()

    def update_geometry(self):
        if self.parent():
            self.setGeometry(self.parent().rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.label.setGeometry(self.rect())

    def paintEvent(self, event):
        if not self._visible:
            return
        from PyQt5.QtGui import QPainter, QBrush
        painter = QPainter(self)
        painter.fillRect(self.rect(), QBrush(QColor(253, 248, 240, 160)))
        painter.end()


class PhotoThumbnail(QFrame):
    remove_requested = pyqtSignal(int)

    def __init__(self, photo_id, file_path, description="", parent=None):
        super().__init__(parent)
        self.photo_id = photo_id
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setStyleSheet("""
            PhotoThumbnail {
                background: #f7efe3;
                border: 1px solid #d4b896;
                border-radius: 6px;
                padding: 4px;
            }
            PhotoThumbnail:hover {
                border: 2px solid #b8784e;
            }
        """)
        self.setFixedSize(160, 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.img_label = QLabel()
        self.img_label.setFixedSize(140, 110)
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("background: #ede4d6; border-radius: 4px;")
        self._load_thumbnail(file_path)
        layout.addWidget(self.img_label)

        self.desc_edit = QLineEdit(description)
        self.desc_edit.setPlaceholderText("照片描述")
        self.desc_edit.setMaxLength(50)
        layout.addWidget(self.desc_edit)

        btn_remove = QPushButton("移除")
        btn_remove.setFixedHeight(24)
        btn_remove.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        btn_remove.clicked.connect(lambda: self.remove_requested.emit(self.photo_id))
        layout.addWidget(btn_remove)

    def _load_thumbnail(self, file_path):
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                140, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.img_label.setPixmap(scaled)
        else:
            self.img_label.setText("无图片")
            self.img_label.setStyleSheet(
                "background: #ede4d6; border-radius: 4px; color: #999; font-size: 12px;"
            )


class LetterEditor(QWidget):
    letter_deleted = pyqtSignal()
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_letter_id = None
        self._private_overlay = None
        self._photo_widgets = []
        self._setup_ui()
        self.setStyleSheet(WARM_STYLESHEET)
        self._load_letter_list()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)

        left_panel = self._build_left_panel()
        splitter.addWidget(left_panel)

        right_panel = self._build_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([280, 720])

        bottom_bar = self._build_bottom_bar()
        main_layout.addWidget(bottom_bar)

    def _build_left_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title = QLabel("信件列表")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.letter_table = QTableWidget()
        self.letter_table.setColumnCount(6)
        self.letter_table.setHorizontalHeaderLabels(
            ["ID", "标题", "寄信人", "日期", "私密", "状态"]
        )
        self.letter_table.setAlternatingRowColors(True)
        self.letter_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.letter_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.letter_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.letter_table.verticalHeader().setVisible(False)
        self.letter_table.horizontalHeader().setStretchLastSection(True)
        self.letter_table.setColumnWidth(0, 40)
        self.letter_table.setColumnWidth(1, 120)
        self.letter_table.setColumnWidth(2, 70)
        self.letter_table.setColumnWidth(3, 80)
        self.letter_table.setColumnWidth(4, 45)
        self.letter_table.setColumnWidth(5, 60)
        self.letter_table.cellClicked.connect(self._on_letter_selected)
        layout.addWidget(self.letter_table)

        batch_label = QLabel("批量操作（先勾选多封信件）")
        batch_label.setStyleSheet("font-weight:bold; font-size:11px; color:#8b7355; padding-top:4px;")
        layout.addWidget(batch_label)

        batch_row1 = QHBoxLayout()
        batch_row1.addWidget(QLabel("分类："))
        self.batch_category_combo = QComboBox()
        self.batch_category_combo.setEditable(True)
        self.batch_category_combo.addItems(["", "家书", "公务", "其他"])
        self.batch_category_combo.setMinimumWidth(80)
        batch_row1.addWidget(self.batch_category_combo)

        batch_row1.addWidget(QLabel("修复："))
        self.batch_restoration_combo = QComboBox()
        self.batch_restoration_combo.addItems(["", "良好", "轻微损毁", "需修复", "已修复"])
        self.batch_restoration_combo.setMinimumWidth(80)
        batch_row1.addWidget(self.batch_restoration_combo)
        layout.addLayout(batch_row1)

        batch_row2 = QHBoxLayout()
        self.batch_private_check = QCheckBox("设为私密")
        self.batch_private_check.setStyleSheet("font-size:12px;")
        batch_row2.addWidget(self.batch_private_check)

        self.batch_unprivate_check = QCheckBox("取消私密")
        self.batch_unprivate_check.setStyleSheet("font-size:12px;")
        batch_row2.addWidget(self.batch_unprivate_check)

        self.batch_apply_btn = QPushButton("批量应用")
        self.batch_apply_btn.setFixedHeight(28)
        self.batch_apply_btn.setStyleSheet(
            "QPushButton{background:#b8784e;color:#fdf8f0;font-size:12px;padding:4px 10px;}"
            "QPushButton:hover{background:#a06040;}"
        )
        self.batch_apply_btn.clicked.connect(self._on_batch_apply)
        batch_row2.addWidget(self.batch_apply_btn)
        layout.addLayout(batch_row2)

        return widget

    def _build_right_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.private_checkbox = QCheckBox("🔒 私密标记")
        self.private_checkbox.stateChanged.connect(self._on_private_changed)
        top_bar.addWidget(self.private_checkbox)

        top_bar.addSpacing(20)

        status_label = QLabel("修复状态：")
        status_label.setFont(QFont("Microsoft YaHei", 12))
        top_bar.addWidget(status_label)

        self.restoration_combo = QComboBox()
        self.restoration_combo.addItems(RESTORATION_STATUSES)
        top_bar.addWidget(self.restoration_combo)
        top_bar.addStretch()

        layout.addLayout(top_bar)

        self.tabs = QTabWidget()
        self._build_basic_info_tab()
        self._build_content_edit_tab()
        self._build_ocr_tab()
        self._build_photo_tab()
        layout.addWidget(self.tabs)

        return widget

    def _build_basic_info_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("请输入信件标题")
        form.addRow("标题：", self.title_edit)

        self.sender_combo = QComboBox()
        self.sender_combo.setEditable(True)
        self.sender_combo.setPlaceholderText("选择寄信人")
        self._populate_people_combo(self.sender_combo)
        form.addRow("寄信人：", self.sender_combo)

        self.receiver_combo = QComboBox()
        self.receiver_combo.setEditable(True)
        self.receiver_combo.setPlaceholderText("选择收信人")
        self._populate_people_combo(self.receiver_combo)
        form.addRow("收信人：", self.receiver_combo)

        date_row = QHBoxLayout()
        self.send_date_edit = QLineEdit()
        self.send_date_edit.setPlaceholderText("如：1950-03-15")
        date_row.addWidget(QLabel("寄出日期："))
        date_row.addWidget(self.send_date_edit)
        self.receive_date_edit = QLineEdit()
        self.receive_date_edit.setPlaceholderText("如：1950-03-20")
        date_row.addWidget(QLabel("收到日期："))
        date_row.addWidget(self.receive_date_edit)
        date_row.addStretch()
        form.addRow(date_row)

        loc_row = QHBoxLayout()
        self.send_location_edit = QLineEdit()
        self.send_location_edit.setPlaceholderText("寄出地点")
        loc_row.addWidget(QLabel("寄出地："))
        loc_row.addWidget(self.send_location_edit)
        self.receive_location_edit = QLineEdit()
        self.receive_location_edit.setPlaceholderText("收到地点")
        loc_row.addWidget(QLabel("收到地："))
        loc_row.addWidget(self.receive_location_edit)
        loc_row.addStretch()
        form.addRow(loc_row)

        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("如：家书、商务信函")
        form.addRow("分类：", self.category_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(100)
        self.notes_edit.setPlaceholderText("备注信息")
        form.addRow("备注：", self.notes_edit)

        self.tabs.addTab(tab, "基本信息")

    def _build_content_edit_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)

        auto_break_action = QAction("自动断句", self)
        auto_break_action.setToolTip("在。！？；后自动添加换行")
        auto_break_action.triggered.connect(self._auto_sentence_break)
        toolbar.addAction(auto_break_action)

        toolbar.addSeparator()

        insert_annotation_action = QAction("插入批注", self)
        insert_annotation_action.setToolTip("在光标处插入批注标记")
        insert_annotation_action.triggered.connect(self._insert_annotation)
        toolbar.addAction(insert_annotation_action)

        toolbar.addSeparator()

        font_label = QLabel("  字号：")
        font_label.setStyleSheet("color: #4a3728;")
        toolbar.addWidget(font_label)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 36)
        self.font_size_spin.setValue(14)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setFixedWidth(80)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        toolbar.addWidget(self.font_size_spin)

        layout.addWidget(toolbar)

        self.content_edit = QTextEdit()
        self.content_edit.setFont(QFont("SimSun", 14))
        self.content_edit.setPlaceholderText("在此编辑信件正文内容……")
        self.content_edit.setStyleSheet(
            "QTextEdit { background: #fefcf8; border: 1px solid #d4b896; "
            "border-radius: 4px; padding: 12px; line-height: 1.8; }"
        )
        layout.addWidget(self.content_edit)

        self._private_overlay = PrivateOverlay(self.content_edit)
        self._private_overlay.hide()

        self.tabs.addTab(tab, "正文编辑")

    def _build_ocr_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        btn_row = QHBoxLayout()
        self.copy_ocr_btn = QPushButton("📋 复制OCR原文")
        self.copy_ocr_btn.setFixedWidth(160)
        self.copy_ocr_btn.clicked.connect(self._copy_ocr_to_editor)
        btn_row.addWidget(self.copy_ocr_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        ocr_splitter = QSplitter(Qt.Horizontal)
        ocr_splitter.setStretchFactor(0, 1)
        ocr_splitter.setStretchFactor(1, 1)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        ocr_raw_label = QLabel("OCR 原始文本（只读）")
        ocr_raw_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        left_layout.addWidget(ocr_raw_label)
        self.ocr_raw_edit = QTextEdit()
        self.ocr_raw_edit.setReadOnly(True)
        self.ocr_raw_edit.setFont(QFont("SimSun", 13))
        self.ocr_raw_edit.setStyleSheet(
            "QTextEdit { background: #f5efe6; border: 1px solid #d4b896; "
            "border-radius: 4px; padding: 10px; color: #8b7355; }"
        )
        self.ocr_raw_edit.setPlaceholderText("OCR识别的原始文本将显示在此处")
        left_layout.addWidget(self.ocr_raw_edit)
        ocr_splitter.addWidget(left_container)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        ocr_correct_label = QLabel("手动校对文本（可编辑）")
        ocr_correct_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        right_layout.addWidget(ocr_correct_label)
        self.ocr_correct_edit = QTextEdit()
        self.ocr_correct_edit.setFont(QFont("SimSun", 13))
        self.ocr_correct_edit.setStyleSheet(
            "QTextEdit { background: #fefcf8; border: 1px solid #d4b896; "
            "border-radius: 4px; padding: 10px; }"
        )
        self.ocr_correct_edit.setPlaceholderText("在此进行手动校对和修正")
        right_layout.addWidget(self.ocr_correct_edit)
        ocr_splitter.addWidget(right_container)

        ocr_splitter.setSizes([400, 400])
        layout.addWidget(ocr_splitter)

        self.tabs.addTab(tab, "OCR校对")

    def _build_photo_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        btn_row = QHBoxLayout()
        self.add_photo_btn = QPushButton("➕ 添加照片")
        self.add_photo_btn.clicked.connect(self._add_photo)
        btn_row.addWidget(self.add_photo_btn)
        btn_row.addStretch()

        photo_count_label = QLabel("照片列表：")
        photo_count_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        btn_row.addWidget(photo_count_label)

        self.photo_count_value = QLabel("0")
        self.photo_count_value.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        btn_row.addWidget(self.photo_count_value)

        layout.addLayout(btn_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.photo_container = QWidget()
        self.photo_grid = QGridLayout(self.photo_container)
        self.photo_grid.setSpacing(12)
        self.photo_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self.photo_container)

        layout.addWidget(scroll)

        self.tabs.addTab(tab, "照片管理")

    def _build_bottom_bar(self):
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 4, 0, 0)

        layout.addStretch()

        self.save_btn = QPushButton("💾 保存修改")
        self.save_btn.setFixedSize(120, 36)
        self.save_btn.clicked.connect(self._save_letter)
        layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton("🗑 删除信件")
        self.delete_btn.setFixedSize(120, 36)
        self.delete_btn.setStyleSheet(
            "QPushButton { background-color: #c0735e; color: #fdf8f0; }"
            "QPushButton:hover { background-color: #a85a45; }"
            "QPushButton:pressed { background-color: #8b3a2a; }"
        )
        self.delete_btn.clicked.connect(self._delete_letter)
        layout.addWidget(self.delete_btn)

        return bar

    def _populate_people_combo(self, combo):
        combo.clear()
        combo.addItem("", -1)
        rows = execute_query_returning(
            "SELECT id, name FROM people ORDER BY name"
        )
        for row in rows:
            combo.addItem(row["name"], row["id"])

    def _load_letter_list(self):
        self.letter_table.setRowCount(0)
        rows = execute_query_returning("""
            SELECT l.id, l.title, p.name AS sender_name,
                   l.send_date, l.is_private, l.restoration_status
            FROM letters l
            LEFT JOIN people p ON l.sender_id = p.id
            ORDER BY l.send_date DESC, l.id DESC
        """)
        self.letter_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.letter_table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.letter_table.setItem(i, 1, QTableWidgetItem(row["title"] or ""))
            self.letter_table.setItem(i, 2, QTableWidgetItem(row["sender_name"] or ""))
            self.letter_table.setItem(i, 3, QTableWidgetItem(row["send_date"] or ""))
            priv = "🔒 是" if row["is_private"] else "否"
            self.letter_table.setItem(i, 4, QTableWidgetItem(priv))
            self.letter_table.setItem(
                i, 5, QTableWidgetItem(row["restoration_status"] or "良好")
            )
        self.letter_table.resizeRowsToContents()

    def _on_letter_selected(self, row, _col):
        id_item = self.letter_table.item(row, 0)
        if not id_item:
            return
        letter_id = int(id_item.text())
        self._load_letter_detail(letter_id)

    def _load_letter_detail(self, letter_id):
        self.current_letter_id = letter_id
        rows = execute_query_returning(
            "SELECT * FROM letters WHERE id = ?", (letter_id,)
        )
        if not rows:
            return
        data = rows[0]

        self.title_edit.setText(data.get("title", "") or "")
        self._set_combo_by_id(self.sender_combo, data.get("sender_id"))
        self._set_combo_by_id(self.receiver_combo, data.get("receiver_id"))
        self.send_date_edit.setText(data.get("send_date", "") or "")
        self.receive_date_edit.setText(data.get("receive_date", "") or "")
        self.send_location_edit.setText(data.get("send_location", "") or "")
        self.receive_location_edit.setText(data.get("receive_location", "") or "")
        self.category_edit.setText(data.get("category", "") or "")
        self.notes_edit.setPlainText(data.get("notes", "") or "")
        self.content_edit.setPlainText(data.get("content", "") or "")
        self.ocr_raw_edit.setPlainText(data.get("raw_ocr_text", "") or "")
        self.ocr_correct_edit.setPlainText(data.get("content", "") or "")

        is_private = bool(data.get("is_private", 0))
        self.private_checkbox.blockSignals(True)
        self.private_checkbox.setChecked(is_private)
        self.private_checkbox.blockSignals(False)
        self._apply_private_overlay(is_private)

        status = data.get("restoration_status", "良好") or "良好"
        idx = self.restoration_combo.findText(status)
        if idx >= 0:
            self.restoration_combo.setCurrentIndex(idx)

        self._load_photos(letter_id)

    def _set_combo_by_id(self, combo, person_id):
        if person_id is None:
            combo.setCurrentIndex(0)
            return
        for i in range(combo.count()):
            if combo.itemData(i) == person_id:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)

    def _on_private_changed(self, state):
        is_private = state == Qt.Checked
        self._apply_private_overlay(is_private)

    def _apply_private_overlay(self, is_private):
        if self._private_overlay:
            self._private_overlay.set_overlay_visible(is_private)
        if is_private:
            self.private_checkbox.setText("🔒 私密标记（已锁定）")
        else:
            self.private_checkbox.setText("🔓 私密标记")

    def _auto_sentence_break(self):
        cursor = self.content_edit.textCursor()
        text = self.content_edit.toPlainText()
        result = re.sub(r'([。！？；])', r'\1\n', text)
        self.content_edit.setPlainText(result)

    def _insert_annotation(self):
        cursor = self.content_edit.textCursor()
        annotation_text = "【批注：】"
        cursor.insertText(annotation_text)
        cursor.movePosition(cursor.Left, cursor.MoveAnchor, 1)
        cursor.movePosition(cursor.Left, cursor.KeepAnchor, 1)
        self.content_edit.setTextCursor(cursor)
        self.content_edit.setFocus()

    def _on_font_size_changed(self, size):
        cursor = self.content_edit.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontPointSize(size)
        self.content_edit.mergeCurrentCharFormat(fmt)

    def _copy_ocr_to_editor(self):
        ocr_text = self.ocr_raw_edit.toPlainText()
        if ocr_text:
            self.ocr_correct_edit.setPlainText(ocr_text)
            self.content_edit.setPlainText(ocr_text)

    def _load_photos(self, letter_id):
        for w in self._photo_widgets:
            self.photo_grid.removeWidget(w)
            w.deleteLater()
        self._photo_widgets.clear()

        rows = execute_query_returning(
            "SELECT id, file_path, description FROM photos WHERE letter_id = ? ORDER BY id",
            (letter_id,),
        )
        cols = 4
        for i, row in enumerate(rows):
            thumb = PhotoThumbnail(row["id"], row["file_path"], row["description"] or "")
            thumb.remove_requested.connect(self._remove_photo)
            c = i % cols
            r = i // cols
            self.photo_grid.addWidget(thumb, r, c)
            self._photo_widgets.append(thumb)

        self.photo_count_value.setText(str(len(rows)))

    def _add_photo(self):
        if self.current_letter_id is None:
            QMessageBox.warning(self, "提示", "请先选择一封信件")
            return
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择照片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if not file_paths:
            return
        for fp in file_paths:
            execute_query(
                "INSERT INTO photos (letter_id, file_path, description) VALUES (?, ?, '')",
                (self.current_letter_id, fp),
            )
        self._load_photos(self.current_letter_id)

    def _remove_photo(self, photo_id):
        reply = QMessageBox.question(
            self, "确认移除", "确定要移除这张照片吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            execute_update("DELETE FROM photos WHERE id = ?", (photo_id,))
            if self.current_letter_id:
                self._load_photos(self.current_letter_id)

    def _save_letter(self):
        if self.current_letter_id is None:
            QMessageBox.warning(self, "提示", "请先选择一封信件")
            return

        sender_id = self._resolve_person_id(self.sender_combo)
        receiver_id = self._resolve_person_id(self.receiver_combo)
        is_private = 1 if self.private_checkbox.isChecked() else 0
        restoration_status = self.restoration_combo.currentText()

        execute_update("""
            UPDATE letters SET
                title = ?, sender_id = ?, receiver_id = ?,
                send_date = ?, receive_date = ?,
                send_location = ?, receive_location = ?,
                category = ?, notes = ?, content = ?,
                raw_ocr_text = ?,
                is_private = ?, restoration_status = ?,
                updated_at = datetime('now','localtime')
            WHERE id = ?
        """, (
            self.title_edit.text(),
            sender_id,
            receiver_id,
            self.send_date_edit.text(),
            self.receive_date_edit.text(),
            self.send_location_edit.text(),
            self.receive_location_edit.text(),
            self.category_edit.text(),
            self.notes_edit.toPlainText(),
            self.content_edit.toPlainText(),
            self.ocr_raw_edit.toPlainText(),
            is_private,
            restoration_status,
            self.current_letter_id,
        ))

        self._save_photo_descriptions()
        self._load_letter_list()
        self._populate_people_combo(self.sender_combo)
        self._populate_people_combo(self.receiver_combo)
        if sender_id:
            for i in range(self.sender_combo.count()):
                if self.sender_combo.itemData(i) == sender_id:
                    self.sender_combo.setCurrentIndex(i)
                    break
        if receiver_id:
            for i in range(self.receiver_combo.count()):
                if self.receiver_combo.itemData(i) == receiver_id:
                    self.receiver_combo.setCurrentIndex(i)
                    break
        self.data_changed.emit()
        QMessageBox.information(self, "保存成功", "信件修改已保存")

    def _save_photo_descriptions(self):
        for thumb in self._photo_widgets:
            desc = thumb.desc_edit.text()
            execute_update(
                "UPDATE photos SET description = ? WHERE id = ?",
                (desc, thumb.photo_id),
            )

    def _delete_letter(self):
        if self.current_letter_id is None:
            QMessageBox.warning(self, "提示", "请先选择一封信件")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除信件（ID: {self.current_letter_id}）吗？\n此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            execute_update("DELETE FROM letters WHERE id = ?", (self.current_letter_id,))
            self.current_letter_id = None
            self._clear_form()
            self._load_letter_list()
            self.letter_deleted.emit()
            self.data_changed.emit()
            QMessageBox.information(self, "已删除", "信件已删除")

    def _clear_form(self):
        self.title_edit.clear()
        self.sender_combo.setCurrentIndex(0)
        self.receiver_combo.setCurrentIndex(0)
        self.send_date_edit.clear()
        self.receive_date_edit.clear()
        self.send_location_edit.clear()
        self.receive_location_edit.clear()
        self.category_edit.clear()
        self.notes_edit.clear()
        self.content_edit.clear()
        self.ocr_raw_edit.clear()
        self.ocr_correct_edit.clear()
        self.private_checkbox.setChecked(False)
        self.restoration_combo.setCurrentIndex(0)
        for w in self._photo_widgets:
            self.photo_grid.removeWidget(w)
            w.deleteLater()
        self._photo_widgets.clear()
        self.photo_count_value.setText("0")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._private_overlay and self._private_overlay._visible:
            self._private_overlay.update_geometry()

    def refresh(self):
        self._load_letter_list()
        self._populate_people_combo(self.sender_combo)
        self._populate_people_combo(self.receiver_combo)

    def _on_batch_apply(self):
        selected_rows = self.letter_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在左侧列表中选择一封或多封信件。")
            return

        letter_ids = []
        for idx in selected_rows:
            id_item = self.letter_table.item(idx.row(), 0)
            if id_item:
                letter_ids.append(int(id_item.text()))

        if not letter_ids:
            return

        category = self.batch_category_combo.currentText().strip()
        restoration = self.batch_restoration_combo.currentText().strip()
        set_private = self.batch_private_check.isChecked()
        unset_private = self.batch_unprivate_check.isChecked()

        if not category and not restoration and not set_private and not unset_private:
            QMessageBox.information(self, "提示", "请至少选择一项要批量修改的内容。")
            return

        changes = []
        if category:
            changes.append(f"分类 → {category}")
        if restoration:
            changes.append(f"修复状态 → {restoration}")
        if set_private:
            changes.append("设为私密")
        if unset_private:
            changes.append("取消私密")

        reply = QMessageBox.question(
            self, "确认批量操作",
            f"已选中 {len(letter_ids)} 封信件，将执行以下修改：\n\n"
            + "\n".join(f"  · {c}" for c in changes)
            + "\n\n确认应用？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        for lid in letter_ids:
            sets = []
            params = []
            if category:
                sets.append("category = ?")
                params.append(category)
            if restoration:
                sets.append("restoration_status = ?")
                params.append(restoration)
            if set_private:
                sets.append("is_private = 1")
            if unset_private:
                sets.append("is_private = 0")
            if sets:
                sets.append("updated_at = datetime('now','localtime')")
                sql = f"UPDATE letters SET {', '.join(sets)} WHERE id = ?"
                params.append(lid)
                execute_update(sql, tuple(params))

        self._load_letter_list()
        self.data_changed.emit()
        QMessageBox.information(self, "批量操作完成", f"已更新 {len(letter_ids)} 封信件。")

    def _resolve_person_id(self, combo):
        text = combo.currentText().strip()
        if not text:
            return None
        idx = combo.currentIndex()
        if idx >= 0:
            pid = combo.itemData(idx)
            item_text = combo.itemText(idx) if idx < combo.count() else ""
            if pid and pid != -1 and item_text == text:
                return pid
        existing = execute_query_returning("SELECT id FROM people WHERE name = ?", (text,))
        if existing:
            return existing[0]["id"]
        new_id = execute_query("INSERT INTO people (name) VALUES (?)", (text,))
        self._populate_people_combo(combo)
        other = self.receiver_combo if combo is self.sender_combo else self.sender_combo
        self._populate_people_combo(other)
        for i in range(combo.count()):
            if combo.itemData(i) == new_id:
                combo.setCurrentIndex(i)
                break
        return new_id

    def _select_letter_by_id(self, letter_id):
        for row in range(self.letter_table.rowCount()):
            item = self.letter_table.item(row, 0)
            if item and int(item.text()) == letter_id:
                self.letter_table.selectRow(row)
                self._on_letter_selected(row, 0)
                break
