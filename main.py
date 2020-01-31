from copy import deepcopy
import shlex
import subprocess
import sys

from PySide2.QtCore import QFile, QObject
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QGraphicsScene

from monitor_item import MonitorItem


def gen_xrandr_from_data(data):
    """Takes monitor data and generates a xrandr command line."""
    cli = ["xrandr"]
    for name, mon in data.items():
        cli.append(f"--output {name}")
        cli.append(f'--pos {int(mon["pos_x"])}x{int(mon["pos_y"])}')
        cli.append(f'--mode {mon["current_mode"]}')
        mod_x, mod_y = [int(n) for n in mon["current_mode"].split("x")]
        cli.append(f'--scale {mon["res_x"]/mod_x}x{mon["res_y"]/mod_y}')
        if mon["primary"]:
            cli.append("--primary")
        if not mon["enabled"]:
            cli.append("--off")

    return " ".join(cli)


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
        self.ui.setWindowTitle('Display Configuration')
        self.ui.screenCombo.currentTextChanged.connect(self.monitor_selected)
        self.xrandr_info = {}
        self.get_xrandr_info()
        self.orig_xrandr_info = deepcopy(self.xrandr_info)
        self.fill_ui()
        self.ui.horizontalScale.valueChanged.connect(self.scale_changed)
        self.ui.verticalScale.valueChanged.connect(self.scale_changed)
        self.ui.modes.currentTextChanged.connect(self.mode_changed)
        self.ui.applyButton.clicked.connect(self.do_apply)
        self.ui.okButton.clicked.connect(self.do_ok)
        self.ui.resetButton.clicked.connect(self.do_reset)
        self.ui.cancelButton.clicked.connect(self.ui.reject)

    def do_reset(self):
        for n in self.xrandr_info:
            self.xrandr_info[n].update(self.orig_xrandr_info[n])
        self.fill_ui()

    def do_ok(self):
        self.do_apply()
        self.ui.accept()

    def do_apply(self):
        cli = gen_xrandr_from_data(self.xrandr_info)
        subprocess.check_call(shlex.split(cli))

    def fill_ui(self):
        """Load data from xrandr and setup the whole thing."""
        self.scene = QGraphicsScene(self)
        self.ui.sceneView.setScene(self.scene)
        self.ui.screenCombo.clear()

        for name, monitor in self.xrandr_info.items():
            self.ui.screenCombo.addItem(name)
            mon_item = MonitorItem(data=monitor, window=self, name=name,)
            # mon_item.setPos(monitor["pos_x"], monitor["pos_y"])
            self.scene.addItem(mon_item)
            monitor["item"] = mon_item
        self.adjust_view()
        self.scale_changed()  # Trigger scale labels update

    def mode_changed(self):
        mon = self.ui.screenCombo.currentText()
        mode = self.ui.modes.currentText()
        if not mode:
            return
        print(f"Changing {mon} to {mode}")
        self.xrandr_info[mon]["current_mode"] = mode
        mode_x, mode_y = mode.split("x")
        # use resolution via scaling
        self.xrandr_info[mon]["res_x"] = int(
            int(mode_x) * self.ui.horizontalScale.value() / 100
        )
        self.xrandr_info[mon]["res_y"] = int(
            int(mode_y) * self.ui.verticalScale.value() / 100
        )
        self.xrandr_info[mon]["item"].update_visuals(self.xrandr_info[mon])

    def monitor_moved(self):
        "Update xrandr_info with new monitor positions"
        for _, mon in self.xrandr_info.items():
            item = mon["item"]
            mon["pos_x"] = item.x()
            mon["pos_y"] = item.y()
        self.update_replica_of_data()
        for _, mon in self.xrandr_info.items():
            mon["item"].update_visuals(mon)
        self.adjust_view()

    def adjust_view(self):
        self.ui.sceneView.resetTransform()
        self.ui.sceneView.ensureVisible(self.scene.sceneRect(), 100, 100)
        scale_factor = 0.8 * min(
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
                    replica_of=[],
                )
            elif line[0] == " ":  # A mode
                mode_name = line.strip().split()[0]
                self.xrandr_info[name]["modes"].append(mode_name)
                if "*" in line:
                    print(f"Current mode for {name}: {mode_name}")
                    self.xrandr_info[name]["current_mode"] = mode_name
        self.update_replica_of_data()

    def update_replica_of_data(self):
        for a in self.xrandr_info:
            self.xrandr_info[a]["replica_of"] = []
            for b in self.xrandr_info:
                if a != b and is_replica_of(self.xrandr_info[a], self.xrandr_info[b]):
                    self.xrandr_info[a]["replica_of"].append(b)

    def monitor_selected(self, name):
        if not name:
            return
        # needed so we don't flip through all modes as they are added
        self.ui.modes.blockSignals(True)
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
                if mon in self.xrandr_info[name]["replica_of"]:
                    self.ui.replicaOf.setCurrentText(mon)
        self.ui.modes.blockSignals(False)

    def scale_changed(self):
        self.ui.horizontalScaleLabel.setText(f"{self.ui.horizontalScale.value()}%")
        self.ui.verticalScaleLabel.setText(f"{self.ui.verticalScale.value()}%")
        self.mode_changed()  # Not really, but it's the same thing


if __name__ == "__main__":
    app = QApplication(sys.argv)

    ui_file = QFile("main.ui")
    ui_file.open(QFile.ReadOnly)

    loader = QUiLoader()
    window = Window(loader.load(ui_file))

    sys.exit(app.exec_())
