import sys
from datetime import date

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QComboBox,
    QCheckBox, QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
    QGroupBox, QTextEdit, QSplitter, QAbstractItemView, QSizePolicy,
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from database import execute_query, execute_query_returning, execute_update, search_letters

STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 13px;
}
QGroupBox {
    font-weight: bold;
    font-size: 14px;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    margin-top: 12px;
    padding: 14px 10px 10px 10px;
    background-color: #fafafa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #2c3e50;
}
QLineEdit, QComboBox, QDateEdit {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    padding: 5px 8px;
    background: #fff;
    min-height: 28px;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
    border-color: #3498db;
}
QPushButton {
    border: none;
    border-radius: 4px;
    padding: 7px 18px;
    background-color: #3498db;
    color: #fff;
    font-weight: bold;
    min-height: 30px;
}
QPushButton:hover {
    background-color: #2980b9;
}
QPushButton:pressed {
    background-color: #21618c;
}
QPushButton#btnDanger {
    background-color: #e74c3c;
}
QPushButton#btnDanger:hover {
    background-color: #c0392b;
}
QPushButton#btnSuccess {
    background-color: #27ae60;
}
QPushButton#btnSuccess:hover {
    background-color: #1e8449;
}
QPushButton#btnWarning {
    background-color: #f39c12;
}
QPushButton#btnWarning:hover {
    background-color: #d68910;
}
QTableWidget {
    border: 1px solid #d0d0d0;
    border-radius: 4px;
    background-color: #fff;
    gridline-color: #e8e8e8;
    selection-background-color: #d4e6f1;
    selection-color: #2c3e50;
}
QTableWidget::item {
    padding: 4px 6px;
}
QHeaderView::section {
    background-color: #ecf0f1;
    border: none;
    border-bottom: 2px solid #bdc3c7;
    border-right: 1px solid #d5d8dc;
    padding: 6px 8px;
    font-weight: bold;
    color: #2c3e50;
}
QLabel#statsLabel {
    font-size: 14px;
    font-weight: bold;
    color: #2c3e50;
    padding: 4px 10px;
}
QCheckBox {
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QDialog {
    background-color: #fafafa;
}
QTextEdit {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    background: #fff;
    padding: 4px;
}
"""


class LetterDetailDialog(QDialog):
    def __init__(self, letter_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"家书详情 - {letter_data.get('title', '')}")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(STYLESHEET)
        layout = QVBoxLayout(self)

        fields = [
            ("标题", letter_data.get("title", "")),
            ("寄信人", letter_data.get("sender_name", "")),
            ("收信人", letter_data.get("receiver_name", "")),
            ("寄信日期", letter_data.get("send_date", "")),
            ("收信日期", letter_data.get("receive_date", "")),
            ("寄信地点", letter_data.get("send_location", "")),
            ("收信地点", letter_data.get("receive_location", "")),
            ("类别", letter_data.get("category", "")),
            ("私密", "是" if letter_data.get("is_private") else "否"),
            ("修复状态", letter_data.get("restoration_status", "")),
        ]

        meta_layout = QFormLayout()
        for label_text, value in fields:
            lbl = QLabel(label_text)
            lbl.setFixedWidth(70)
            val = QLabel(str(value) if value else "-")
            val.setWordWrap(True)
            meta_layout.addRow(lbl, val)
        layout.addLayout(meta_layout)

        layout.addWidget(QLabel("正文内容："))
        content_edit = QTextEdit()
        content_edit.setReadOnly(True)
        content_edit.setPlainText(letter_data.get("content", "") or "（无内容）")
        content_edit.setMinimumHeight(200)
        layout.addWidget(content_edit)

        if letter_data.get("notes"):
            layout.addWidget(QLabel("备注："))
            notes_edit = QTextEdit()
            notes_edit.setReadOnly(True)
            notes_edit.setPlainText(letter_data["notes"])
            notes_edit.setMaximumHeight(80)
            layout.addWidget(notes_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)


class BorrowDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登记借阅")
        self.setMinimumWidth(420)
        self.setStyleSheet(STYLESHEET)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.letter_combo = QComboBox()
        self._load_letters()
        form.addRow("选择家书：", self.letter_combo)

        self.borrower_edit = QLineEdit()
        self.borrower_edit.setPlaceholderText("请输入借阅人姓名")
        form.addRow("借阅人：", self.borrower_edit)

        self.borrow_date_edit = QDateEdit()
        self.borrow_date_edit.setCalendarPopup(True)
        self.borrow_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.borrow_date_edit.setDate(QDate.currentDate())
        form.addRow("借阅日期：", self.borrow_date_edit)

        self.expected_return_edit = QDateEdit()
        self.expected_return_edit.setCalendarPopup(True)
        self.expected_return_edit.setDisplayFormat("yyyy-MM-dd")
        self.expected_return_edit.setDate(QDate.currentDate().addDays(30))
        form.addRow("预计归还日期：", self.expected_return_edit)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("备注（可选）")
        form.addRow("备注：", self.notes_edit)

        layout.addLayout(form)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("确定")
        btn_box.button(QDialogButtonBox.Cancel).setText("取消")
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_letters(self):
        rows = execute_query_returning(
            "SELECT l.id, l.title, p.name as sender_name "
            "FROM letters l LEFT JOIN people p ON l.sender_id = p.id "
            "ORDER BY l.id DESC"
        )
        for r in rows:
            title = r["title"] or f"无标题#{r['id']}"
            sender = r.get("sender_name", "")
            display = f"{r['id']} - {title}" + (f"（{sender}）" if sender else "")
            self.letter_combo.addItem(display, r["id"])

    def _on_accept(self):
        if self.letter_combo.count() == 0:
            QMessageBox.warning(self, "提示", "没有可选择的家书。")
            return
        if not self.borrower_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入借阅人姓名。")
            return
        self.accept()

    def get_data(self):
        return {
            "letter_id": self.letter_combo.currentData(),
            "borrower_name": self.borrower_edit.text().strip(),
            "borrow_date": self.borrow_date_edit.date().toString("yyyy-MM-dd"),
            "expected_return_date": self.expected_return_edit.date().toString("yyyy-MM-dd"),
            "notes": self.notes_edit.text().strip(),
        }


class SearchBorrowWindow(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("检索借阅")
        self.setMinimumSize(1100, 800)
        self.setStyleSheet(STYLESHEET)
        self._setup_ui()
        self._load_combo_data()
        self._do_search()
        self._refresh_borrow_table()
        self._update_statistics()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(14, 14, 14, 14)

        splitter = QSplitter(Qt.Vertical)

        # ---- 检索区域 ----
        search_group = QGroupBox("全文检索")
        search_layout = QVBoxLayout(search_group)

        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索家书标题、内容、人名、地点……")
        self.search_input.returnPressed.connect(self._do_search)
        top_bar.addWidget(self.search_input, stretch=1)

        self.search_btn = QPushButton("搜索")
        self.search_btn.setFixedWidth(100)
        self.search_btn.clicked.connect(self._do_search)
        top_bar.addWidget(self.search_btn)

        self.borrow_from_result_btn = QPushButton("登记借阅")
        self.borrow_from_result_btn.setObjectName("btnSuccess")
        self.borrow_from_result_btn.setFixedWidth(100)
        self.borrow_from_result_btn.clicked.connect(self._on_borrow_from_result)
        top_bar.addWidget(self.borrow_from_result_btn)
        search_layout.addLayout(top_bar)

        adv_layout = QHBoxLayout()
        adv_layout.addWidget(QLabel("日期范围："))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate(1900, 1, 1))
        self.date_from.setFixedWidth(130)
        adv_layout.addWidget(self.date_from)

        adv_layout.addWidget(QLabel("至"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setFixedWidth(130)
        adv_layout.addWidget(self.date_to)

        adv_layout.addWidget(QLabel("寄信人："))
        self.sender_combo = QComboBox()
        self.sender_combo.setMinimumWidth(100)
        adv_layout.addWidget(self.sender_combo)

        adv_layout.addWidget(QLabel("收信人："))
        self.receiver_combo = QComboBox()
        self.receiver_combo.setMinimumWidth(100)
        adv_layout.addWidget(self.receiver_combo)

        adv_layout.addWidget(QLabel("类别："))
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(90)
        adv_layout.addWidget(self.category_combo)

        self.private_check = QCheckBox("仅私密")
        adv_layout.addWidget(self.private_check)

        self.date_filter_check = QCheckBox("启用日期筛选")
        self.date_filter_check.setChecked(False)
        adv_layout.addWidget(self.date_filter_check)

        adv_layout.addWidget(QLabel("修复状态："))
        self.restoration_combo = QComboBox()
        self.restoration_combo.addItems(["全部", "良好", "一般", "需修复"])
        self.restoration_combo.setMinimumWidth(80)
        adv_layout.addWidget(self.restoration_combo)

        adv_layout.addStretch()
        search_layout.addLayout(adv_layout)

        self.search_table = QTableWidget()
        self.search_table.setColumnCount(9)
        self.search_table.setHorizontalHeaderLabels(
            ["ID", "标题", "寄信人", "收信人", "日期", "地点", "内容预览", "私密", "借阅状态"]
        )
        self.search_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.search_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.search_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.search_table.setAlternatingRowColors(True)
        self.search_table.doubleClicked.connect(self._on_letter_double_clicked)
        search_layout.addWidget(self.search_table)

        splitter.addWidget(search_group)

        # ---- 借阅管理区域 ----
        borrow_group = QGroupBox("借阅管理")
        borrow_layout = QVBoxLayout(borrow_group)

        btn_bar = QHBoxLayout()
        self.borrow_btn = QPushButton("登记借阅")
        self.borrow_btn.setObjectName("btnSuccess")
        self.borrow_btn.clicked.connect(self._on_register_borrow)
        btn_bar.addWidget(self.borrow_btn)

        self.return_btn = QPushButton("登记归还")
        self.return_btn.setObjectName("btnWarning")
        self.return_btn.clicked.connect(self._on_register_return)
        btn_bar.addWidget(self.return_btn)

        self.delete_btn = QPushButton("删除记录")
        self.delete_btn.setObjectName("btnDanger")
        self.delete_btn.clicked.connect(self._on_delete_record)
        btn_bar.addWidget(self.delete_btn)

        btn_bar.addStretch()
        borrow_layout.addLayout(btn_bar)

        self.borrow_table = QTableWidget()
        self.borrow_table.setColumnCount(8)
        self.borrow_table.setHorizontalHeaderLabels(
            ["ID", "家书标题", "借阅人", "借阅日期", "预计归还", "实际归还", "状态", "备注"]
        )
        self.borrow_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.borrow_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.borrow_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.borrow_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.borrow_table.setAlternatingRowColors(True)
        borrow_layout.addWidget(self.borrow_table)

        splitter.addWidget(borrow_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, stretch=1)

        # ---- 底部统计 ----
        stats_bar = QHBoxLayout()
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("statsLabel")
        stats_bar.addWidget(self.stats_label)
        stats_bar.addStretch()
        main_layout.addLayout(stats_bar)

    def _load_combo_data(self):
        self.sender_combo.clear()
        self.receiver_combo.clear()
        self.category_combo.clear()

        people = execute_query_returning("SELECT id, name FROM people ORDER BY name")
        self.sender_combo.addItem("全部", None)
        self.receiver_combo.addItem("全部", None)
        for p in people:
            self.sender_combo.addItem(p["name"], p["id"])
            self.receiver_combo.addItem(p["name"], p["id"])

        categories = execute_query_returning(
            "SELECT DISTINCT category FROM letters WHERE category IS NOT NULL AND category != '' ORDER BY category"
        )
        self.category_combo.addItem("全部", None)
        for c in categories:
            self.category_combo.addItem(c["category"], c["category"])

    def _do_search(self):
        keyword = self.search_input.text().strip()
        if keyword:
            results = search_letters(keyword)
        else:
            results = execute_query_returning(
                "SELECT l.*, p1.name as sender_name, p2.name as receiver_name "
                "FROM letters l "
                "LEFT JOIN people p1 ON l.sender_id = p1.id "
                "LEFT JOIN people p2 ON l.receiver_id = p2.id "
                "ORDER BY l.send_date DESC"
            )

        sender_id = self.sender_combo.currentData()
        if sender_id is not None:
            results = [r for r in results if r.get("sender_id") == sender_id]

        receiver_id = self.receiver_combo.currentData()
        if receiver_id is not None:
            results = [r for r in results if r.get("receiver_id") == receiver_id]

        if self.date_filter_check.isChecked():
            date_from_str = self.date_from.date().toString("yyyy-MM-dd")
            date_to_str = self.date_to.date().toString("yyyy-MM-dd")
            results = [
                r for r in results
                if not r.get("send_date")
                or (date_from_str <= r["send_date"] <= date_to_str)
            ]

        category = self.category_combo.currentData()
        if category is not None:
            results = [r for r in results if r.get("category") == category]

        if self.private_check.isChecked():
            results = [r for r in results if r.get("is_private")]

        restoration = self.restoration_combo.currentText()
        if restoration != "全部":
            results = [r for r in results if r.get("restoration_status") == restoration]

        letter_ids = [r["id"] for r in results]
        borrow_map = {}
        if letter_ids:
            placeholders = ",".join("?" for _ in letter_ids)
            borrow_rows = execute_query_returning(
                f"SELECT letter_id, status FROM borrow_records "
                f"WHERE id IN (SELECT MAX(id) FROM borrow_records GROUP BY letter_id) "
                f"AND letter_id IN ({placeholders})",
                tuple(letter_ids)
            )
            for br in borrow_rows:
                borrow_map[br["letter_id"]] = br["status"]

        for r in results:
            r["_borrow_status"] = borrow_map.get(r["id"], "无")

        self._populate_search_table(results)

    def _populate_search_table(self, results):
        self.search_table.setRowCount(len(results))
        for row, r in enumerate(results):
            self.search_table.setItem(row, 0, QTableWidgetItem(str(r.get("id", ""))))
            self.search_table.setItem(row, 1, QTableWidgetItem(r.get("title", "") or ""))
            self.search_table.setItem(row, 2, QTableWidgetItem(r.get("sender_name", "") or ""))
            self.search_table.setItem(row, 3, QTableWidgetItem(r.get("receiver_name", "") or ""))
            self.search_table.setItem(row, 4, QTableWidgetItem(r.get("send_date", "") or ""))
            self.search_table.setItem(row, 5, QTableWidgetItem(r.get("send_location", "") or ""))

            content = r.get("content", "") or ""
            preview = content[:50] + ("…" if len(content) > 50 else "")
            self.search_table.setItem(row, 6, QTableWidgetItem(preview))

            private_item = QTableWidgetItem("是" if r.get("is_private") else "否")
            private_item.setTextAlignment(Qt.AlignCenter)
            if r.get("is_private"):
                private_item.setForeground(QColor("#e74c3c"))
            self.search_table.setItem(row, 7, private_item)

            borrow_status = r.get("_borrow_status", "无")
            borrow_item = QTableWidgetItem(borrow_status)
            borrow_item.setTextAlignment(Qt.AlignCenter)
            if borrow_status == "借出":
                borrow_item.setForeground(QColor("#f39c12"))
            elif borrow_status == "已归还":
                borrow_item.setForeground(QColor("#27ae60"))
            self.search_table.setItem(row, 8, borrow_item)

        self.search_table.setRowCount(len(results))

    def _on_letter_double_clicked(self, index):
        row = index.row()
        letter_id_item = self.search_table.item(row, 0)
        if not letter_id_item:
            return
        letter_id = int(letter_id_item.text())
        rows = execute_query_returning(
            "SELECT l.*, p1.name as sender_name, p2.name as receiver_name "
            "FROM letters l "
            "LEFT JOIN people p1 ON l.sender_id = p1.id "
            "LEFT JOIN people p2 ON l.receiver_id = p2.id "
            "WHERE l.id = ?",
            (letter_id,),
        )
        if rows:
            dlg = LetterDetailDialog(rows[0], self)
            dlg.exec_()

    def _refresh_borrow_table(self):
        rows = execute_query_returning(
            "SELECT br.*, l.title as letter_title "
            "FROM borrow_records br "
            "LEFT JOIN letters l ON br.letter_id = l.id "
            "ORDER BY br.borrow_date DESC"
        )
        self.borrow_table.setRowCount(len(rows))
        today = date.today().isoformat()
        for row, r in enumerate(rows):
            self.borrow_table.setItem(row, 0, QTableWidgetItem(str(r.get("id", ""))))
            self.borrow_table.setItem(row, 1, QTableWidgetItem(r.get("letter_title", "") or ""))
            self.borrow_table.setItem(row, 2, QTableWidgetItem(r.get("borrower_name", "") or ""))
            self.borrow_table.setItem(row, 3, QTableWidgetItem(r.get("borrow_date", "") or ""))
            self.borrow_table.setItem(row, 4, QTableWidgetItem(r.get("expected_return_date", "") or ""))
            self.borrow_table.setItem(row, 5, QTableWidgetItem(r.get("return_date", "") or ""))

            status = r.get("status", "")
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            if status == "借出":
                expected = r.get("expected_return_date", "")
                if expected and expected < today:
                    status_item.setText("逾期")
                    status_item.setForeground(QColor("#e74c3c"))
                else:
                    status_item.setForeground(QColor("#f39c12"))
            elif status == "已归还":
                status_item.setForeground(QColor("#27ae60"))
            self.borrow_table.setItem(row, 6, status_item)

            self.borrow_table.setItem(row, 7, QTableWidgetItem(r.get("notes", "") or ""))

    def _on_register_borrow(self):
        dlg = BorrowDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            execute_query(
                "INSERT INTO borrow_records (letter_id, borrower_name, borrow_date, expected_return_date, status, notes) "
                "VALUES (?, ?, ?, ?, '借出', ?)",
                (
                    data["letter_id"],
                    data["borrower_name"],
                    data["borrow_date"],
                    data["expected_return_date"],
                    data["notes"],
                ),
            )
            self._refresh_borrow_table()
            self._update_statistics()
            self._do_search()
            self.data_changed.emit()

    def _on_register_return(self):
        selected = self.borrow_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择一条借阅记录。")
            return
        row = selected[0].row()
        record_id = int(self.borrow_table.item(row, 0).text())
        current_status = self.borrow_table.item(row, 6).text()

        if current_status == "已归还":
            QMessageBox.information(self, "提示", "该记录已归还，无需重复操作。")
            return

        reply = QMessageBox.question(
            self, "确认归还", "确认登记归还该借阅记录？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            today_str = QDate.currentDate().toString("yyyy-MM-dd")
            execute_update(
                "UPDATE borrow_records SET return_date = ?, status = '已归还' WHERE id = ?",
                (today_str, record_id),
            )
            self._refresh_borrow_table()
            self._update_statistics()
            self._do_search()
            self.data_changed.emit()

    def _on_delete_record(self):
        selected = self.borrow_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择一条借阅记录。")
            return
        row = selected[0].row()
        record_id = int(self.borrow_table.item(row, 0).text())

        reply = QMessageBox.question(
            self, "确认删除", f"确认删除借阅记录 #{record_id}？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            execute_update("DELETE FROM borrow_records WHERE id = ?", (record_id,))
            self._refresh_borrow_table()
            self._update_statistics()
            self._do_search()
            self.data_changed.emit()

    def _on_borrow_from_result(self):
        selected = self.search_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "提示", "请先在搜索结果中选择一封信件。")
            return
        row = selected[0].row()
        letter_id = int(self.search_table.item(row, 0).text())
        letter_title = self.search_table.item(row, 1).text()

        borrow_status_item = self.search_table.item(row, 8)
        if borrow_status_item and borrow_status_item.text() == "借出":
            QMessageBox.information(self, "提示", f"「{letter_title}」已在借出中，无需重复登记。")
            return

        dlg = BorrowDialog(self)
        for i in range(dlg.letter_combo.count()):
            if dlg.letter_combo.itemData(i) == letter_id:
                dlg.letter_combo.setCurrentIndex(i)
                break
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            execute_query(
                "INSERT INTO borrow_records (letter_id, borrower_name, borrow_date, expected_return_date, status, notes) "
                "VALUES (?, ?, ?, ?, '借出', ?)",
                (
                    data["letter_id"],
                    data["borrower_name"],
                    data["borrow_date"],
                    data["expected_return_date"],
                    data["notes"],
                ),
            )
            self._refresh_borrow_table()
            self._update_statistics()
            self._do_search()
            self.data_changed.emit()

    def _update_statistics(self):
        rows = execute_query_returning(
            "SELECT status, expected_return_date FROM borrow_records"
        )
        total = len(rows)
        out = sum(1 for r in rows if r["status"] == "借出")
        today = date.today().isoformat()
        overdue = sum(
            1 for r in rows
            if r["status"] == "借出"
            and r.get("expected_return_date")
            and r["expected_return_date"] < today
        )
        self.stats_label.setText(
            f"借阅统计 ｜ 总计：{total} 条 ｜ 借出中：{out} 条 ｜ 逾期：{overdue} 条"
        )

    def refresh(self):
        self._load_combo_data()
        self._do_search()
        self._refresh_borrow_table()
        self._update_statistics()
