from copy import deepcopy
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
    if "+" in line:  # Is enabled
        enabled = True
        res_x, res_y = [p for p in parts if "x" in p][0].split("+")[0].split("x")
        pos_x, pos_y = [p for p in parts if "x" in p][0].split("+")[1:]
        w_in_mm, h_in_mm = [p.split("mm")[0] for p in parts if p.endswith("mm")]
    else:
        enabled = False
        res_x = res_y = pos_x = pos_y = w_in_mm = h_in_mm = 0
    return (
        name,
        primary,
        int(res_x),
        int(res_y),
        int(w_in_mm),
        int(h_in_mm),
        int(pos_x),
        int(pos_y),
        enabled,
    )


def is_replica_of(a, b):
    """Return True if monitor a is a replica of b.
    
    Replica means same resolution and position.
    """
    return (
        a["pos_x"] == b["pos_x"]
        and a["pos_y"] == b["pos_y"]
        and a["res_x"] == b["res_x"]
        and a["res_y"] == b["res_y"]
    )


class Window(QObject):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        ui.show()
        self.ui.screenCombo.currentTextChanged.connect(self.monitor_selected)
        self.ui.horizontalScale.valueChanged.connect(self.updateScaleLabels)
        self.ui.verticalScale.valueChanged.connect(self.updateScaleLabels)
        self.xrandr_info = {}
        self.get_xrandr_info()
        self.orig_xrandr_info = deepcopy(self.xrandr_info)
        self.fill_ui()

    def fill_ui(self):
        """Load data from xrandr and setup the whole thing."""
        self.scene = QGraphicsScene(self)
        self.ui.sceneView.setScene(self.scene)
        self.ui.screenCombo.clear()

        for name, monitor in self.xrandr_info.items():
            self.ui.screenCombo.addItem(name)
            mon_item = MonitorItem(
                0,
                0,
                monitor["res_x"],
                monitor["res_y"],
                name=name,
                primary=monitor["primary"],
            )
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
        name = None
        for line in data:
            if line and line[0] not in "S \t":  # Output line
                (
                    name,
                    primary,
                    res_x,
                    res_y,
                    w_in_mm,
                    h_in_mm,
                    pos_x,
                    pos_y,
                    enabled,
                ) = parse_monitor(line)
                self.xrandr_info[name] = dict(
                    primary=primary,
                    res_x=res_x,
                    res_y=res_y,
                    w_in_mm=w_in_mm,
                    h_in_mm=h_in_mm,
                    pos_x=pos_x,
                    pos_y=pos_y,
                    modes=[],
                    current_mode=None,
                    enabled=enabled,
                )
            elif line[0] == " ":  # A mode
                mode_name = line.strip().split()[0]
                self.xrandr_info[name]["modes"].append(mode_name)
                if "*" in line:
                    print(f"Current mode for {name}: {mode_name}")
                    self.xrandr_info[name]["current_mode"] = mode_name

    def monitor_selected(self, name):
        # Show modes
        self.ui.modes.clear()
        for mode in self.xrandr_info[name]["modes"]:
            self.ui.modes.addItem(mode)
        self.ui.modes.setCurrentText(self.xrandr_info[name]["current_mode"])
        mod_x, mod_y = [
            int(x) for x in self.xrandr_info[name]["current_mode"].split("x")
        ]
        h_scale = self.xrandr_info[name]["res_x"] / mod_x
        v_scale = self.xrandr_info[name]["res_y"] / mod_y
        self.ui.horizontalScale.setValue(h_scale * 100)
        self.ui.verticalScale.setValue(v_scale * 100)
        self.ui.primary.setChecked(self.xrandr_info[name]["primary"])
        self.ui.enabled.setChecked(self.xrandr_info[name]["enabled"])

        self.ui.replicaOf.clear()
        self.ui.replicaOf.addItem("None")
        for mon in self.xrandr_info:
            if mon != name:
                self.ui.replicaOf.addItem(mon)
                if is_replica_of(self.xrandr_info[mon], self.xrandr_info[name]):
                    self.ui.replicaOf.setCurrentText(mon)

    def updateScaleLabels(self):
        self.ui.horizontalScaleLabel.setText(f"{self.ui.horizontalScale.value()}%")
        self.ui.verticalScaleLabel.setText(f"{self.ui.verticalScale.value()}%")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ui_file = QFile("main.ui")
    ui_file.open(QFile.ReadOnly)

    loader = QUiLoader()
    window = Window(loader.load(ui_file))

    sys.exit(app.exec_())
