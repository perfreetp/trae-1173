import math
import random
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QDialog, QFormLayout, QComboBox, QLineEdit, QTextEdit,
    QGroupBox, QHeaderView, QMessageBox, QAbstractItemView, QSizePolicy
)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from database import execute_query, execute_query_returning, execute_update

RELATION_TYPES = ["父子", "母子", "夫妻", "兄弟", "姐妹", "祖孙", "叔侄", "其他"]
GENDER_OPTIONS = ["男", "女", "未知"]

STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei", "SimHei", sans-serif;
    font-size: 13px;
    color: #2c3e50;
}
QGroupBox {
    font-weight: bold;
    font-size: 14px;
    border: 1px solid #bdc3c7;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #2c3e50;
}
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2980b9;
}
QPushButton:pressed {
    background-color: #21618c;
}
QPushButton#deleteBtn {
    background-color: #e74c3c;
}
QPushButton#deleteBtn:hover {
    background-color: #c0392b;
}
QTableWidget {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    gridline-color: #ecf0f1;
    selection-background-color: #d4e6f1;
    selection-color: #2c3e50;
}
QTableWidget::item {
    padding: 4px;
}
QHeaderView::section {
    background-color: #ecf0f1;
    font-weight: bold;
    border: none;
    border-bottom: 1px solid #bdc3c7;
    border-right: 1px solid #bdc3c7;
    padding: 5px;
}
QComboBox, QLineEdit, QTextEdit {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    padding: 5px;
    background: white;
}
QComboBox:focus, QLineEdit:focus, QTextEdit:focus {
    border-color: #3498db;
}
QDialog {
    background-color: #fdfefe;
}
QLabel#statLabel {
    font-size: 13px;
    padding: 4px 8px;
    background-color: #eaf2f8;
    border-radius: 4px;
}
"""


class AddPersonDialog(QDialog):
    def __init__(self, parent=None, person_data=None):
        super().__init__(parent)
        self.person_data = person_data
        self._init_ui()
        if person_data:
            self._fill_data(person_data)

    def _init_ui(self):
        title = "编辑人物" if self.person_data else "添加人物"
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        self.setStyleSheet(STYLESHEET)

        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入姓名")
        layout.addRow("姓名：", self.name_edit)

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(GENDER_OPTIONS)
        layout.addRow("性别：", self.gender_combo)

        self.birth_edit = QLineEdit()
        self.birth_edit.setPlaceholderText("如：1920")
        layout.addRow("出生年份：", self.birth_edit)

        self.death_edit = QLineEdit()
        self.death_edit.setPlaceholderText("如：1990")
        layout.addRow("逝世年份：", self.death_edit)

        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("别名、字号等")
        layout.addRow("别名：", self.alias_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("备注信息")
        layout.addRow("备注：", self.notes_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("background-color: #95a5a6;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _fill_data(self, data):
        self.name_edit.setText(data.get("name", ""))
        idx = GENDER_OPTIONS.index(data.get("gender", "未知")) if data.get("gender", "未知") in GENDER_OPTIONS else 2
        self.gender_combo.setCurrentIndex(idx)
        self.birth_edit.setText(data.get("birth_year", ""))
        self.death_edit.setText(data.get("death_year", ""))
        self.alias_edit.setText(data.get("alias_name", ""))
        self.notes_edit.setPlainText(data.get("notes", ""))

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "gender": self.gender_combo.currentText(),
            "birth_year": self.birth_edit.text().strip(),
            "death_year": self.death_edit.text().strip(),
            "alias_name": self.alias_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
        }


class AddRelationDialog(QDialog):
    def __init__(self, parent=None, people=None):
        super().__init__(parent)
        self.people = people or []
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("添加关系")
        self.setMinimumWidth(380)
        self.setStyleSheet(STYLESHEET)

        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.person1_combo = QComboBox()
        self.person2_combo = QComboBox()
        for p in self.people:
            label = f"{p['name']} (ID:{p['id']})"
            self.person1_combo.addItem(label, p["id"])
            self.person2_combo.addItem(label, p["id"])

        layout.addRow("人物一：", self.person1_combo)

        self.relation_combo = QComboBox()
        self.relation_combo.addItems(RELATION_TYPES)
        layout.addRow("关系类型：", self.relation_combo)

        layout.addRow("人物二：", self.person2_combo)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        self.notes_edit.setPlaceholderText("备注（可选）")
        layout.addRow("备注：", self.notes_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._validate_and_accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("background-color: #95a5a6;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _validate_and_accept(self):
        if self.person1_combo.currentData() == self.person2_combo.currentData():
            QMessageBox.warning(self, "提示", "请选择不同的人物")
            return
        self.accept()

    def get_data(self):
        return {
            "person1_id": self.person1_combo.currentData(),
            "relation_type": self.relation_combo.currentText(),
            "person2_id": self.person2_combo.currentData(),
            "notes": self.notes_edit.toPlainText().strip(),
        }


class RelationshipGraphWidget(QWidget):
    NODE_W = 110
    NODE_H = 48

    def __init__(self, parent=None):
        super().__init__(parent)
        self.people = []
        self.relationships = []
        self.positions = {}
        self._drag_id = None
        self._drag_offset = QPointF()
        self.setMinimumSize(400, 350)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_data(self, people, relationships):
        self.people = people
        self.relationships = relationships
        existing = set(self.positions.keys())
        current = {p["id"] for p in people}
        for pid in current - existing:
            margin = 60
            x = random.randint(margin, max(margin + 1, self.width() - self.NODE_W - margin))
            y = random.randint(margin, max(margin + 1, self.height() - self.NODE_H - margin))
            self.positions[pid] = QPointF(x, y)
        for pid in existing - current:
            del self.positions[pid]
        self._apply_force_layout()
        self.update()

    def _apply_force_layout(self):
        if len(self.people) < 2:
            return
        connected = {}
        for r in self.relationships:
            p1, p2 = r["person1_id"], r["person2_id"]
            connected.setdefault(p1, set()).add(p2)
            connected.setdefault(p2, set()).add(p1)
        for _ in range(60):
            forces = {p["id"]: QPointF(0, 0) for p in self.people}
            for i, pa in enumerate(self.people):
                for j, pb in enumerate(self.people):
                    if i >= j:
                        continue
                    a, b = pa["id"], pb["id"]
                    pos_a = self.positions.get(a, QPointF(100, 100))
                    pos_b = self.positions.get(b, QPointF(200, 200))
                    dx = pos_b.x() - pos_a.x()
                    dy = pos_b.y() - pos_a.y()
                    dist = max(math.sqrt(dx * dx + dy * dy), 1.0)
                    ideal = 180
                    repulsion = -3000.0 / (dist * dist)
                    fx = repulsion * dx / dist
                    fy = repulsion * dy / dist
                    if b in connected.get(a, set()):
                        attraction = (dist - ideal) * 0.05
                        fx += attraction * dx / dist
                        fy += attraction * dy / dist
                    forces[a] += QPointF(fx, fy)
                    forces[b] += QPointF(-fx, -fy)
            w, h = max(self.width(), 400), max(self.height(), 350)
            for p in self.people:
                pid = p["id"]
                pos = self.positions.get(pid, QPointF(100, 100))
                fx = max(-20, min(20, forces[pid].x()))
                fy = max(-20, min(20, forces[pid].y()))
                nx = max(10, min(w - self.NODE_W - 10, pos.x() + fx))
                ny = max(10, min(h - self.NODE_H - 10, pos.y() + fy))
                self.positions[pid] = QPointF(nx, ny)

    def _node_at(self, pos):
        for p in self.people:
            npos = self.positions.get(p["id"])
            if npos and QRectF(npos.x(), npos.y(), self.NODE_W, self.NODE_H).contains(pos):
                return p["id"]
        return None

    def _gender_color(self, gender):
        if gender == "男":
            return QColor(52, 152, 219)
        elif gender == "女":
            return QColor(231, 76, 60)
        return QColor(149, 165, 166)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fdfefe"))

        id_name = {p["id"]: p for p in self.people}

        for r in self.relationships:
            p1 = self.positions.get(r["person1_id"])
            p2 = self.positions.get(r["person2_id"])
            if not p1 or not p2:
                continue
            cx1 = p1.x() + self.NODE_W / 2
            cy1 = p1.y() + self.NODE_H / 2
            cx2 = p2.x() + self.NODE_W / 2
            cy2 = p2.y() + self.NODE_H / 2
            pen = QPen(QColor(120, 144, 156), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(QPointF(cx1, cy1), QPointF(cx2, cy2))
            mx, my = (cx1 + cx2) / 2, (cy1 + cy2) / 2
            painter.setPen(QPen(QColor(55, 71, 79)))
            font = QFont("Microsoft YaHei", 9)
            painter.setFont(font)
            painter.drawText(QRectF(mx - 30, my - 10, 60, 20), Qt.AlignCenter, r["relation_type"])

        for p in self.people:
            npos = self.positions.get(p["id"])
            if not npos:
                continue
            bg = self._gender_color(p.get("gender", "未知"))
            rect = QRectF(npos.x(), npos.y(), self.NODE_W, self.NODE_H)
            path = QPainterPath()
            path.addRoundedRect(rect, 10, 10)
            painter.setPen(QPen(bg.darker(120), 2))
            painter.setBrush(QBrush(bg))
            painter.drawPath(path)
            painter.setPen(QPen(Qt.white))
            font = QFont("Microsoft YaHei", 11, QFont.Bold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, p["name"])
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            nid = self._node_at(event.pos())
            if nid is not None:
                self._drag_id = nid
                npos = self.positions[nid]
                self._drag_offset = QPointF(event.pos().x() - npos.x(), event.pos().y() - npos.y())

    def mouseMoveEvent(self, event):
        if self._drag_id is not None:
            nx = event.pos().x() - self._drag_offset.x()
            ny = event.pos().y() - self._drag_offset.y()
            self.positions[self._drag_id] = QPointF(nx, ny)
            self.update()

    def mouseReleaseEvent(self, event):
        self._drag_id = None


class RelationshipWindow(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("人物关系")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(STYLESHEET)
        self._init_ui()
        self._refresh_all()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        people_group = QGroupBox("人物列表")
        people_layout = QVBoxLayout(people_group)

        self.people_table = QTableWidget()
        self.people_table.setColumnCount(7)
        self.people_table.setHorizontalHeaderLabels(["ID", "姓名", "性别", "出生年份", "逝世年份", "别名", "备注"])
        self.people_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.people_table.horizontalHeader().setStretchLastSection(True)
        self.people_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.people_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.people_table.setAlternatingRowColors(True)
        people_layout.addWidget(self.people_table)

        btn_layout = QHBoxLayout()
        self.add_person_btn = QPushButton("添加人物")
        self.add_person_btn.clicked.connect(self._on_add_person)
        self.edit_person_btn = QPushButton("编辑人物")
        self.edit_person_btn.setStyleSheet("background-color: #27ae60;")
        self.edit_person_btn.clicked.connect(self._on_edit_person)
        self.delete_person_btn = QPushButton("删除人物")
        self.delete_person_btn.setObjectName("deleteBtn")
        self.delete_person_btn.clicked.connect(self._on_delete_person)
        btn_layout.addWidget(self.add_person_btn)
        btn_layout.addWidget(self.edit_person_btn)
        btn_layout.addWidget(self.delete_person_btn)
        people_layout.addLayout(btn_layout)

        left_layout.addWidget(people_group)
        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        graph_group = QGroupBox("关系图谱")
        graph_layout = QVBoxLayout(graph_group)
        self.graph_widget = RelationshipGraphWidget()
        graph_layout.addWidget(self.graph_widget)
        right_layout.addWidget(graph_group, stretch=3)

        rel_group = QGroupBox("关系管理")
        rel_layout = QVBoxLayout(rel_group)

        self.rel_table = QTableWidget()
        self.rel_table.setColumnCount(5)
        self.rel_table.setHorizontalHeaderLabels(["ID", "人物一", "关系类型", "人物二", "备注"])
        self.rel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.rel_table.horizontalHeader().setStretchLastSection(True)
        self.rel_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rel_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rel_table.setAlternatingRowColors(True)
        self.rel_table.setMaximumHeight(180)
        rel_layout.addWidget(self.rel_table)

        rel_btn_layout = QHBoxLayout()
        self.add_rel_btn = QPushButton("添加关系")
        self.add_rel_btn.clicked.connect(self._on_add_relation)
        self.delete_rel_btn = QPushButton("删除关系")
        self.delete_rel_btn.setObjectName("deleteBtn")
        self.delete_rel_btn.clicked.connect(self._on_delete_relation)
        rel_btn_layout.addWidget(self.add_rel_btn)
        rel_btn_layout.addWidget(self.delete_rel_btn)
        rel_btn_layout.addStretch()
        rel_layout.addLayout(rel_btn_layout)

        right_layout.addWidget(rel_group, stretch=2)

        stat_group = QGroupBox("统计")
        stat_layout = QHBoxLayout(stat_group)
        self.stat_people_label = QLabel("总人物：0")
        self.stat_people_label.setObjectName("statLabel")
        self.stat_rel_label = QLabel("总关系：0")
        self.stat_rel_label.setObjectName("statLabel")
        self.stat_top_label = QLabel("最多连接：无")
        self.stat_top_label.setObjectName("statLabel")
        stat_layout.addWidget(self.stat_people_label)
        stat_layout.addWidget(self.stat_rel_label)
        stat_layout.addWidget(self.stat_top_label)
        stat_layout.addStretch()
        right_layout.addWidget(stat_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([380, 720])
        main_layout.addWidget(splitter)

    def _refresh_all(self):
        self._refresh_people()
        self._refresh_relationships()
        self._refresh_stats()

    def _refresh_people(self):
        people = execute_query_returning("SELECT * FROM people ORDER BY id")
        self.people_table.setRowCount(len(people))
        for row, p in enumerate(people):
            self.people_table.setItem(row, 0, QTableWidgetItem(str(p["id"])))
            self.people_table.setItem(row, 1, QTableWidgetItem(p["name"] or ""))
            self.people_table.setItem(row, 2, QTableWidgetItem(p["gender"] or ""))
            self.people_table.setItem(row, 3, QTableWidgetItem(p["birth_year"] or ""))
            self.people_table.setItem(row, 4, QTableWidgetItem(p["death_year"] or ""))
            self.people_table.setItem(row, 5, QTableWidgetItem(p["alias_name"] or ""))
            self.people_table.setItem(row, 6, QTableWidgetItem(p["notes"] or ""))
        self._cached_people = people

    def _refresh_relationships(self):
        rels = execute_query_returning(
            "SELECT r.*, p1.name as person1_name, p2.name as person2_name "
            "FROM relationships r "
            "LEFT JOIN people p1 ON r.person1_id = p1.id "
            "LEFT JOIN people p2 ON r.person2_id = p2.id "
            "ORDER BY r.id"
        )
        self.rel_table.setRowCount(len(rels))
        for row, r in enumerate(rels):
            self.rel_table.setItem(row, 0, QTableWidgetItem(str(r["id"])))
            self.rel_table.setItem(row, 1, QTableWidgetItem(r["person1_name"] or ""))
            self.rel_table.setItem(row, 2, QTableWidgetItem(r["relation_type"] or ""))
            self.rel_table.setItem(row, 3, QTableWidgetItem(r["person2_name"] or ""))
            self.rel_table.setItem(row, 4, QTableWidgetItem(r["notes"] or ""))
        self._cached_rels = rels
        people = getattr(self, "_cached_people", [])
        self.graph_widget.set_data(people, rels)

    def _refresh_stats(self):
        people = getattr(self, "_cached_people", [])
        rels = getattr(self, "_cached_rels", [])
        self.stat_people_label.setText(f"总人物：{len(people)}")
        self.stat_rel_label.setText(f"总关系：{len(rels)}")
        if people and rels:
            conn_count = {}
            for r in rels:
                conn_count[r["person1_id"]] = conn_count.get(r["person1_id"], 0) + 1
                conn_count[r["person2_id"]] = conn_count.get(r["person2_id"], 0) + 1
            id_name = {p["id"]: p["name"] for p in people}
            if conn_count:
                top_id = max(conn_count, key=conn_count.get)
                top_name = id_name.get(top_id, "未知")
                top_count = conn_count[top_id]
                self.stat_top_label.setText(f"最多连接：{top_name}（{top_count}条）")
            else:
                self.stat_top_label.setText("最多连接：无")
        else:
            self.stat_top_label.setText("最多连接：无")

    def _on_add_person(self):
        dlg = AddPersonDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "提示", "姓名不能为空")
                return
            execute_query(
                "INSERT INTO people (name, gender, birth_year, death_year, alias_name, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (data["name"], data["gender"], data["birth_year"], data["death_year"],
                 data["alias_name"], data["notes"])
            )
            self._refresh_all()
            self.data_changed.emit()

    def _on_edit_person(self):
        row = self.people_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择要编辑的人物")
            return
        people = getattr(self, "_cached_people", [])
        if row >= len(people):
            return
        person = people[row]
        dlg = AddPersonDialog(self, person_data=person)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "提示", "姓名不能为空")
                return
            execute_update(
                "UPDATE people SET name=?, gender=?, birth_year=?, death_year=?, "
                "alias_name=?, notes=?, updated_at=datetime('now','localtime') WHERE id=?",
                (data["name"], data["gender"], data["birth_year"], data["death_year"],
                 data["alias_name"], data["notes"], person["id"])
            )
            self._refresh_all()
            self.data_changed.emit()

    def _on_delete_person(self):
        row = self.people_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择要删除的人物")
            return
        people = getattr(self, "_cached_people", [])
        if row >= len(people):
            return
        person = people[row]

        sender_letters = execute_query_returning(
            "SELECT id, title FROM letters WHERE sender_id = ?", (person["id"],)
        )
        receiver_letters = execute_query_returning(
            "SELECT id, title FROM letters WHERE receiver_id = ?", (person["id"],)
        )

        if sender_letters or receiver_letters:
            related_count = len(sender_letters) + len(receiver_letters)
            detail_lines = []
            for lt in sender_letters[:5]:
                detail_lines.append(f"  · [ID:{lt['id']}] {lt['title'] or '无标题'} （作为寄信人）")
            for lt in receiver_letters[:5]:
                detail_lines.append(f"  · [ID:{lt['id']}] {lt['title'] or '无标题'} （作为收信人）")
            if related_count > 5:
                detail_lines.append(f"  ……等共 {related_count} 封信件")
            detail = "\n".join(detail_lines)

            reply = QMessageBox.question(
                self, "人物被信件引用",
                f"人物「{person['name']}」被 {related_count} 封信件引用：\n\n{detail}\n\n"
                f"如果继续删除，这些信件的关联人物将被清空。\n"
                f"是否继续删除？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                execute_update("UPDATE letters SET sender_id = NULL WHERE sender_id = ?", (person["id"],))
                execute_update("UPDATE letters SET receiver_id = NULL WHERE receiver_id = ?", (person["id"],))
                execute_update("DELETE FROM people WHERE id=?", (person["id"],))
                self._refresh_all()
                self.data_changed.emit()
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除人物「{person['name']}」吗？相关关系也会被删除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            execute_update("DELETE FROM people WHERE id=?", (person["id"],))
            self._refresh_all()
            self.data_changed.emit()

    def _on_add_relation(self):
        people = getattr(self, "_cached_people", [])
        if len(people) < 2:
            QMessageBox.information(self, "提示", "至少需要两个才能添加关系")
            return
        dlg = AddRelationDialog(self, people=people)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            execute_query(
                "INSERT INTO relationships (person1_id, person2_id, relation_type, notes) "
                "VALUES (?, ?, ?, ?)",
                (data["person1_id"], data["person2_id"], data["relation_type"], data["notes"])
            )
            self._refresh_all()
            self.data_changed.emit()

    def _on_delete_relation(self):
        row = self.rel_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择要删除的关系")
            return
        rels = getattr(self, "_cached_rels", [])
        if row >= len(rels):
            return
        rel = rels[row]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除这条关系吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            execute_update("DELETE FROM relationships WHERE id=?", (rel["id"],))
            self._refresh_all()
            self.data_changed.emit()

    def refresh(self):
        self._refresh_all()
