import os
import base64
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QGridLayout, QDialog, QFormLayout, QLineEdit,
    QTextEdit, QComboBox, QScrollArea, QMessageBox, QFileDialog,
    QSizePolicy, QFrame, QSplitter
)
from PyQt5.QtCore import Qt, QSize, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QLinearGradient

from database import execute_query, execute_query_returning, execute_update

STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 13px;
    color: #2c3e50;
}
QListWidget {
    background: #ffffff;
    border: 1px solid #dce1e8;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}
QListWidget::item {
    padding: 10px 8px;
    border-bottom: 1px solid #eef0f4;
    border-radius: 4px;
}
QListWidget::item:selected {
    background: #e8f4fd;
    color: #1a73e8;
}
QListWidget::item:hover {
    background: #f5f8fc;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4a90d9, stop:1 #357abd);
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 7px 18px;
    font-weight: 500;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #5a9fe9, stop:1 #4589cd);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #357abd, stop:1 #2a6aad);
}
QPushButton#btnDelete {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #e74c3c, stop:1 #c0392b);
}
QPushButton#btnDelete:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f05a4a, stop:1 #d0443a);
}
QPushButton#btnTimeline {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #27ae60, stop:1 #1e8e4e);
}
QPushButton#btnTimeline:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2ecc71, stop:1 #27ae60);
}
QPushButton#btnExport {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #8e44ad, stop:1 #71368a);
}
QPushButton#btnExport:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #9b59b6, stop:1 #8e44ad);
}
QLabel#sectionTitle {
    font-size: 16px;
    font-weight: bold;
    color: #1a73e8;
    padding: 6px 0;
}
QLabel#albumDetailLabel {
    font-size: 14px;
    color: #34495e;
    padding: 2px 0;
}
QScrollArea {
    border: none;
    background: transparent;
}
QFrame#photoCard {
    background: #ffffff;
    border: 1px solid #e0e4ea;
    border-radius: 8px;
    padding: 6px;
}
QLineEdit, QTextEdit, QComboBox {
    border: 1px solid #dce1e8;
    border-radius: 5px;
    padding: 6px 10px;
    background: #ffffff;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border-color: #4a90d9;
}
"""


class CreateAlbumDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建纪念册")
        self.setMinimumWidth(380)
        self.setStyleSheet(STYLESHEET)
        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入纪念册名称")
        layout.addRow("纪念册名称：", self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("请输入纪念册描述（可选）")
        self.desc_edit.setMaximumHeight(100)
        layout.addRow("描述：", self.desc_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("创建")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("background: #95a5a6;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip()
        }


class AddItemDialog(QDialog):
    def __init__(self, album_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加条目")
        self.setMinimumWidth(400)
        self.setStyleSheet(STYLESHEET)
        self.album_id = album_id
        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.type_combo = QComboBox()
        self.type_combo.addItem("信件", "letter")
        self.type_combo.addItem("照片", "photo")
        self.type_combo.currentIndexChanged.connect(self._refresh_items)
        layout.addRow("条目类型：", self.type_combo)

        self.item_combo = QComboBox()
        layout.addRow("选择条目：", self.item_combo)

        self.caption_edit = QLineEdit()
        self.caption_edit.setPlaceholderText("请输入条目标题/说明（可选）")
        layout.addRow("说明：", self.caption_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("添加")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("background: #95a5a6;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        self._refresh_items()

    def _refresh_items(self):
        self.item_combo.clear()
        item_type = self.type_combo.currentData()
        if item_type == "letter":
            rows = execute_query_returning(
                "SELECT id, title, send_date FROM letters ORDER BY send_date DESC"
            )
            for r in rows:
                title = r["title"] or "无标题"
                date = r["send_date"] or ""
                self.item_combo.addItem(
                    f"[{r['id']}] {title} ({date})" if date else f"[{r['id']}] {title}",
                    r["id"]
                )
        else:
            rows = execute_query_returning(
                "SELECT id, file_path, description FROM photos ORDER BY id DESC"
            )
            for r in rows:
                desc = r["description"] or os.path.basename(r["file_path"] or "")
                self.item_combo.addItem(f"[{r['id']}] {desc}", r["id"])

    def get_data(self):
        return {
            "item_type": self.type_combo.currentData(),
            "item_id": self.item_combo.currentData(),
            "caption": self.caption_edit.text().strip()
        }


class TimelineWidget(QWidget):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.timeline_data = data or []
        self.setMinimumHeight(200)

    def set_data(self, data):
        self.timeline_data = data or []
        self.update()

    def paintEvent(self, event):
        if not self.timeline_data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        center_x = 60
        top_y = 20
        bottom_y = h - 20

        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, QColor(74, 144, 217, 30))
        gradient.setColorAt(1, QColor(74, 144, 217, 10))
        painter.fillRect(self.rect(), gradient)

        pen_line = QPen(QColor(74, 144, 217), 3)
        painter.setPen(pen_line)
        painter.drawLine(center_x, top_y, center_x, bottom_y)

        years = sorted(set(item["year"] for item in self.timeline_data))
        if not years:
            painter.end()
            return

        n = len(years)
        segment = (bottom_y - top_y) / max(n, 1)

        font_year = QFont("Microsoft YaHei", 11, QFont.Bold)
        font_title = QFont("Microsoft YaHei", 9)

        for i, year in enumerate(years):
            y = top_y + i * segment + segment / 2

            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QColor(74, 144, 217))
            painter.drawEllipse(QPoint(center_x, int(y)), 8, 8)

            painter.setPen(QColor(26, 115, 232))
            painter.setFont(font_year)
            painter.drawText(8, int(y) - 12, 50, 24, Qt.AlignRight | Qt.AlignVCenter, str(year))

            items_for_year = [it for it in self.timeline_data if it["year"] == year]
            painter.setPen(QColor(52, 73, 94))
            painter.setFont(font_title)
            tx = center_x + 20
            for j, item in enumerate(items_for_year):
                ty = int(y) - 12 + j * 20
                if ty > bottom_y - 10:
                    break
                painter.drawText(tx, ty, w - tx - 10, 18, Qt.AlignLeft | Qt.AlignVCenter, item.get("title", ""))

        painter.end()


class AlbumWindow(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_album_id = None
        self._setup_ui()
        self.setStyleSheet(STYLESHEET)
        self._load_albums()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        title_label = QLabel("专题相册")
        title_label.setStyleSheet("font-size:20px; font-weight:bold; color:#1a73e8; padding:4px 0;")
        main_layout.addWidget(title_label)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        section_label = QLabel("纪念册管理")
        section_label.setObjectName("sectionTitle")
        left_layout.addWidget(section_label)

        self.album_list = QListWidget()
        self.album_list.currentRowChanged.connect(self._on_album_selected)
        left_layout.addWidget(self.album_list)

        btn_row = QHBoxLayout()
        create_btn = QPushButton("创建纪念册")
        create_btn.clicked.connect(self._create_album)
        btn_row.addWidget(create_btn)

        delete_album_btn = QPushButton("删除纪念册")
        delete_album_btn.setObjectName("btnDelete")
        delete_album_btn.clicked.connect(self._delete_album)
        btn_row.addWidget(delete_album_btn)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)

        self.detail_label = QLabel("请选择一个纪念册")
        self.detail_label.setObjectName("albumDetailLabel")
        right_layout.addWidget(self.detail_label)

        detail_btn_row = QHBoxLayout()
        add_item_btn = QPushButton("添加条目")
        add_item_btn.clicked.connect(self._add_item)
        detail_btn_row.addWidget(add_item_btn)

        delete_item_btn = QPushButton("删除条目")
        delete_item_btn.setObjectName("btnDelete")
        delete_item_btn.clicked.connect(self._delete_item)
        detail_btn_row.addWidget(delete_item_btn)

        timeline_btn = QPushButton("时间轴生成")
        timeline_btn.setObjectName("btnTimeline")
        timeline_btn.clicked.connect(self._generate_timeline)
        detail_btn_row.addWidget(timeline_btn)

        export_btn = QPushButton("导出相册")
        export_btn.setObjectName("btnExport")
        export_btn.clicked.connect(self._export_album)
        detail_btn_row.addWidget(export_btn)

        detail_btn_row.addStretch()
        right_layout.addLayout(detail_btn_row)

        self.photo_scroll = QScrollArea()
        self.photo_scroll.setWidgetResizable(True)
        self.photo_container = QWidget()
        self.photo_grid_layout = QGridLayout(self.photo_container)
        self.photo_grid_layout.setSpacing(10)
        self.photo_grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.photo_scroll.setWidget(self.photo_container)
        right_layout.addWidget(self.photo_scroll, 1)

        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_container = QWidget()
        self.timeline_container_layout = QVBoxLayout(self.timeline_container)
        self.timeline_container_layout.setAlignment(Qt.AlignTop)
        self.timeline_scroll.setWidget(self.timeline_container)
        self.timeline_scroll.setVisible(False)
        right_layout.addWidget(self.timeline_scroll, 1)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter, 1)

        global_section = QLabel("年份时间轴")
        global_section.setObjectName("sectionTitle")
        main_layout.addWidget(global_section)

        self.global_timeline = TimelineWidget()
        self.global_timeline.setMinimumHeight(220)
        self.global_timeline.setMaximumHeight(350)
        main_layout.addWidget(self.global_timeline)

        self._load_global_timeline()

    def _load_albums(self):
        self.album_list.clear()
        rows = execute_query_returning(
            "SELECT id, name, description, created_at FROM albums ORDER BY created_at DESC"
        )
        for r in rows:
            item = QListWidgetItem(r["name"])
            item.setData(Qt.UserRole, r["id"])
            item.setToolTip(f"创建于 {r['created_at']}\n{r['description'] or ''}")
            self.album_list.addItem(item)
        if self.album_list.count() > 0:
            self.album_list.setCurrentRow(0)

    def _on_album_selected(self, row):
        if row < 0:
            self.current_album_id = None
            self.detail_label.setText("请选择一个纪念册")
            self._clear_photo_grid()
            return
        item = self.album_list.item(row)
        self.current_album_id = item.data(Qt.UserRole)
        self._load_album_detail()
        self.timeline_scroll.setVisible(False)
        self.photo_scroll.setVisible(True)

    def _load_album_detail(self):
        if not self.current_album_id:
            return
        rows = execute_query_returning(
            "SELECT name, description, created_at FROM albums WHERE id = ?",
            (self.current_album_id,)
        )
        if not rows:
            return
        album = rows[0]
        desc = album["description"] or "无描述"
        self.detail_label.setText(
            f"📖 {album['name']}  |  {desc}  |  创建于 {album['created_at']}"
        )
        self._load_photo_grid()

    def _clear_photo_grid(self):
        while self.photo_grid_layout.count():
            child = self.photo_grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _load_photo_grid(self):
        self._clear_photo_grid()
        if not self.current_album_id:
            return

        items = execute_query_returning(
            """SELECT ai.id, ai.caption, ai.letter_id, ai.photo_id,
                      l.title AS letter_title, l.send_date,
                      p.file_path AS photo_path, p.description AS photo_desc
               FROM album_items ai
               LEFT JOIN letters l ON ai.letter_id = l.id
               LEFT JOIN photos p ON ai.photo_id = p.id
               WHERE ai.album_id = ?
               ORDER BY ai.sort_order, ai.id""",
            (self.current_album_id,)
        )

        cols = 4
        for i, item in enumerate(items):
            card = QFrame()
            card.setObjectName("photoCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(4, 4, 4, 4)
            card_layout.setSpacing(4)

            img_label = QLabel()
            img_label.setFixedSize(140, 140)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setStyleSheet("background:#f0f2f5; border-radius:6px;")

            pixmap_loaded = False
            if item["photo_id"] and item["photo_path"]:
                pm = QPixmap(item["photo_path"])
                if not pm.isNull():
                    img_label.setPixmap(pm.scaled(
                        140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    ))
                    pixmap_loaded = True

            if not pixmap_loaded:
                if item["letter_id"]:
                    img_label.setText("✉️ 信件")
                    img_label.setStyleSheet(
                        "background:#e8f4fd; border-radius:6px; "
                        "font-size:20px; color:#4a90d9;"
                    )
                else:
                    img_label.setText("📎 条目")
                    img_label.setStyleSheet(
                        "background:#f5f5f5; border-radius:6px; "
                        "font-size:16px; color:#999;"
                    )

            card_layout.addWidget(img_label)

            caption = item["caption"]
            if not caption:
                if item["letter_title"]:
                    caption = item["letter_title"]
                elif item["photo_desc"]:
                    caption = item["photo_desc"]
                else:
                    caption = "未命名"
            cap_label = QLabel(caption)
            cap_label.setWordWrap(True)
            cap_label.setMaximumWidth(140)
            cap_label.setAlignment(Qt.AlignCenter)
            cap_label.setStyleSheet("font-size:11px; color:#555; padding:2px;")
            card_layout.addWidget(cap_label)

            if item["send_date"]:
                date_label = QLabel(item["send_date"])
                date_label.setAlignment(Qt.AlignCenter)
                date_label.setStyleSheet("font-size:10px; color:#999;")
                card_layout.addWidget(date_label)

            card.setData = item["id"]
            row = i // cols
            col = i % cols
            self.photo_grid_layout.addWidget(card, row, col)

    def _create_album(self):
        dlg = CreateAlbumDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["name"]:
            QMessageBox.warning(self, "提示", "纪念册名称不能为空")
            return
        execute_query(
            "INSERT INTO albums (name, description) VALUES (?, ?)",
            (data["name"], data["description"])
        )
        self._load_albums()
        self._load_global_timeline()

    def _delete_album(self):
        if not self.current_album_id:
            QMessageBox.information(self, "提示", "请先选择一个纪念册")
            return
        item = self.album_list.currentItem()
        name = item.text() if item else ""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除纪念册「{name}」吗？所有条目也将被删除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        execute_update("DELETE FROM albums WHERE id = ?", (self.current_album_id,))
        self.current_album_id = None
        self._load_albums()
        self._load_global_timeline()

    def _add_item(self):
        if not self.current_album_id:
            QMessageBox.information(self, "提示", "请先选择一个纪念册")
            return
        dlg = AddItemDialog(self.current_album_id, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["item_id"]:
            QMessageBox.warning(self, "提示", "请选择一个条目")
            return
        if data["item_type"] == "letter":
            execute_query(
                "INSERT INTO album_items (album_id, letter_id, caption) VALUES (?, ?, ?)",
                (self.current_album_id, data["item_id"], data["caption"])
            )
        else:
            execute_query(
                "INSERT INTO album_items (album_id, photo_id, caption) VALUES (?, ?, ?)",
                (self.current_album_id, data["item_id"], data["caption"])
            )
        self._load_photo_grid()

    def _delete_item(self):
        if not self.current_album_id:
            QMessageBox.information(self, "提示", "请先选择一个纪念册")
            return
        items = execute_query_returning(
            "SELECT ai.id, ai.caption, l.title AS letter_title, p.description AS photo_desc "
            "FROM album_items ai "
            "LEFT JOIN letters l ON ai.letter_id = l.id "
            "LEFT JOIN photos p ON ai.photo_id = p.id "
            "WHERE ai.album_id = ? ORDER BY ai.sort_order, ai.id",
            (self.current_album_id,)
        )
        if not items:
            QMessageBox.information(self, "提示", "当前纪念册没有条目")
            return
        names = []
        for it in items:
            label = it["caption"] or it["letter_title"] or it["photo_desc"] or f"条目#{it['id']}"
            names.append(label)
        name, ok = QComboBox().__class__.__mro__[0] and None, False
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(
            self, "删除条目", "选择要删除的条目：", names, 0, False
        )
        if not ok or not name:
            return
        idx = names.index(name)
        item_id = items[idx]["id"]
        execute_update("DELETE FROM album_items WHERE id = ?", (item_id,))
        self._load_photo_grid()

    def _generate_timeline(self):
        if not self.current_album_id:
            QMessageBox.information(self, "提示", "请先选择一个纪念册")
            return
        rows = execute_query_returning(
            """SELECT l.title, l.send_date,
                      substr(l.send_date, 1, 4) AS year
               FROM album_items ai
               JOIN letters l ON ai.letter_id = l.id
               WHERE ai.album_id = ? AND l.send_date IS NOT NULL AND l.send_date != ''
               ORDER BY l.send_date""",
            (self.current_album_id,)
        )
        if not rows:
            QMessageBox.information(self, "提示", "当前纪念册中没有含日期的信件，无法生成时间轴")
            return

        while self.timeline_container_layout.count():
            child = self.timeline_container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        years = sorted(set(r["year"] for r in rows))
        for year in years:
            year_label = QLabel(f"📅 {year} 年")
            year_label.setStyleSheet(
                "font-size:15px; font-weight:bold; color:#1a73e8; "
                "padding:8px 0 4px 12px; border-bottom:2px solid #4a90d9;"
            )
            self.timeline_container_layout.addWidget(year_label)

            year_items = [r for r in rows if r["year"] == year]
            for it in year_items:
                title = it["title"] or "无标题"
                date = it["send_date"] or ""
                entry = QLabel(f"    ✉️  {date}  —  {title}")
                entry.setStyleSheet(
                    "font-size:12px; color:#34495e; padding:3px 0 3px 24px;"
                )
                entry.setWordWrap(True)
                self.timeline_container_layout.addWidget(entry)

        self.photo_scroll.setVisible(False)
        self.timeline_scroll.setVisible(True)

    def _load_global_timeline(self):
        rows = execute_query_returning(
            """SELECT l.title, substr(l.send_date, 1, 4) AS year
               FROM album_items ai
               JOIN letters l ON ai.letter_id = l.id
               WHERE l.send_date IS NOT NULL AND l.send_date != ''
               ORDER BY year, l.send_date"""
        )
        self.global_timeline.set_data(rows)

    def _export_album(self):
        if not self.current_album_id:
            QMessageBox.information(self, "提示", "请先选择一个纪念册")
            return
        album_rows = execute_query_returning(
            "SELECT * FROM albums WHERE id = ?", (self.current_album_id,)
        )
        if not album_rows:
            return
        album = album_rows[0]

        items = execute_query_returning(
            """SELECT ai.caption, ai.letter_id, ai.photo_id,
                      l.title AS letter_title, l.content AS letter_content,
                      l.send_date, p.file_path AS photo_path, p.description AS photo_desc
               FROM album_items ai
               LEFT JOIN letters l ON ai.letter_id = l.id
               LEFT JOIN photos p ON ai.photo_id = p.id
               WHERE ai.album_id = ?
               ORDER BY ai.sort_order, ai.id""",
            (self.current_album_id,)
        )

        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出相册", f"{album['name']}.html", "HTML 文件 (*.html)"
        )
        if not save_path:
            return

        sections_html = ""
        for item in items:
            caption = item["caption"] or item["letter_title"] or item["photo_desc"] or "未命名"
            img_tag = ""
            if item["photo_path"] and os.path.isfile(item["photo_path"]):
                try:
                    with open(item["photo_path"], "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    ext = os.path.splitext(item["photo_path"])[1].lower()
                    mime = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".gif": "gif", ".bmp": "bmp"}.get(ext, "jpeg")
                    img_tag = f'<img src="data:image/{mime};base64,{b64}" style="max-width:300px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">'
                except Exception:
                    img_tag = '<div style="width:200px;height:150px;background:#f0f0f0;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#aaa;">图片无法加载</div>'
            elif item["letter_id"]:
                img_tag = '<div style="width:200px;height:150px;background:#e8f4fd;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:40px;">✉️</div>'

            date_str = item["send_date"] or ""
            date_html = f'<p style="color:#888;font-size:12px;">{date_str}</p>' if date_str else ""
            content_html = ""
            if item["letter_content"]:
                content_html = (
                    f'<div style="margin-top:8px;padding:10px;background:#fafafa;'
                    f'border-radius:6px;font-size:13px;color:#555;max-height:200px;overflow:auto;">'
                    f'{item["letter_content"][:500]}</div>'
                )

            sections_html += f"""
            <div style="background:#fff;border-radius:12px;padding:16px;margin:12px 0;
                        box-shadow:0 2px 12px rgba(0,0,0,0.06);display:inline-block;
                        vertical-align:top;width:280px;margin-right:16px;">
                {img_tag}
                <h3 style="margin:10px 0 4px;font-size:15px;color:#2c3e50;">{caption}</h3>
                {date_html}
                {content_html}
            </div>"""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{album['name']}</title>
<style>
body {{
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    background: #f5f7fa;
    margin: 0;
    padding: 20px;
    color: #2c3e50;
}}
.header {{
    text-align: center;
    padding: 30px 0;
    background: linear-gradient(135deg, #4a90d9, #357abd);
    color: #fff;
    border-radius: 12px;
    margin-bottom: 24px;
}}
.header h1 {{ font-size: 28px; margin: 0; }}
.header p {{ font-size: 14px; opacity: 0.85; margin-top: 8px; }}
.items {{ text-align: center; }}
</style>
</head>
<body>
<div class="header">
    <h1>{album['name']}</h1>
    <p>{album['description'] or ''}</p>
    <p style="font-size:12px;margin-top:4px;">创建于 {album['created_at']}</p>
</div>
<div class="items">
    {sections_html}
</div>
</body>
</html>"""

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "导出成功", f"相册已导出到：\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出时出错：\n{e}")

    def refresh(self):
        self._load_albums()
