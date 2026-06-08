import os
import shutil
from datetime import datetime

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from PIL import Image

from database import execute_query, execute_query_returning, execute_update

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")
ENVELOPES_DIR = os.path.join(DATA_DIR, "envelopes")

for d in [PHOTOS_DIR, ENVELOPES_DIR]:
    os.makedirs(d, exist_ok=True)

STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 13px;
    color: #2c3e50;
}
QGroupBox {
    font-weight: bold;
    font-size: 14px;
    border: 2px solid #bdc3c7;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 18px;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 6px;
    color: #2c3e50;
}
QLineEdit, QComboBox, QDateEdit, QTextEdit {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    padding: 6px 10px;
    background-color: #fdfdfd;
    selection-background-color: #3498db;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {
    border: 1px solid #3498db;
}
QPushButton {
    border: none;
    border-radius: 4px;
    padding: 8px 18px;
    font-weight: bold;
    color: #ffffff;
    background-color: #3498db;
}
QPushButton:hover {
    background-color: #2980b9;
}
QPushButton:pressed {
    background-color: #21618c;
}
QPushButton#btnClear {
    background-color: #95a5a6;
}
QPushButton#btnClear:hover {
    background-color: #7f8c8d;
}
QPushButton#btnSave {
    background-color: #27ae60;
    font-size: 15px;
    padding: 10px 30px;
}
QPushButton#btnSave:hover {
    background-color: #219a52;
}
QPushButton#btnRemove {
    background-color: #e74c3c;
    padding: 3px 8px;
    font-size: 11px;
}
QPushButton#btnRemove:hover {
    background-color: #c0392b;
}
QPushButton#btnAddPerson {
    background-color: #8e44ad;
    padding: 4px 10px;
    font-size: 12px;
}
QPushButton#btnAddPerson:hover {
    background-color: #7d3c98;
}
QLabel {
    color: #34495e;
}
QScrollArea {
    border: 1px solid #dce1e5;
    border-radius: 4px;
    background-color: #f8f9fa;
}
"""


class ThumbnailWidget(QWidget):
    removed = pyqtSignal(int)

    def __init__(self, image_path, index, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.index = index
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        pixmap = self._load_thumbnail(self.image_path, 120, 90)
        lbl = QLabel()
        lbl.setPixmap(pixmap)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedSize(124, 94)
        lbl.setStyleSheet("border: 1px solid #dce1e5; border-radius: 3px; background: #fff;")
        layout.addWidget(lbl, alignment=Qt.AlignCenter)

        btn = QPushButton("✕ 移除")
        btn.setObjectName("btnRemove")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.removed.emit(self.index))
        layout.addWidget(btn, alignment=Qt.AlignCenter)

    @staticmethod
    def _load_thumbnail(path, w, h):
        try:
            img = Image.open(path)
            img.thumbnail((w, h), Image.LANCZOS)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimg)
        except Exception:
            return QPixmap(w, h)


class EnvelopeItemWidget(QWidget):
    removed = pyqtSignal(int)

    def __init__(self, image_path, item_type, description, index, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.item_type = item_type
        self.description = description
        self.index = index
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        pixmap = ThumbnailWidget._load_thumbnail(self.image_path, 48, 48)
        lbl_img = QLabel()
        lbl_img.setPixmap(pixmap)
        lbl_img.setFixedSize(52, 52)
        lbl_img.setStyleSheet("border: 1px solid #dce1e5; border-radius: 3px;")
        layout.addWidget(lbl_img)

        lbl_type = QLabel(f"[{self.item_type}]")
        lbl_type.setFixedWidth(60)
        lbl_type.setStyleSheet("font-weight: bold; color: #8e44ad;")
        layout.addWidget(lbl_type)

        lbl_desc = QLabel(self.description or os.path.basename(self.image_path))
        lbl_desc.setStyleSheet("color: #555;")
        layout.addWidget(lbl_desc, 1)

        btn = QPushButton("✕")
        btn.setObjectName("btnRemove")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedWidth(36)
        btn.clicked.connect(lambda: self.removed.emit(self.index))
        layout.addWidget(btn)


class ScanImportWindow(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.photo_paths = []
        self.envelope_data = []
        self._setup_ui()
        self._load_people()
        self.setStyleSheet(STYLESHEET)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        title_label = QLabel("扫描导入 - 家书录入")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50; padding: 4px 0;")
        main_layout.addWidget(title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setSpacing(14)

        self._build_letter_form()
        self._build_photo_section()
        self._build_envelope_section()
        self._build_ocr_section()
        self._build_action_buttons()

        self.content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

    def _build_letter_form(self):
        group = QGroupBox("信件信息")
        form = QGridLayout(group)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        row = 0
        form.addWidget(QLabel("标题："), row, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("请输入信件标题")
        form.addWidget(self.title_edit, row, 1, 1, 5)

        row += 1
        form.addWidget(QLabel("寄信人："), row, 0)
        sender_layout = QHBoxLayout()
        self.sender_combo = QComboBox()
        self.sender_combo.setEditable(True)
        self.sender_combo.setPlaceholderText("选择或输入寄信人")
        sender_layout.addWidget(self.sender_combo, 1)
        btn_add_sender = QPushButton("＋ 新增")
        btn_add_sender.setObjectName("btnAddPerson")
        btn_add_sender.setCursor(Qt.PointingHandCursor)
        btn_add_sender.clicked.connect(lambda: self._add_person(self.sender_combo))
        sender_layout.addWidget(btn_add_sender)
        form.addLayout(sender_layout, row, 1, 1, 5)

        row += 1
        form.addWidget(QLabel("收信人："), row, 0)
        receiver_layout = QHBoxLayout()
        self.receiver_combo = QComboBox()
        self.receiver_combo.setEditable(True)
        self.receiver_combo.setPlaceholderText("选择或输入收信人")
        receiver_layout.addWidget(self.receiver_combo, 1)
        btn_add_receiver = QPushButton("＋ 新增")
        btn_add_receiver.setObjectName("btnAddPerson")
        btn_add_receiver.setCursor(Qt.PointingHandCursor)
        btn_add_receiver.clicked.connect(lambda: self._add_person(self.receiver_combo))
        receiver_layout.addWidget(btn_add_receiver)
        form.addLayout(receiver_layout, row, 1, 1, 5)

        row += 1
        form.addWidget(QLabel("寄出日期："), row, 0)
        self.send_date_edit = QDateEdit()
        self.send_date_edit.setCalendarPopup(True)
        self.send_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.send_date_edit.setDate(QDate.currentDate())
        form.addWidget(self.send_date_edit, row, 1, 1, 2)

        form.addWidget(QLabel("收到日期："), row, 3)
        self.receive_date_edit = QDateEdit()
        self.receive_date_edit.setCalendarPopup(True)
        self.receive_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.receive_date_edit.setDate(QDate.currentDate())
        form.addWidget(self.receive_date_edit, row, 4, 1, 2)

        row += 1
        form.addWidget(QLabel("寄出地点："), row, 0)
        self.send_location_edit = QLineEdit()
        self.send_location_edit.setPlaceholderText("如：北京")
        form.addWidget(self.send_location_edit, row, 1, 1, 2)

        form.addWidget(QLabel("收到地点："), row, 3)
        self.receive_location_edit = QLineEdit()
        self.receive_location_edit.setPlaceholderText("如：上海")
        form.addWidget(self.receive_location_edit, row, 4, 1, 2)

        row += 1
        form.addWidget(QLabel("分类："), row, 0)
        self.category_combo = QComboBox()
        self.category_combo.addItems(["家书", "公务", "其他"])
        form.addWidget(self.category_combo, row, 1, 1, 2)

        row += 1
        form.addWidget(QLabel("备注："), row, 0)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("补充说明（可选）")
        self.notes_edit.setFixedHeight(70)
        form.addWidget(self.notes_edit, row, 1, 1, 5)

        self.content_layout.addWidget(group)

    def _build_photo_section(self):
        group = QGroupBox("批量导入照片")
        layout = QVBoxLayout(group)

        btn_row = QHBoxLayout()
        btn_import = QPushButton("📁 选择照片文件")
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.clicked.connect(self._select_photos)
        btn_row.addWidget(btn_import)
        self.photo_count_label = QLabel("已选 0 张")
        self.photo_count_label.setStyleSheet("color: #7f8c8d;")
        btn_row.addStretch()
        btn_row.addWidget(self.photo_count_label)
        layout.addLayout(btn_row)

        self.photo_scroll = QScrollArea()
        self.photo_scroll.setFixedHeight(150)
        self.photo_scroll.setWidgetResizable(True)
        self.photo_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.photo_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.photo_container = QWidget()
        self.photo_container_layout = QHBoxLayout(self.photo_container)
        self.photo_container_layout.setContentsMargins(6, 6, 6, 6)
        self.photo_container_layout.setSpacing(8)
        self.photo_container_layout.addStretch()
        self.photo_scroll.setWidget(self.photo_container)
        layout.addWidget(self.photo_scroll)

        self.content_layout.addWidget(group)

    def _build_envelope_section(self):
        group = QGroupBox("信封票据")
        layout = QVBoxLayout(group)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("📨 添加信封/票据图片")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._add_envelope_image)
        btn_row.addWidget(btn_add)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.envelope_list = QVBoxLayout()
        self.envelope_list.setSpacing(4)
        layout.addLayout(self.envelope_list)

        self.envelope_empty_label = QLabel("暂无信封票据图片")
        self.envelope_empty_label.setStyleSheet("color: #bdc3c7; padding: 12px; font-style: italic;")
        self.envelope_list.addWidget(self.envelope_empty_label)

        self.content_layout.addWidget(group)

    def _build_ocr_section(self):
        group = QGroupBox("OCR 识别")
        layout = QVBoxLayout(group)

        btn_ocr = QPushButton("🔍 开始 OCR 识别")
        btn_ocr.setCursor(Qt.PointingHandCursor)
        btn_ocr.clicked.connect(self._run_ocr)
        layout.addWidget(btn_ocr)

        self.ocr_result_edit = QTextEdit()
        self.ocr_result_edit.setPlaceholderText("OCR 识别结果将显示在此处...")
        self.ocr_result_edit.setFixedHeight(150)
        layout.addWidget(self.ocr_result_edit)

        self.content_layout.addWidget(group)

    def _build_action_buttons(self):
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_clear = QPushButton("清空表单")
        btn_clear.setObjectName("btnClear")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_form)
        btn_layout.addWidget(btn_clear)

        btn_save = QPushButton("💾 保存信件")
        btn_save.setObjectName("btnSave")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save_letter)
        btn_layout.addWidget(btn_save)

        self.content_layout.addLayout(btn_layout)

    def _load_people(self):
        people = execute_query_returning("SELECT id, name FROM people ORDER BY name")
        for combo in (self.sender_combo, self.receiver_combo):
            combo.clear()
            for p in people:
                combo.addItem(p["name"], p["id"])

    def _add_person(self, combo):
        name, ok = QInputDialog.getText(self, "新增人物", "请输入姓名：")
        if ok and name.strip():
            name = name.strip()
            existing = execute_query_returning("SELECT id FROM people WHERE name = ?", (name,))
            if existing:
                idx = combo.findText(name)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                return
            person_id = execute_query("INSERT INTO people (name) VALUES (?)", (name,))
            combo.addItem(name, person_id)
            combo.setCurrentIndex(combo.count() - 1)
            other = self.receiver_combo if combo is self.sender_combo else self.sender_combo
            if other.findText(name) < 0:
                other.addItem(name, person_id)

    def _select_photos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择照片文件", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp);;所有文件 (*)"
        )
        if files:
            self.photo_paths.extend(files)
            self._refresh_photo_thumbnails()

    def _refresh_photo_thumbnails(self):
        while self.photo_container_layout.count() > 1:
            item = self.photo_container_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for i, path in enumerate(self.photo_paths):
            tw = ThumbnailWidget(path, i)
            tw.removed.connect(self._remove_photo)
            self.photo_container_layout.insertWidget(self.photo_container_layout.count() - 1, tw)

        self.photo_count_label.setText(f"已选 {len(self.photo_paths)} 张")

    def _remove_photo(self, index):
        if 0 <= index < len(self.photo_paths):
            self.photo_paths.pop(index)
            self._refresh_photo_thumbnails()

    def _add_envelope_image(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择信封/票据图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp);;所有文件 (*)"
        )
        if not files:
            return

        types = ["信封", "邮票", "邮戳", "其他"]
        for fpath in files:
            item_type, ok = QInputDialog.getItem(
                self, "选择类型",
                f"请选择「{os.path.basename(fpath)}」的类型：",
                types, 0, False
            )
            if not ok:
                item_type = "其他"

            desc, ok2 = QInputDialog.getText(
                self, "描述",
                f"请输入「{os.path.basename(fpath)}」的描述（可留空）："
            )
            desc = desc.strip() if ok2 else ""
            self.envelope_data.append({
                "path": fpath,
                "type": item_type,
                "description": desc,
            })

        self._refresh_envelope_list()

    def _refresh_envelope_list(self):
        while self.envelope_list.count():
            item = self.envelope_list.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.envelope_data:
            lbl = QLabel("暂无信封票据图片")
            lbl.setStyleSheet("color: #bdc3c7; padding: 12px; font-style: italic;")
            self.envelope_list.addWidget(lbl)
            return

        for i, edata in enumerate(self.envelope_data):
            ew = EnvelopeItemWidget(edata["path"], edata["type"], edata["description"], i)
            ew.removed.connect(self._remove_envelope)
            self.envelope_list.addWidget(ew)

    def _remove_envelope(self, index):
        if 0 <= index < len(self.envelope_data):
            self.envelope_data.pop(index)
            self._refresh_envelope_list()

    def _run_ocr(self):
        if not self.photo_paths:
            QMessageBox.information(self, "提示", "请先导入照片后再进行 OCR 识别。")
            return

        try:
            import pytesseract
            has_tesseract = True
        except ImportError:
            has_tesseract = False

        if has_tesseract:
            all_text = []
            for path in self.photo_paths:
                try:
                    img = Image.open(path)
                    text = pytesseract.image_to_string(img, lang="chi_sim+eng")
                    all_text.append(text.strip())
                except Exception as e:
                    all_text.append(f"[识别失败: {e}]")
            self.ocr_result_edit.setPlainText("\n\n---\n\n".join(all_text))
        else:
            self.ocr_result_edit.setPlainText(
                "【OCR 占位文本】\n\n"
                "未检测到 pytesseract 库，以下为模拟识别结果：\n\n"
                "父亲大人膝下：\n"
                "敬禀者，男自离乡以来，日夜思念。今特托人带回家书一封，\n"
                "望大人保重身体，勿念。家中大小事务，还请多操劳。\n"
                "男在外一切安好，请勿挂念。\n\n"
                "此致\n敬礼\n\n"
                "儿 某某  敬上\n"
                "民国三十五年三月十五日\n\n"
                "---\n"
                "提示：安装 pytesseract 并配置 Tesseract-OCR 后可启用真实识别功能。"
            )

    def _save_letter(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "提示", "请输入信件标题。")
            self.title_edit.setFocus()
            return

        sender_id = self._get_person_id(self.sender_combo)
        receiver_id = self._get_person_id(self.receiver_combo)

        send_date = self.send_date_edit.date().toString("yyyy-MM-dd")
        receive_date = self.receive_date_edit.date().toString("yyyy-MM-dd")
        send_location = self.send_location_edit.text().strip()
        receive_location = self.receive_location_edit.text().strip()
        category = self.category_combo.currentText()
        notes = self.notes_edit.toPlainText().strip()
        raw_ocr = self.ocr_result_edit.toPlainText().strip()

        letter_id = execute_query(
            "INSERT INTO letters "
            "(title, sender_id, receiver_id, send_date, receive_date, "
            "send_location, receive_location, category, notes, raw_ocr_text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (title, sender_id, receiver_id, send_date, receive_date,
             send_location, receive_location, category, notes, raw_ocr)
        )

        saved_photos = 0
        for i, src_path in enumerate(self.photo_paths):
            try:
                ext = os.path.splitext(src_path)[1] or ".jpg"
                dest_name = f"letter_{letter_id}_photo_{i+1}{ext}"
                dest_path = os.path.join(PHOTOS_DIR, dest_name)
                shutil.copy2(src_path, dest_path)
                execute_query(
                    "INSERT INTO photos (letter_id, file_path, is_primary) VALUES (?, ?, ?)",
                    (letter_id, dest_path, 1 if i == 0 else 0)
                )
                saved_photos += 1
            except Exception as e:
                print(f"保存照片失败 [{src_path}]: {e}")

        saved_envelopes = 0
        for i, edata in enumerate(self.envelope_data):
            try:
                ext = os.path.splitext(edata["path"])[1] or ".jpg"
                dest_name = f"letter_{letter_id}_env_{i+1}{ext}"
                dest_path = os.path.join(ENVELOPES_DIR, dest_name)
                shutil.copy2(edata["path"], dest_path)
                execute_query(
                    "INSERT INTO envelopes (letter_id, item_type, image_path, description) "
                    "VALUES (?, ?, ?, ?)",
                    (letter_id, edata["type"], dest_path, edata["description"])
                )
                saved_envelopes += 1
            except Exception as e:
                print(f"保存信封票据失败 [{edata['path']}]: {e}")

        QMessageBox.information(
            self, "保存成功",
            f"信件「{title}」已保存！\n"
            f"关联照片：{saved_photos} 张\n"
            f"信封票据：{saved_envelopes} 项"
        )
        self._clear_form()
        self.data_changed.emit()

    def _get_person_id(self, combo):
        text = combo.currentText().strip()
        if not text:
            return None
        idx = combo.currentIndex()
        if idx >= 0:
            pid = combo.itemData(idx)
            if pid and combo.currentText() == text:
                return pid
        existing = execute_query_returning("SELECT id FROM people WHERE name = ?", (text,))
        if existing:
            return existing[0]["id"]
        new_id = execute_query("INSERT INTO people (name) VALUES (?)", (text,))
        self._load_people()
        return new_id

    def refresh(self):
        self._load_people()

    def _clear_form(self):
        self.title_edit.clear()
        self.sender_combo.setCurrentIndex(-1)
        self.sender_combo.clearEditText()
        self.receiver_combo.setCurrentIndex(-1)
        self.receiver_combo.clearEditText()
        self.send_date_edit.setDate(QDate.currentDate())
        self.receive_date_edit.setDate(QDate.currentDate())
        self.send_location_edit.clear()
        self.receive_location_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.notes_edit.clear()
        self.ocr_result_edit.clear()
        self.photo_paths.clear()
        self._refresh_photo_thumbnails()
        self.envelope_data.clear()
        self._refresh_envelope_list()
