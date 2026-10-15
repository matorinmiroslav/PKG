import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
                             QProgressBar, QLabel, QHeaderView, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image, UnidentifiedImageError


# 1. DATA / PARSING LAYER (Infrastructure)
class ImageParser:
    """Слой, отвечающий непосредственно за извлечение данных из файла."""

    SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.gif', '.tif', '.tiff', '.bmp', '.png', '.pcx')

    @staticmethod
    def parse(filepath: str):
        try:
            with Image.open(filepath) as img:
                filename = os.path.basename(filepath)
                fmt = img.format.upper() if img.format else "UNKNOWN"

                # 1. Размер (в пикселях)
                width, height = img.size
                size_str = f"{width} x {height}"

                # 2. Разрешение (DPI)
                dpi = img.info.get('dpi')
                if dpi and isinstance(dpi, (tuple, list)) and len(dpi) >= 2:
                    dpi_str = f"{round(dpi[0])} x {round(dpi[1])}"
                else:
                    dpi_str = "Не указано"

                # 3. Глубина цвета
                mode_to_depth = {
                    '1': 1,
                    'L': 8, 'P': 8,
                    'RGB': 24, 'YCbCr': 24, 'LAB': 24, 'HSV': 24,
                    'RGBA': 32, 'CMYK': 32, 'I': 32, 'F': 32
                }
                color_depth = mode_to_depth.get(img.mode, "Неизвестно")
                if color_depth != "Неизвестно":
                    color_depth = f"{color_depth} бит"

                # 4. Сжатие
                compression = img.info.get('compression')
                if not compression:
                    if fmt in ('JPEG', 'JPG'):
                        compression = "JPEG (Lossy)"
                    elif fmt == 'PNG':
                        compression = "Deflate (Lossless)"
                    elif fmt == 'GIF':
                        compression = "LZW (Lossless)"
                    elif fmt == 'BMP':
                        compression = "Без сжатия / RLE"
                    elif fmt == 'PCX':
                        compression = "RLE (Lossless)"
                    else:
                        compression = "Не определено"
                else:
                    compression = str(compression)

                #ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ
                jpeg_quant = "Не применимо"
                gif_colors = "Не применимо"

                # 5. Матрица квантования для JPEG
                if fmt in ('JPEG', 'JPG'):
                    if hasattr(img, 'quantization') and img.quantization:
                        if 0 in img.quantization:
                            q_matrix = img.quantization[0]
                            if isinstance(q_matrix, (list, tuple)) and len(q_matrix) >= 8:
                                short_matrix = ", ".join(map(str, q_matrix[:8]))
                                jpeg_quant = f"Матрица 0 (первые 8): [{short_matrix}...]"
                            else:
                                jpeg_quant = "Присутствует"
                        else:
                            jpeg_quant = "Присутствует"
                    else:
                        jpeg_quant = "Стандартная / Скрыта"

                # 6. Количество цветов в палитре GIF
                if fmt == 'GIF' or img.mode == 'P':
                    if img.palette:
                        try:
                            if hasattr(img.palette, 'colors') and img.palette.colors:
                                gif_colors = f"{len(img.palette.colors)} цветов"
                            else:
                                palette_bytes = img.palette.getdata()[1]
                                gif_colors = f"{len(palette_bytes) // 3} цветов"
                        except Exception:
                            gif_colors = "До 256 цветов"
                    else:
                        gif_colors = "Нет палитры"

                return {
                    "file": filename,
                    "size": size_str,
                    "dpi": dpi_str,
                    "depth": color_depth,
                    "compression": compression,
                    "jpeg_quant": jpeg_quant,
                    "gif_colors": gif_colors
                }
        except (UnidentifiedImageError, IOError):
            return None


# 2. CORE / BUSINESS LOGIC LAYER (Engine)
class ScannerThread(QThread):
    progress_updated = pyqtSignal(int, int)
    batch_ready = pyqtSignal(list)
    scan_finished = pyqtSignal(float)

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path
        self._is_running = True

    def run(self):
        import time
        start_time = time.time()

        files_to_process = []
        for root, _, files in os.walk(self.folder_path):
            if not self._is_running:
                break
            for file in files:
                if file.lower().endswith(ImageParser.SUPPORTED_FORMATS):
                    files_to_process.append(os.path.join(root, file))

        total_files = len(files_to_process)
        if total_files == 0:
            self.scan_finished.emit(0.0)
            return

        processed = 0
        batch = []
        batch_size = 50

        max_workers = (os.cpu_count() or 2) * 2
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(ImageParser.parse, path): path for path in files_to_process}

            for future in as_completed(futures):
                if not self._is_running:
                    break

                result = future.result()
                processed += 1

                if result:
                    batch.append(result)

                if len(batch) >= batch_size or processed == total_files:
                    self.batch_ready.emit(batch)
                    batch = []
                    self.progress_updated.emit(processed, total_files)

        end_time = time.time()
        self.scan_finished.emit(float(end_time - start_time))

    def stop(self):
        self._is_running = False


# 3. PRESENTATION LAYER (UI)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Metadata Analyzer (Lab 2)")
        self.resize(1100, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.btn_select_folder = QPushButton("Выбрать папку для сканирования")
        self.btn_select_folder.setFixedHeight(40)
        self.btn_select_folder.clicked.connect(self.select_folder)
        layout.addWidget(self.btn_select_folder)

        self.lbl_status = QLabel("Ожидание...")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Имя файла", "Размер (px)", "Разрешение (DPI)",
            "Глубина цвета", "Сжатие", "Матрица квант. (JPEG)", "Цветов в палитре (GIF)"
        ])

        # Настройка автоматического растяжения колонок
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        self.scanner_thread = None

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.table.setRowCount(0)
            self.lbl_status.setText(f"Сканирование папки: {folder}")
            self.progress_bar.setValue(0)

            self.scanner_thread = ScannerThread(folder)
            self.scanner_thread.batch_ready.connect(self.add_batch_to_table)
            self.scanner_thread.progress_updated.connect(self.update_progress)
            self.scanner_thread.scan_finished.connect(self.scan_complete)
            self.scanner_thread.start()

    def add_batch_to_table(self, batch: list):
        for item in batch:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            self.table.setItem(row_position, 0, QTableWidgetItem(item["file"]))
            self.table.setItem(row_position, 1, QTableWidgetItem(item["size"]))
            self.table.setItem(row_position, 2, QTableWidgetItem(item["dpi"]))
            self.table.setItem(row_position, 3, QTableWidgetItem(item["depth"]))
            self.table.setItem(row_position, 4, QTableWidgetItem(item["compression"]))
            self.table.setItem(row_position, 5, QTableWidgetItem(item["jpeg_quant"]))
            self.table.setItem(row_position, 6, QTableWidgetItem(item["gif_colors"]))

    def update_progress(self, processed: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(processed)
        self.lbl_status.setText(f"Обработано файлов: {processed} из {total}")

    def scan_complete(self, duration: float):
        self.lbl_status.setText(
            f"Сканирование завершено за {duration:.2f} сек. Всего найдено изображений: {self.table.rowCount()}")
        QMessageBox.information(self, "Готово", f"Сканирование успешно завершено за {duration:.2f} секунд(ы)!")

    def closeEvent(self, event):
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.stop()
            self.scanner_thread.wait()
        event.accept()


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    plugins_path = current_dir / '.venv' / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'PyQt6' / 'Qt6' / 'plugins'

    if plugins_path.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins_path)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

