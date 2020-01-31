import subprocess
import sys

from PySide2.QtWidgets import QApplication, QGraphicsScene, QGraphicsRectItem
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile, Qt, QPoint


def parse_monitor(line):
    parts = line.split()
    name = parts[0]
    primary = "primary" in parts
    w_in_mm, h_in_mm = [p.split("mm")[0] for p in parts if p.endswith("mm")]
    res_x, res_y = [p for p in parts if "x" in p][0].split("+")[0].split("x")
    pos_x, pos_y = [p for p in parts if "x" in p][0].split("+")[1:]
    print(name, pos_x, pos_y)
    return (
        name,
        primary,
        int(res_x),
        int(res_y),
        int(w_in_mm),
        int(h_in_mm),
        int(pos_x),
        int(pos_y),
    )


xrandr_info = {}


def get_xrandr_info():
    data = subprocess.check_output(["xrandr"]).decode("utf-8").splitlines()
    outputs = [x for x in data if x and x[0] not in "S \t"]
    for o in outputs:
        name, primary, res_x, res_y, w_in_mm, h_in_mm, pos_x, pos_y = parse_monitor(o)
        xrandr_info[name] = dict(
            primary=primary,
            res_x=res_x,
            res_y=res_y,
            w_in_mm=w_in_mm,
            h_in_mm=h_in_mm,
            pos_x=pos_x,
            pos_y=pos_y,
        )


class MonitorItem(QGraphicsRectItem):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.setAcceptedMouseButtons(Qt.LeftButton)

    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        self.orig_pos = self.pos()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)

    def mouseMoveEvent(self, event):
        view = event.widget().parent()
        click_pos = event.buttonDownScreenPos(Qt.LeftButton)
        current_pos = event.screenPos()
        print(current_pos - click_pos)
        print(view.mapToScene(view.mapFromScene(self.orig_pos) + current_pos - click_pos))
        self.setPos(view.mapToScene(view.mapFromScene(self.orig_pos) + current_pos - click_pos))
        # self.setPos(delta.x(), delta.y())


def fill_ui(data, window):
    global scene
    scene = QGraphicsScene(window)
    scene.addText("Hello World!")
    window.sceneView.setScene(scene)
    window.screenCombo.clear()
    for name, monitor in xrandr_info.items():
        window.screenCombo.addItem(name)
        mon_item = MonitorItem(0, 0, monitor["res_x"], monitor["res_y"])
        mon_item.setPos(monitor["pos_x"], monitor["pos_y"])
        scene.addItem(mon_item)

    print(scene.sceneRect())
    window.sceneView.ensureVisible(scene.sceneRect(), 100, 100)
    scale_factor = 0.7 * min(
        window.sceneView.width() / scene.sceneRect().width(),
        window.sceneView.height() / scene.sceneRect().height(),
    )
    window.sceneView.scale(scale_factor, scale_factor)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ui_file = QFile("main.ui")
    ui_file.open(QFile.ReadOnly)

    loader = QUiLoader()
    window = loader.load(ui_file)
    window.show()
    get_xrandr_info()
    fill_ui(xrandr_info, window)

    sys.exit(app.exec_())
