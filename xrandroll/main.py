import os
import shlex
import subprocess
import sys

from PySide2.QtCore import QFile, QObject
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QGraphicsScene, QLabel

from .monitor_item import MonitorItem
from . import xrandr


def parse_mode(mode):
    return (int(n) for n in mode.split("x"))


def gen_xrandr_from_data(data):
    """Takes monitor data and generates a xrandr command line."""
    cli = ["xrandr"]
    for name, mon in data.items():
        cli.append(f"--output {name}")
        if not mon["enabled"]:
            cli.append("--off")
        else:
            cli.append(f'--pos {int(mon["pos_x"])}x{int(mon["pos_y"])}')
            cli.append(f'--mode {mon["current_mode"]}')
            mod_x, mod_y = parse_mode(mon["current_mode"])
            if mon["orientation"] in (1, 3):
                mod_x, mod_y = mod_y, mod_x
            cli.append(f'--scale {mon["res_x"]/mod_x}x{mon["res_y"]/mod_y}')
            cli.append(
                f"--rotate {['normal', 'left', 'inverted', 'right'][mon['orientation']]}"
            )
            if mon["primary"]:
                cli.append("--primary")

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


class Window(QObject):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        ui.show()
        self.ui.setWindowTitle("Display Configuration")
        self.ui.screenCombo.currentTextChanged.connect(self.monitor_selected)
        self.ui.replicaOf.currentTextChanged.connect(self.replica_changed)
        self.ui.orientationCombo.currentIndexChanged.connect(self.orientation_changed)
        self.get_xrandr_info()
        self.fill_ui()
        self.ui.horizontalScale.valueChanged.connect(self.scale_changed)
        self.ui.verticalScale.valueChanged.connect(self.scale_changed)
        self.ui.modes.currentTextChanged.connect(self.mode_changed)
        self.ui.applyButton.clicked.connect(self.do_apply)
        self.ui.okButton.clicked.connect(self.do_ok)
        self.ui.resetButton.clicked.connect(self.do_reset)
        self.ui.cancelButton.clicked.connect(self.ui.reject)
        self.ui.scaleModeCombo.currentTextChanged.connect(self.scale_mode_changed)
        self.ui.primary.stateChanged.connect(self.primary_changed)
        self.ui.enabled.stateChanged.connect(self.enabled_changed)

        self.pos_label = QLabel(self.ui.sceneView)
        self.pos_label.move(5, 5)

    def enabled_changed(self):
        mon = self.ui.screenCombo.currentText()
        enabled = self.ui.enabled.isChecked()
        print(f"Setting {mon} enabled status to {enabled}")
        monitor = self.screen.monitors[mon]
        monitor.enabled = enabled
        if enabled and not monitor.get_current_mode():
            # Choose a mode
            self.ui.modes.setCurrentText(monitor.get_preferred_mode_name())
            self.mode_changed()
        self.screen.update_replica_of()
        for mon in self.screen.monitors.values():
            mon.item.update_visuals(mon)
        self.adjust_view()

    def primary_changed(self):
        mon_name = self.ui.screenCombo.currentText()
        primary = self.ui.primary.isChecked()
        if primary:
            self.screen.set_primary(mon_name)
        else:
            self.screen.set_primary("foobar")  # no primary

        for monitor in self.screen.monitors.values():
            monitor.item.update_visuals(monitor)

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
            mod_x, mod_y = parse_mode(mon["current_mode"])
            target_x, target_y = [replicate[x] for x in ["res_x", "res_y"]]
            scale_x = 1000 * target_x / mod_x
            scale_y = 1000 * target_y / mod_y
            self.ui.horizontalScale.setValue(scale_x)
            self.ui.verticalScale.setValue(scale_y)

        self.update_replica_of_data()
        for _, mon in self.xrandr_info.items():
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
        """Configure UI out of our screen data."""
        self.scene = QGraphicsScene(self)
        self.ui.sceneView.setScene(self.scene)
        self.ui.screenCombo.clear()

        for name, monitor in self.screen.monitors.items():
            self.ui.screenCombo.addItem(name)
            mon_item = MonitorItem(data=monitor, window=self, name=name,)
            self.scene.addItem(mon_item)
            monitor.item = mon_item
        self.ui.screenCombo.setCurrentText(self.screen.choose_a_monitor())
        self.adjust_view()
        # self.scale_changed()  # Trigger scale labels update

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
        monitor = self.screen.monitors[mon]
        monitor.set_current_mode(mode)
        mode_x, mode_y = (
            monitor.get_current_mode().res_x,
            monitor.get_current_mode().res_y,
        )
        # use resolution via scaling
        if monitor.orientation in ("normal", "inverted"):
            monitor.res_x = int(mode_x * self.ui.horizontalScale.value() / 1000)
            monitor.res_y = int(mode_y * self.ui.verticalScale.value() / 1000)
        else:
            monitor.res_x = int(mode_y * self.ui.horizontalScale.value() / 1000)
            monitor.res_y = int(mode_x * self.ui.verticalScale.value() / 1000)
        # TODO self.xrandr_info[mon]["item"].update_visuals(self.xrandr_info[mon])

    def show_pos(self, x, y):
        self.pos_label.setText(f"{x},{y}")
        self.pos_label.resize(self.pos_label.sizeHint())

    def monitor_moved(self):
        "Update screen with new monitor positions"
        for mon in self.screen.monitors.values():
            item = mon.item
            mon.pos_x = item.x()
            mon.pos_y = item.y()
        self.screen.update_replica_of()
        for mon in self.screen.monitors.values():
            mon.item.update_visuals(mon)
        self.adjust_view()

    def possible_snaps(self, name):
        """Return two lists of values to which the x and y position
        of monitor "name" could snap to."""
        snaps_x = []
        snaps_y = []

        for output, monitor in self.screen.monitors.items():
            if output == name:
                continue
            else:
                mode = monitor.get_current_mode()
                mod_x, mod_y = mode.res_x, mode.res_y
                snaps_x.append(monitor.pos_x)
                snaps_x.append(monitor.pos_x + mod_x)
                snaps_y.append(monitor.pos_x)
                snaps_y.append(monitor.pos_x + mod_y)
        return snaps_x, snaps_y

    def adjust_view(self):
        self.ui.sceneView.resetTransform()
        self.ui.sceneView.ensureVisible(self.scene.sceneRect(), 100, 100)
        try:
            scale_factor = 0.8 * min(
                self.ui.sceneView.width() / self.scene.sceneRect().width(),
                self.ui.sceneView.height() / self.scene.sceneRect().height(),
            )
            self.ui.sceneView.scale(scale_factor, scale_factor)
        except ZeroDivisionError:
            # Don't worry
            pass

    def get_xrandr_info(self):
        _xrandr_data = xrandr.read_data()
        self.screen = xrandr.parse_data(_xrandr_data)
        self.screen.update_replica_of()
        self.reset_screen = xrandr.parse_data(_xrandr_data)

    def monitor_selected(self, name):
        if not name:
            return
        # needed so we don't flip through all modes as they are added
        self.ui.modes.blockSignals(True)
        # Show modes
        self.ui.modes.clear()
        monitor = self.screen.monitors[name]
        for mode in monitor.modes:
            self.ui.modes.addItem(mode)

        mode = monitor.get_current_mode()
        self.ui.modes.setCurrentText(mode.name)
        if monitor.orientation in ("normal", "inverted"):
            h_scale = monitor.res_x / mode.res_x
            v_scale = monitor.res_y / mode.res_y
        else:
            h_scale = monitor.res_y / mode.res_x
            v_scale = monitor.res_x / mode.res_y

        self.ui.horizontalScale.setValue(h_scale * 1000)
        self.ui.verticalScale.setValue(v_scale * 1000)
        self.ui.primary.setChecked(monitor.primary)
        self.ui.enabled.setChecked(monitor.enabled)
        self.ui.orientationCombo.setCurrentText(monitor.orientation)

        self.ui.replicaOf.clear()
        self.ui.replicaOf.addItem("None")
        for mon in self.screen.monitors:
            if mon != name:
                self.ui.replicaOf.addItem(mon)
                if mon in self.screen.monitors[name].replica_of:
                    self.ui.replicaOf.setCurrentText(mon)
        self.ui.modes.blockSignals(False)

        guessed_scale_mode = monitor.guess_scale_mode()
        self.ui.scaleModeCombo.setCurrentText(guessed_scale_mode)
        self.scale_mode_changed()

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
    Window(loader.load(ui_file))
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
