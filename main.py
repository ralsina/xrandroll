import subprocess
import sys

from PySide2.QtCore import QFile, QObject
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QGraphicsScene

from monitor_item import MonitorItem


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


class Window(QObject):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        ui.show()
        self.ui.screenCombo.currentTextChanged.connect(self.monitor_selected)
        self.xrandr_info = {}
        self.get_xrandr_info()
        self.fill_ui()

    def fill_ui(self):
        """Load data from xrandr and setup the whole thing."""
        self.scene = QGraphicsScene(self)
        self.ui.sceneView.setScene(self.scene)
        self.ui.screenCombo.clear()

        for name, monitor in self.xrandr_info.items():
            self.ui.screenCombo.addItem(name)
            mon_item = MonitorItem(0, 0, monitor["res_x"], monitor["res_y"], name=name)
            mon_item.setPos(monitor["pos_x"], monitor["pos_y"])
            self.scene.addItem(mon_item)
            monitor["item"] = mon_item
        self.adjust_view()

    def adjust_view(self):
        self.ui.sceneView.ensureVisible(self.scene.sceneRect(), 100, 100)
        scale_factor = 0.7 * min(
            self.ui.sceneView.width() / self.scene.sceneRect().width(),
            self.ui.sceneView.height() / self.scene.sceneRect().height(),
        )
        self.ui.sceneView.scale(scale_factor, scale_factor)

    def get_xrandr_info(self):
        data = subprocess.check_output(["xrandr"]).decode("utf-8").splitlines()
        outputs = [x for x in data if x and x[0] not in "S \t"]
        for o in outputs:
            name, primary, res_x, res_y, w_in_mm, h_in_mm, pos_x, pos_y = parse_monitor(
                o
            )
            self.xrandr_info[name] = dict(
                primary=primary,
                res_x=res_x,
                res_y=res_y,
                w_in_mm=w_in_mm,
                h_in_mm=h_in_mm,
                pos_x=pos_x,
                pos_y=pos_y,
            )

    def monitor_selected(self, name):
        print(name)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ui_file = QFile("main.ui")
    ui_file.open(QFile.ReadOnly)

    loader = QUiLoader()
    window = Window(loader.load(ui_file))

    sys.exit(app.exec_())
