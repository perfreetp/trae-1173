from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QMessageBox,
    QScrollArea, QFrame, QDialog, QSizePolicy
)
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt5.QtCore import Qt, pyqtSignal

from database import get_statistics, get_timeline_data, execute_query_returning, execute_update


STAT_CARDS = [
    ("total_letters", "书信总数", "#E07A5F"),
    ("total_people", "人物总数", "#3D405B"),
    ("private_letters", "私密信件", "#81B29A"),
    ("borrowed_out", "借出数量", "#F2CC8F"),
    ("need_repair", "待修复", "#E07A5F"),
    ("total_albums", "相册总数", "#3D405B"),
    ("total_photos", "照片总数", "#81B29A"),
]

TABLE_HEADERS = ["ID", "标题", "寄信人", "收信人", "寄出日期", "寄出地点", "私密", "修复状态"]


def _make_stat_card(key, label, color, stats):
    frame = QFrame()
    frame.setFixedHeight(90)
    frame.setStyleSheet(f"""
        QFrame {{
            background: {color};
            border-radius: 10px;
            padding: 10px 16px;
        }}
    """)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(4)
    val_label = QLabel(str(stats.get(key, 0)))
    val_label.setStyleSheet("font-size:26px; font-weight:bold; color:#fff; border:none;")
    val_label.setAlignment(Qt.AlignCenter)
    name_label = QLabel(label)
    name_label.setStyleSheet("font-size:13px; color:rgba(255,255,255,0.85); border:none;")
    name_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(val_label)
    layout.addWidget(name_label)
    return frame


class TimelineChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._data = []

    def set_data(self, data):
        self._data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        margin_l, margin_r, margin_t, margin_b = 50, 20, 30, 40
        chart_w = w - margin_l - margin_r
        chart_h = h - margin_t - margin_b

        painter.fillRect(self.rect(), QColor("#2B2D42"))

        font = QFont("Microsoft YaHei", 9)
        painter.setFont(font)
        painter.setPen(QColor("#8D99AE"))
        painter.drawText(5, 20, "书信年份分布")

        if not self._data:
            painter.setPen(QColor("#8D99AE"))
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无数据")
            painter.end()
            return

        max_cnt = max(d["cnt"] for d in self._data)
        if max_cnt == 0:
            max_cnt = 1
        bar_count = len(self._data)
        bar_gap = 6
        bar_w = max(8, min(40, (chart_w - bar_gap * (bar_count - 1)) // bar_count))

        total_bars_width = bar_count * bar_w + (bar_count - 1) * bar_gap
        start_x = margin_l + (chart_w - total_bars_width) // 2

        for i, item in enumerate(self._data):
            x = start_x + i * (bar_w + bar_gap)
            ratio = item["cnt"] / max_cnt
            bar_h = int(ratio * chart_h)
            y = margin_t + chart_h - bar_h

            grad_color = QColor("#E07A5F")
            painter.setBrush(QBrush(grad_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), bar_w, bar_h, 3, 3)

            painter.setPen(QColor("#EDF2F4"))
            painter.setFont(QFont("Microsoft YaHei", 8))
            if bar_h > 20:
                painter.drawText(int(x), int(y) + 4, bar_w, 18,
                                 Qt.AlignCenter, str(item["cnt"]))

            painter.setPen(QColor("#8D99AE"))
            painter.setFont(QFont("Microsoft YaHei", 7))
            year_text = item["year"] if len(item["year"]) == 4 else item["year"]
            painter.drawText(int(x) - 4, margin_t + chart_h + 6, bar_w + 8, 20,
                             Qt.AlignCenter, year_text)

        painter.setPen(QPen(QColor("#8D99AE"), 1, Qt.DotLine))
        for step in range(1, 5):
            gy = margin_t + chart_h - int(chart_h * step / 4)
            painter.drawLine(margin_l, gy, w - margin_r, gy)
            painter.setPen(QColor("#8D99AE"))
            painter.setFont(QFont("Microsoft YaHei", 7))
            painter.drawText(2, gy - 4, margin_l - 6, 16,
                             Qt.AlignRight | Qt.AlignVCenter,
                             str(int(max_cnt * step / 4)))

        painter.end()


class LetterDetailDialog(QDialog):
    def __init__(self, letter_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"书信详情 - {letter_data.get('title', '')}")
        self.setMinimumSize(480, 400)
        self.setStyleSheet("""
            QDialog {
                background: #2B2D42;
                color: #EDF2F4;
            }
            QLabel { border: none; }
        """)
        layout = QVBoxLayout(self)
        fields = [
            ("标题", "title"), ("寄信人", "sender_name"),
            ("收信人", "receiver_name"), ("寄出日期", "send_date"),
            ("寄出地点", "send_location"), ("收信地点", "receive_location"),
            ("私密", "is_private"), ("修复状态", "restoration_status"),
            ("分类", "category"), ("备注", "notes"),
        ]
        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (label, key) in enumerate(fields):
            lbl = QLabel(f"{label}：")
            lbl.setStyleSheet("font-weight:bold; color:#F2CC8F; font-size:13px;")
            val = QLabel(str(letter_data.get(key, "")))
            val.setStyleSheet("font-size:13px; color:#EDF2F4;")
            if key == "is_private":
                val.setText("是" if letter_data.get(key) == 1 else "否")
            val.setWordWrap(True)
            grid.addWidget(lbl, i, 0)
            grid.addWidget(val, i, 1)
        layout.addLayout(grid)

        content_label = QLabel("信件内容：")
        content_label.setStyleSheet("font-weight:bold; color:#F2CC8F; font-size:13px; margin-top:8px;")
        layout.addWidget(content_label)
        content = QLabel(str(letter_data.get("content", "")))
        content.setWordWrap(True)
        content.setStyleSheet("font-size:13px; color:#EDF2F4; background:#3D405B; "
                              "border-radius:6px; padding:10px;")
        layout.addWidget(content)

        btn = QPushButton("关闭")
        btn.setStyleSheet("""
            QPushButton {
                background: #E07A5F; color: #fff; border: none;
                border-radius: 6px; padding: 8px 24px; font-size: 13px;
            }
            QPushButton:hover { background: #c96a50; }
        """)
        btn.clicked.connect(self.close)
        layout.addWidget(btn, alignment=Qt.AlignRight)


class ArchiveOverview(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._letters = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none; background:#1E1F2E;}")

        container = QWidget()
        container.setStyleSheet("background:#1E1F2E;")
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(24, 20, 24, 20)
        self._container_layout.setSpacing(16)

        header_row = QHBoxLayout()
        title = QLabel("档案总览")
        title.setStyleSheet("font-size:22px; font-weight:bold; color:#EDF2F4; border:none;")
        header_row.addWidget(title)
        header_row.addStretch()
        self._refresh_btn = QPushButton("刷新数据")
        self._refresh_btn.setFixedSize(100, 34)
        self._refresh_btn.setStyleSheet("""
            QPushButton {
                background:#E07A5F; color:#fff; border:none;
                border-radius:6px; font-size:13px;
            }
            QPushButton:hover { background:#c96a50; }
        """)
        self._refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(self._refresh_btn)
        self._container_layout.addLayout(header_row)

        self._stats_row = QHBoxLayout()
        self._stats_row.setSpacing(14)
        self._container_layout.addLayout(self._stats_row)

        chart_label = QLabel("年份时间轴")
        chart_label.setStyleSheet("font-size:15px; font-weight:bold; color:#EDF2F4; border:none;")
        self._container_layout.addWidget(chart_label)

        self._timeline = TimelineChart()
        self._container_layout.addWidget(self._timeline)

        table_label = QLabel("书信列表")
        table_label.setStyleSheet("font-size:15px; font-weight:bold; color:#EDF2F4; border:none;")
        self._container_layout.addWidget(table_label)

        self._table = QTableWidget()
        self._table.setColumnCount(len(TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        self._table.setStyleSheet("""
            QTableWidget {
                background: #2B2D42; color: #EDF2F4;
                gridline-color: #3D405B; border: none;
                font-size: 13px;
                alternate-background-color: #33354A;
            }
            QTableWidget::item:selected {
                background: #E07A5F; color: #fff;
            }
            QHeaderView::section {
                background: #3D405B; color: #F2CC8F;
                border: none; padding: 6px; font-size: 13px;
                font-weight: bold;
            }
        """)
        self._table.verticalHeader().setVisible(False)
        self._container_layout.addWidget(self._table)

        scroll.setWidget(container)
        root.addWidget(scroll)

    def refresh(self):
        stats = get_statistics()
        self._rebuild_stat_cards(stats)
        timeline = get_timeline_data()
        self._timeline.set_data(timeline)
        self._load_letters()

    def _rebuild_stat_cards(self, stats):
        while self._stats_row.count():
            item = self._stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for key, label, color in STAT_CARDS:
            card = _make_stat_card(key, label, color, stats)
            self._stats_row.addWidget(card)

    def _load_letters(self):
        rows = execute_query_returning("""
            SELECT l.id, l.title, p1.name AS sender_name, p2.name AS receiver_name,
                   l.send_date, l.send_location, l.is_private, l.restoration_status
            FROM letters l
            LEFT JOIN people p1 ON l.sender_id = p1.id
            LEFT JOIN people p2 ON l.receiver_id = p2.id
            ORDER BY l.send_date DESC
        """)
        self._letters = rows
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                str(row.get("id", "")),
                str(row.get("title", "")),
                str(row.get("sender_name", "")),
                str(row.get("receiver_name", "")),
                str(row.get("send_date", "")),
                str(row.get("send_location", "")),
                "是" if row.get("is_private") == 1 else "否",
                str(row.get("restoration_status", "")),
            ]
            for c, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignCenter)
                if c == 6 and v == "是":
                    item.setForeground(QColor("#E07A5F"))
                if c == 7 and v == "需修复":
                    item.setForeground(QColor("#F2CC8F"))
                self._table.setItem(r, c, item)

    def _on_double_click(self, row, _col):
        if row < 0 or row >= len(self._letters):
            return
        letter = self._letters[row]
        full = execute_query_returning(
            "SELECT l.*, p1.name AS sender_name, p2.name AS receiver_name "
            "FROM letters l "
            "LEFT JOIN people p1 ON l.sender_id = p1.id "
            "LEFT JOIN people p2 ON l.receiver_id = p2.id "
            "WHERE l.id = ?",
            (letter["id"],)
        )
        if full:
            dlg = LetterDetailDialog(full[0], self)
            dlg.exec_()

    def _show_context_menu(self, pos):
        row = self._table.rowAt(pos.y())
        if row < 0 or row >= len(self._letters):
            return
        letter = self._letters[row]
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2B2D42; color: #EDF2F4;
                border: 1px solid #3D405B; padding: 4px;
            }
            QMenu::item:selected {
                background: #E07A5F;
            }
        """)

        toggle_text = "取消私密" if letter.get("is_private") == 1 else "标记私密"
        toggle_action = menu.addAction(toggle_text)
        delete_action = menu.addAction("删除信件")

        action = menu.exec_(self._table.viewport().mapToGlobal(pos))
        if action == toggle_action:
            new_val = 0 if letter.get("is_private") == 1 else 1
            execute_update("UPDATE letters SET is_private = ? WHERE id = ?",
                           (new_val, letter["id"]))
            self.refresh()
            self.data_changed.emit()
        elif action == delete_action:
            confirm = QMessageBox.question(
                self, "确认删除",
                f"确定要删除信件「{letter.get('title', '')}」吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                execute_update("DELETE FROM letters WHERE id = ?",
                               (letter["id"],))
                self.refresh()
                self.data_changed.emit()
