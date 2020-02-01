from PySide2.QtCore import Qt, QObject
from PySide2.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide2.QtGui import QBrush


class MonitorItem(QGraphicsRectItem, QObject):
    z = 0

    def __init__(self, *a, **kw):
        data = kw.pop("data")
        self.name = kw.pop("name")
        self.window = kw.pop("window")
        super().__init__(0, 0, 0, 0)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.label = QGraphicsTextItem("", self)
        self.bottom_edge = QGraphicsRectItem(0, 0, 0, 0, self)
        self.bottom_edge.setBrush(QBrush("red", Qt.SolidPattern))
        self.update_visuals(data)

    def update_visuals(self, data):
        if data["replica_of"]:
            label_text = f"{self.name} [{','.join(data['replica_of'])}]"
        else:
            label_text = self.name
        if data["orientation"] in (0, 2):
            self.setRect(0, 0, data["res_x"], data["res_y"])
            if data["orientation"] == 0:
                self.bottom_edge.setRect(0, data["res_y"] - 50, data["res_x"], 50)
            if data["orientation"] == 2:
                self.bottom_edge.setRect(0, 0, data["res_x"], 50)
        else:
            self.setRect(0, 0, data["res_y"], data["res_x"])
            if data["orientation"] == 1:
                self.bottom_edge.setRect(data["res_y"] - 50, 0, 50, data["res_x"])
            if data["orientation"] == 3:
                self.bottom_edge.setRect(0, 0, 50, data["res_x"])
        self.setPos(data["pos_x"], data["pos_y"])
        self.label.setPlainText(label_text)
        label_scale = min(
            self.rect().width() / self.label.boundingRect().width(),
            self.rect().height() / self.label.boundingRect().height(),
        )
        self.label.setScale(label_scale)
        if data["enabled"]:
            if data["primary"]:
                self.setBrush(QBrush("#eee8d5", Qt.SolidPattern))
                self.setZValue(1)
            else:
                self.setBrush(QBrush("white", Qt.SolidPattern))
                self.setZValue(self.z)
                self.z -= 1
        else:
            self.setBrush(QBrush("#010101", Qt.FDiagPattern))

    def mousePressEvent(self, event):
        self.window.pos_label.show()
        self.setCursor(Qt.ClosedHandCursor)
        self.orig_pos = self.pos()
        self.window.ui.screenCombo.setCurrentText(self.name)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        self.window.monitor_moved()
        self.window.pos_label.hide()

    def mouseMoveEvent(self, event):
        view = event.widget().parent()
        click_pos = event.buttonDownScreenPos(Qt.LeftButton)
        current_pos = event.screenPos()
        self.setPos(
            view.mapToScene(view.mapFromScene(self.orig_pos) + current_pos - click_pos)
        )
        self.window.show_pos(int(self.pos().x()), int(self.pos().y()))
