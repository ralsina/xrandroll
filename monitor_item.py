from PySide2.QtCore import Qt
from PySide2.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide2.QtGui import QBrush, QPen


class MonitorItem(QGraphicsRectItem):
    def __init__(self, *a, **kw):
        primary = kw.pop('primary')
        super().__init__(*a, **kw)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.label = QGraphicsTextItem(kw["name"], self)
        label_scale = min(
            self.rect().width() / self.label.boundingRect().width(),
            self.rect().height() / self.label.boundingRect().height(),
        )
        self.label.setScale(label_scale)
        if primary:
            self.setBrush(QBrush('#eee8d5', Qt.SolidPattern))

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
