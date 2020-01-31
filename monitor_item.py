from PySide2.QtCore import Qt, QObject
from PySide2.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide2.QtGui import QBrush


class MonitorItem(QGraphicsRectItem, QObject):
    z = 0

    def __init__(self, *a, **kw):
        data = kw.pop("data")
        self.name = kw.pop("name")
        self.window = kw.pop("window")
        super().__init__(*a, **kw)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.label = QGraphicsTextItem("", self)
        self.update_visuals(data)

    def update_visuals(self, data):
        if data['replica_of']:
            label_text = f"{self.name} [{','.join(data['replica_of'])}]"
        else:
            label_text = self.name
        self.setRect(0, 0, data['res_x'], data['res_y'])
        self.setPos(data['pos_x'], data['pos_y'])
        self.label.setPlainText(label_text)
        label_scale = min(
            self.rect().width() / self.label.boundingRect().width(),
            self.rect().height() / self.label.boundingRect().height(),
        )
        self.label.setScale(label_scale)
        if data['primary']:
            self.setBrush(QBrush("#eee8d5", Qt.SolidPattern))
            self.setZValue(1)
        else:
            self.setBrush(QBrush("white", Qt.SolidPattern))
            self.setZValue(self.z)
            self.z -= 1

    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        self.orig_pos = self.pos()
        self.window.ui.screenCombo.setCurrentText(self.name)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        self.window.monitor_moved()

    def mouseMoveEvent(self, event):
        view = event.widget().parent()
        click_pos = event.buttonDownScreenPos(Qt.LeftButton)
        current_pos = event.screenPos()
        self.setPos(
            view.mapToScene(view.mapFromScene(self.orig_pos) + current_pos - click_pos)
        )
