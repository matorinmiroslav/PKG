import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox, QPushButton, QColorDialog, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

import converter

class ColorConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лабораторная №1 (RGB - LAB - CMYK)")
        self.resize(800, 500)

        self.is_updating = False
        self.init_ui()
        self.update_all_from_rgb(128, 128, 128)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Верхняя панель: Плашка цвета + Кнопка палитры + Предупреждение
        top_layout = QHBoxLayout()

        self.color_preview = QFrame()
        self.color_preview.setFixedSize(100, 60)
        self.color_preview.setStyleSheet("border: 2px solid #555; background-color: rgb(128,128,128);")

        self.btn_palette = QPushButton("Выбрать из палитры")
        self.btn_palette.clicked.connect(self.open_color_dialog)

        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red; font-weight: bold;")
        self.warning_label.setWordWrap(True)

        top_layout.addWidget(self.color_preview)
        top_layout.addWidget(self.btn_palette)
        top_layout.addWidget(self.warning_label, stretch=1)

        main_layout.addLayout(top_layout)

        # Панели для RGB, LAB, CMYK
        models_layout = QHBoxLayout()

        rgb_group, self.rgb_controls = self.create_model_group("RGB", [
            ("R", 0, 255, False), ("G", 0, 255, False), ("B", 0, 255, False)
        ], self.on_rgb_changed)

        lab_group, self.lab_controls = self.create_model_group("LAB", [
            ("L", 0, 100, True), ("A", -128, 128, True), ("B", -128, 128, True)
        ], self.on_lab_changed)

        cmyk_group, self.cmyk_controls = self.create_model_group("CMYK", [
            ("C", 0, 100, True), ("M", 0, 100, True), ("Y", 0, 100, True), ("K", 0, 100, True)
        ], self.on_cmyk_changed)

        models_layout.addWidget(rgb_group)
        models_layout.addWidget(lab_group)
        models_layout.addWidget(cmyk_group)

        main_layout.addLayout(models_layout)

    def create_model_group(self, title, components, callback):
        group = QFrame()
        group.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel(f"<b>{title}</b>", alignment=Qt.AlignmentFlag.AlignCenter))
        controls = {}

        for name, min_v, max_v, is_float in components:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{name}:"))

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(min_v), int(max_v))

            if is_float:
                spin = QDoubleSpinBox()
                spin.setRange(float(min_v), float(max_v))
                spin.setDecimals(1)
            else:
                spin = QSpinBox()
                spin.setRange(int(min_v), int(max_v))

            slider.valueChanged.connect(lambda v, s=spin, f=is_float: s.setValue(v))
            if is_float:
                spin.valueChanged.connect(lambda v, sl=slider: sl.setValue(int(v)))
            else:
                spin.valueChanged.connect(slider.setValue)

            spin.valueChanged.connect(callback)

            row.addWidget(slider)
            row.addWidget(spin)
            layout.addLayout(row)

            controls[name] = {"slider": slider, "spin": spin}

        return group, controls

    def update_all_from_rgb(self, r, g, b, warning=""):
        self.is_updating = True

        self.color_preview.setStyleSheet(f"border: 2px solid #555; background-color: rgb({r},{g},{b});")
        self.warning_label.setText(warning)

        # RGB
        self.rgb_controls["R"]["spin"].setValue(r)
        self.rgb_controls["G"]["spin"].setValue(g)
        self.rgb_controls["B"]["spin"].setValue(b)

        # LAB
        l, a, b_val = converter.rgb_to_lab(r, g, b)
        self.lab_controls["L"]["spin"].setValue(l)
        self.lab_controls["A"]["spin"].setValue(a)
        self.lab_controls["B"]["spin"].setValue(b_val)

        # CMYK
        c, m, y, k = converter.rgb_to_cmyk(r, g, b)
        self.cmyk_controls["C"]["spin"].setValue(c)
        self.cmyk_controls["M"]["spin"].setValue(m)
        self.cmyk_controls["Y"]["spin"].setValue(y)
        self.cmyk_controls["K"]["spin"].setValue(k)

        self.is_updating = False

    def on_rgb_changed(self):
        if self.is_updating: return
        r = self.rgb_controls["R"]["spin"].value()
        g = self.rgb_controls["G"]["spin"].value()
        b = self.rgb_controls["B"]["spin"].value()
        self.update_all_from_rgb(r, g, b)

    def on_lab_changed(self):
        if self.is_updating: return
        l = self.lab_controls["L"]["spin"].value()
        a = self.lab_controls["A"]["spin"].value()
        b_val = self.lab_controls["B"]["spin"].value()

        (r, g, b), out_of_gamut = converter.lab_to_rgb(l, a, b_val)
        warn = "Выход за границы sRGB! Выполнена обрезка." if out_of_gamut else ""
        self.update_all_from_rgb(r, g, b, warning=warn)

    def on_cmyk_changed(self):
        if self.is_updating: return
        c = self.cmyk_controls["C"]["spin"].value()
        m = self.cmyk_controls["M"]["spin"].value()
        y = self.cmyk_controls["Y"]["spin"].value()
        k = self.cmyk_controls["K"]["spin"].value()

        r, g, b = converter.cmyk_to_rgb(c, m, y, k)
        self.update_all_from_rgb(r, g, b)

    def open_color_dialog(self):
        r = self.rgb_controls["R"]["spin"].value()
        g = self.rgb_controls["G"]["spin"].value()
        b = self.rgb_controls["B"]["spin"].value()

        color = QColorDialog.getColor(QColor(r, g, b), self, "Выберите цвет")
        if color.isValid():
            self.update_all_from_rgb(color.red(), color.green(), color.blue())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ColorConverterApp()
    window.show()
    sys.exit(app.exec())