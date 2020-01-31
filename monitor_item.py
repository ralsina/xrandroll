from PySide2.QtCore import Qt
from PySide2.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide2.QtGui import QBrush, QPen


class MonitorItem(QGraphicsRectItem):
    z = 0
    def __init__(self, *a, **kw):
        primary = kw.pop('primary')
        name = kw.pop('name')
        replica_of=kw.pop('replica_of')
        super().__init__(*a, **kw)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        if replica_of:
            label_text = f"{name} [{','.join(replica_of)}]"
        else:
            label_text = name
        self.label = QGraphicsTextItem(label_text, self)
        label_scale = min(
            self.rect().width() / self.label.boundingRect().width(),
            self.rect().height() / self.label.boundingRect().height(),
        )
        self.label.setScale(label_scale)
        if primary:
            self.setBrush(QBrush('#eee8d5', Qt.SolidPattern))
            self.setZValue(1)
        else:
            self.setBrush(QBrush('white', Qt.SolidPattern))
            self.setZValue(self.z)
            self.z -= 1

    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        self.orig_pos = self.pos()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)

    def mouseMoveEvent(self, event):
        view = event.widget().parent()
        click_pos = event.buttonDownScreenPos(Qt.LeftButton)
        current_pos = event.screenPos()
        self.setPos(
            view.mapToScene(view.mapFromScene(self.orig_pos) + current_pos - click_pos)
        )
