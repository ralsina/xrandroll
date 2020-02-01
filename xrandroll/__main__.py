import os
import shlex
import subprocess
import sys
from copy import deepcopy

from PySide2.QtCore import QFile, QObject
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QGraphicsScene, QLabel

from .monitor_item import MonitorItem


def gen_xrandr_from_data(data):
    """Takes monitor data and generates a xrandr command line."""
    cli = ["xrandr"]
    for name, mon in data.items():
        cli.append(f"--output {name}")
        cli.append(f'--pos {int(mon["pos_x"])}x{int(mon["pos_y"])}')
        cli.append(f'--mode {mon["current_mode"]}')
        mod_x, mod_y = [int(n) for n in mon["current_mode"].split("x")]
        if mon["orientation"] in (1, 3):
            mod_x, mod_y = mod_y, mod_x
        cli.append(f'--scale {mon["res_x"]/mod_x}x{mon["res_y"]/mod_y}')
        cli.append(
            f"--rotate {['normal', 'left', 'inverted', 'right'][mon['orientation']]}"
        )
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

    left_side = line.split(" (normal left inverted ")[0]
    orientation = 0
    if "left" in left_side:
        orientation = 1
    elif "inverted" in left_side:
        orientation = 2
    elif "right" in left_side:
        orientation = 3

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
        orientation,
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
        self.ui.setWindowTitle("Display Configuration")
        self.ui.screenCombo.currentTextChanged.connect(self.monitor_selected)
        self.ui.replicaOf.currentTextChanged.connect(self.replica_changed)
        self.ui.orientationCombo.currentIndexChanged.connect(self.orientation_changed)
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
        self.ui.scaleModeCombo.currentTextChanged.connect(self.scale_mode_changed)

        self.pos_label = QLabel(self.ui.sceneView)
        self.pos_label.setText("FOOOOO")
        self.pos_label.move(5, 5)

    def scale_mode_changed(self):
        mon = self.ui.screenCombo.currentText()
        scale_mode = self.ui.scaleModeCombo.currentText()
        print(f"Set {mon} scale mode to {scale_mode}")
        if scale_mode == "Manual":
            self.ui.horizontalScale.setEnabled(True)
            self.ui.verticalScale.setEnabled(True)
            try:
                self.ui.horizontalScale.valueChanged.disconnect(
                    self.ui.verticalScale.setValue
                )
            except RuntimeError:  # Not connected
                pass
        elif scale_mode == "Disabled (1x1)":
            self.ui.verticalScale.setEnabled(False)
            self.ui.horizontalScale.setEnabled(False)
            self.ui.horizontalScale.setValue(1000)
            self.ui.verticalScale.setValue(1000)
            try:
                self.ui.horizontalScale.valueChanged.disconnect(
                    self.ui.verticalScale.setValue
                )
            except RuntimeError:  # Not connected
                pass
        elif scale_mode == "Automatic: physical dimensions":
            # Calculate scale factors so that the logical pixels will be the same
            # size as in the primary window
            if self.ui.primary.isChecked():
                print("Has no effect on primary display.")
                return

            # Find the primary monitor
            primary = [k for k in self.xrandr_info if self.xrandr_info[k]["primary"]]
            if not primary:
                print("Oops, no primary!")
                return
            primary = self.xrandr_info[primary[0]]
            monitor = self.xrandr_info[mon]

            prim_density_x = primary["res_x"] / primary["w_in_mm"]
            prim_density_y = primary["res_y"] / primary["h_in_mm"]

            dens_x = monitor["res_x"] / monitor["w_in_mm"]
            dens_y = monitor["res_y"] / monitor["h_in_mm"]

            try:
                self.ui.horizontalScale.valueChanged.disconnect(
                    self.ui.verticalScale.setValue
                )
            except RuntimeError:  # Not connected
                pass
            self.ui.horizontalScale.setEnabled(False)
            self.ui.verticalScale.setEnabled(False)
            self.ui.horizontalScale.setValue(prim_density_x / dens_x * 1000)
            self.ui.verticalScale.setValue(prim_density_y / dens_y * 1000)

        elif scale_mode == "Manual, same in both dimensions":
            self.ui.horizontalScale.setEnabled(True)
            self.ui.verticalScale.setEnabled(False)
            self.ui.horizontalScale.valueChanged.connect(self.ui.verticalScale.setValue)
            self.ui.verticalScale.setValue(self.ui.horizontalScale.value())

    def replica_changed(self):
        mon = self.ui.screenCombo.currentText()
        replicate = self.ui.replicaOf.currentText()
        print(f"Making {mon} a replica of {replicate}")
        if replicate in ("None", "", None):
            print("TODO: make things non-replicas")
            return
        mon = self.xrandr_info[mon]
        replicate = self.xrandr_info[replicate]

        # Making a replica implies:
        # Set the same position
        mon["pos_x"] = replicate["pos_x"]
        mon["pos_y"] = replicate["pos_y"]

        # Set the same mode if possible
        if replicate["current_mode"] in mon["modes"]:
            mon["current_mode"] = replicate["current_mode"]
        else:
            # Keep the current mode, and change scaling so it
            # has the same effective size as the desired mode
            mod_x, mod_y = [int(x) for x in mon["current_mode"].split("x")]
            target_x, target_y = [replicate[x] for x in ["res_x", "res_y"]]
            scale_x = 1000 * target_x / mod_x
            scale_y = 1000 * target_y / mod_y
            breakpoint()
            print(target_x, target_y, mod_x, mod_y)
            print(scale_x, scale_y)
            self.ui.horizontalScale.setValue(scale_x)
            self.ui.verticalScale.setValue(scale_y)

        mon["item"].update_visuals(mon)

    def do_reset(self):
        for n in self.xrandr_info:
            self.xrandr_info[n].update(self.orig_xrandr_info[n])
        self.fill_ui()

    def do_ok(self):
        self.do_apply()
        self.ui.accept()

    def do_apply(self):
        cli = gen_xrandr_from_data(self.xrandr_info)
        print(cli)
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

    def orientation_changed(self):
        mon = self.ui.screenCombo.currentText()
        orientation = self.ui.orientationCombo.currentIndex()
        self.xrandr_info[mon]["orientation"] = orientation
        self.mode_changed()

    def mode_changed(self):
        mon = self.ui.screenCombo.currentText()
        mode = self.ui.modes.currentText()
        if not mode:
            return
        print(f"Changing {mon} to {mode}")
        self.xrandr_info[mon]["current_mode"] = mode
        mode_x, mode_y = mode.split("x")
        # use resolution via scaling
        if self.xrandr_info[mon]["orientation"] in (0, 2):
            self.xrandr_info[mon]["res_x"] = int(
                int(mode_x) * self.ui.horizontalScale.value() / 1000
            )
            self.xrandr_info[mon]["res_y"] = int(
                int(mode_y) * self.ui.verticalScale.value() / 1000
            )
        else:
            self.xrandr_info[mon]["res_x"] = int(
                int(mode_y) * self.ui.horizontalScale.value() / 1000
            )
            self.xrandr_info[mon]["res_y"] = int(
                int(mode_x) * self.ui.verticalScale.value() / 1000
            )
        self.xrandr_info[mon]["item"].update_visuals(self.xrandr_info[mon])

    def show_pos(self, x, y):
        self.pos_label.setText(f"{x},{y}")
        self.pos_label.resize(self.pos_label.sizeHint())

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
                    orientation,
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
                    orientation=orientation,
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
        if self.xrandr_info[name]["orientation"] in (0, 2):
            h_scale = self.xrandr_info[name]["res_x"] / mod_x
            v_scale = self.xrandr_info[name]["res_y"] / mod_y
        else:
            h_scale = self.xrandr_info[name]["res_y"] / mod_x
            v_scale = self.xrandr_info[name]["res_x"] / mod_y
        self.ui.horizontalScale.setValue(h_scale * 1000)
        self.ui.verticalScale.setValue(v_scale * 1000)
        self.ui.primary.setChecked(self.xrandr_info[name]["primary"])
        self.ui.enabled.setChecked(self.xrandr_info[name]["enabled"])
        self.ui.orientationCombo.setCurrentIndex(self.xrandr_info[name]["orientation"])

        self.ui.replicaOf.clear()
        self.ui.replicaOf.addItem("None")
        for mon in self.xrandr_info:
            if mon != name:
                self.ui.replicaOf.addItem(mon)
                if mon in self.xrandr_info[name]["replica_of"]:
                    self.ui.replicaOf.setCurrentText(mon)
        self.ui.modes.blockSignals(False)

    def scale_changed(self):
        self.ui.horizontalScaleLabel.setText(
            f"{int(self.ui.horizontalScale.value()/10)}%"
        )
        self.ui.verticalScaleLabel.setText(f"{int(self.ui.verticalScale.value()/10)}%")
        self.mode_changed()  # Not really, but it's the same thing

def main():
    app = QApplication(sys.argv)

    ui_file = QFile(os.path.join(os.path.dirname(__file__), "main.ui"))
    ui_file.open(QFile.ReadOnly)

    loader = QUiLoader()
    window = Window(loader.load(ui_file))

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()