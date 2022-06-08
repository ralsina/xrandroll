from PySide2.QtCore import Qt, QObject
from PySide2.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PySide2.QtGui import QBrush, QColor


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

    def update_visuals(self, monitor):
        self.setRect(0, 0, monitor.res_x, monitor.res_y)
        self.setPos(monitor.pos_x, monitor.pos_y)
        if monitor.orientation == "normal":
            self.bottom_edge.setRect(0, monitor.res_y - 50, monitor.res_x, 50)
        elif monitor.orientation == "left":
            self.bottom_edge.setRect(monitor.res_x - 50, 0, 50, monitor.res_y)
        elif monitor.orientation == "inverted":
            self.bottom_edge.setRect(0, 0, monitor.res_x, 50)
        elif monitor.orientation == "right":
            self.bottom_edge.setRect(0, 0, 50, monitor.res_y)
        if monitor.replica_of:
            label_text = f"{self.name} [{','.join(monitor.replica_of)}]"
        else:
            label_text = self.name
        self.label.setPlainText(label_text)
        label_scale = min(
            self.rect().width() / self.label.boundingRect().width(),
            self.rect().height() / self.label.boundingRect().height(),
        )
        self.label.setScale(label_scale)
        if monitor.enabled:
            if monitor.primary:
                color = QColor("#eee8d5")
                color.setAlpha(200)
                self.setBrush(QBrush(color, Qt.SolidPattern))
                self.setZValue(1000)
            else:
                color = QColor("#ffffff")
                color.setAlpha(200)
                self.setBrush(QBrush(color, Qt.SolidPattern))
                self.setZValue(self.z)
                self.z -= 1
            self.show()
        else:
            color = QColor("#f1f1f1")
            color.setAlpha(200)
            self.setBrush(QBrush(color, Qt.SolidPattern))
            self.setZValue(-1000)
            self.hide()

    def mousePressEvent(self, event):
        self.window.pos_label.show()
        self.setCursor(Qt.ClosedHandCursor)
        self.orig_pos = self.pos()
        self.window.ui.screenCombo.setCurrentText(self.name)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        self.window.pos_label.hide()
        self.window.monitor_moved()

    def mouseMoveEvent(self, event):
        snaps_x, snaps_y = self.window.possible_snaps(self.name)
        view = event.widget().parent()
        click_pos = event.buttonDownScreenPos(Qt.LeftButton)
        current_pos = event.screenPos()
        new_pos = view.mapFromScene(self.orig_pos) + current_pos - click_pos
        new_pos = view.mapToScene(new_pos)
        delta = abs(view.mapToScene(0, 25).y())
        if not event.modifiers() & Qt.ControlModifier:  # Ctrl was not pressed, so snap
            # This snaps the left and top edges
            x = new_pos.x()
            delta_x = min((abs(x - sx), i) for i, sx in enumerate(snaps_x))
            if delta_x[0] < delta:  # snap
                new_pos.setX(int(snaps_x[delta_x[1]]))
            y = new_pos.y()
            delta_y = min((abs(y - sy), i) for i, sy in enumerate(snaps_y))
            if delta_y[0] < delta:  # snap
                new_pos.setY(int(snaps_y[delta_y[1]]))

            # This snaps the right and bottom edges
            x = new_pos.x() + self.rect().width()
            delta_x = min((abs(x - sx), i) for i, sx in enumerate(snaps_x))
            if delta_x[0] < delta:  # snap
                new_pos.setX(int(snaps_x[delta_x[1]]) - self.rect().width())
            y = new_pos.y() + self.rect().height()
            delta_y = min((abs(y - sy), i) for i, sy in enumerate(snaps_y))
            if delta_y[0] < delta:  # snap
                new_pos.setY(int(snaps_y[delta_y[1]]) - self.rect().height())

        self.setPos(new_pos)
        self.window.show_pos(int(self.pos().x()), int(self.pos().y()))
