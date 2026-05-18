import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QDateEdit, QProgressBar,
    QGroupBox, QMessageBox, QCheckBox, QFrame
)
from qgis.PyQt.QtCore import QDate, Qt, QSize
from qgis.PyQt.QtGui import (
    QIcon, QPixmap, QPainter, QColor,
    QBrush, QLinearGradient
)
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis.core import QgsProject, QgsMapLayer, QgsSettings

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def svg_icon(svg_str, size=18):
    renderer = QSvgRenderer(svg_str.encode())
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


ICON_SETTINGS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
</svg>"""

ICON_RUN = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polygon points="5 3 19 12 5 21 5 3"/>
</svg>"""

ICON_CLOSE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#888" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <line x1="18" y1="6" x2="6" y2="18"/>
  <line x1="6" y1="6" x2="18" y2="18"/>
</svg>"""

ICON_REFRESH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#555" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="23 4 23 10 17 10"/>
  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
</svg>"""


class HeaderBanner(QLabel):
    """
    Shows farmHeader.png as the banner background.
    No logo or text drawn on top — everything is in the image itself.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self.setMinimumWidth(500)

        img_path = os.path.join(PLUGIN_DIR, "data", "farmHeader.png")
        self._bg = QPixmap(img_path) if os.path.exists(img_path) else QPixmap()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        if not self._bg.isNull():
            scaled = self._bg.scaled(
                w, h,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            x_off = (scaled.width() - w) // 2
            y_off = (scaled.height() - h) // 2
            painter.drawPixmap(0, 0, scaled, x_off, y_off, w, h)
        else:
            # Fallback gradient when image is missing
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, QColor("#0d2e0d"))
            grad.setColorAt(1, QColor("#2d7a2d"))
            painter.fillRect(0, 0, w, h, QBrush(grad))

        # Very subtle dark vignette at top and bottom edges
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 30))

        painter.end()


class CropixDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("Cropix")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog { background-color: #f4f6f4; }
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                color: #444;
                border: 1px solid #dde8dd;
                border-radius: 10px;
                margin-top: 8px;
                padding-top: 8px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #2d7a2d;
            }
            QComboBox, QDateEdit {
                border: 1px solid #dde8dd;
                border-radius: 6px;
                padding: 6px 10px;
                background: #fafffe;
                font-size: 12px;
            }
            QComboBox:focus, QDateEdit:focus { border-color: #2d7a2d; }
            QCheckBox { font-size: 12px; spacing: 6px; }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border-radius: 4px;
                border: 2px solid #ccc;
            }
            QCheckBox::indicator:checked {
                background-color: #2d7a2d;
                border-color: #2d7a2d;
            }
            QLabel { font-size: 12px; }
            QProgressBar {
                border: none;
                border-radius: 5px;
                background: #e8f0e8;
                height: 8px;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2d7a2d, stop:1 #52b852
                );
            }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(HeaderBanner())

        body = QFrame()
        body.setStyleSheet("QFrame { background: #f4f6f4; }")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 16, 20, 16)
        body_layout.setSpacing(12)

        # 1. Farm layer
        farm_group = QGroupBox("1.  Farm Polygon")
        farm_layout = QVBoxLayout()
        farm_layout.setContentsMargins(12, 8, 12, 12)
        farm_layout.setSpacing(6)

        self.layer_combo = QComboBox()
        self.refresh_layers()

        refresh_btn = QPushButton("  Refresh")
        refresh_btn.setIcon(svg_icon(ICON_REFRESH, 14))
        refresh_btn.setIconSize(QSize(14, 14))
        refresh_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #dde8dd;
                border-radius: 6px;
                padding: 5px 12px;
                background: #f4f6f4;
                color: #444;
                font-size: 11px;
            }
            QPushButton:hover { background: #e8f0e8; }
        """)
        refresh_btn.setFixedWidth(100)
        refresh_btn.clicked.connect(self.refresh_layers)

        layer_row = QHBoxLayout()
        layer_row.addWidget(self.layer_combo)
        layer_row.addWidget(refresh_btn)

        lbl = QLabel("Select the polygon layer representing your farm:")
        lbl.setStyleSheet("color: #666; font-size: 11px;")
        farm_layout.addWidget(lbl)
        farm_layout.addLayout(layer_row)
        farm_group.setLayout(farm_layout)
        body_layout.addWidget(farm_group)

        # 2. Date range
        date_group = QGroupBox("2.  Date Range")
        date_layout = QHBoxLayout()
        date_layout.setContentsMargins(12, 8, 12, 12)
        date_layout.setSpacing(8)

        self.date_start = QDateEdit()
        self.date_start.setDate(QDate.currentDate().addMonths(-2))
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")

        self.date_end = QDateEdit()
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")

        from_lbl = QLabel("From:")
        from_lbl.setStyleSheet("color: #666; font-size: 11px;")
        to_lbl = QLabel("To:")
        to_lbl.setStyleSheet("color: #666; font-size: 11px;")

        date_layout.addWidget(from_lbl)
        date_layout.addWidget(self.date_start)
        date_layout.addSpacing(8)
        date_layout.addWidget(to_lbl)
        date_layout.addWidget(self.date_end)
        date_group.setLayout(date_layout)
        body_layout.addWidget(date_group)

        # 3. Indices
        index_group = QGroupBox("3.  Vegetation Indices")
        index_layout = QHBoxLayout()
        index_layout.setContentsMargins(12, 8, 12, 12)
        index_layout.setSpacing(16)

        self.indices = {}
        index_colors = {"NDVI": "#2d7a2d", "NDWI": "#1a6eb5", "EVI": "#4a7c59"}
        tooltips = {
            "NDVI": "Normalized Difference Vegetation Index\nDetects vegetation density and health",
            "NDWI": "Normalized Difference Water Index\nDetects water content in vegetation",
            "EVI":  "Enhanced Vegetation Index\nImproved NDVI with atmospheric correction",
        }
        for name in ["NDVI", "NDWI", "EVI"]:
            cb = QCheckBox(f"  {name}")
            cb.setChecked(True)
            cb.setToolTip(tooltips[name])
            cb.setStyleSheet(f"""
                QCheckBox {{ color: {index_colors[name]}; font-weight: bold; font-size: 13px; }}
                QCheckBox::indicator:checked {{
                    background-color: {index_colors[name]};
                    border-color: {index_colors[name]};
                }}
            """)
            self.indices[name] = cb
            index_layout.addWidget(cb)

        index_layout.addStretch()
        index_group.setLayout(index_layout)
        body_layout.addWidget(index_group)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        body_layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        body_layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        settings_btn = QPushButton("  Settings")
        settings_btn.setIcon(svg_icon(ICON_SETTINGS, 15))
        settings_btn.setIconSize(QSize(15, 15))
        settings_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc; border-radius: 8px;
                padding: 9px 16px; background: white;
                color: #444; font-size: 12px;
            }
            QPushButton:hover { background: #f0f0f0; border-color: #aaa; }
        """)
        settings_btn.clicked.connect(self.open_settings)

        self.run_btn = QPushButton("  Start Analysis")
        self.run_btn.setIcon(svg_icon(ICON_RUN, 15))
        self.run_btn.setIconSize(QSize(15, 15))
        self.run_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a5c1a,stop:1 #2d7a2d);
                color: white; border: none; border-radius: 8px;
                padding: 10px 24px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #145014,stop:1 #256325);
            }
            QPushButton:disabled { background: #bbb; color: #eee; }
        """)
        self.run_btn.clicked.connect(self.run_analysis)

        close_btn = QPushButton("  Close")
        close_btn.setIcon(svg_icon(ICON_CLOSE, 14))
        close_btn.setIconSize(QSize(14, 14))
        close_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc; border-radius: 8px;
                padding: 9px 16px; background: white;
                color: #888; font-size: 12px;
            }
            QPushButton:hover { background: #f0f0f0; }
        """)
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(settings_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(close_btn)
        body_layout.addLayout(btn_layout)

        layout.addWidget(body)
        self.setLayout(layout)

    def refresh_layers(self):
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer:
                if layer.geometryType() == 2:
                    self.layer_combo.addItem(layer.name(), layer.id())
        if self.layer_combo.count() == 0:
            self.layer_combo.addItem("  No polygon layers found")

    def open_settings(self):
        from .settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.exec_()

    def run_analysis(self):
        if self.layer_combo.count() == 0 or not self.layer_combo.currentData():
            QMessageBox.warning(self, "No Layer Selected",
                "Please add a polygon layer to QGIS and select it here.")
            return

        selected_indices = [k for k, v in self.indices.items() if v.isChecked()]
        if not selected_indices:
            QMessageBox.warning(self, "No Index Selected",
                "Please select at least one vegetation index.")
            return

        settings = QgsSettings()
        client_id = settings.value("cropix/client_id", "")
        client_secret = settings.value("cropix/client_secret", "")

        if not client_id or not client_secret:
            reply = QMessageBox.question(
                self, "Credentials Missing",
                "Sentinel Hub OAuth credentials are not configured.\n\nOpen Settings now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.open_settings()
            return

        layer = QgsProject.instance().mapLayer(self.layer_combo.currentData())
        date_start = self.date_start.date().toString("yyyy-MM-dd")
        date_end   = self.date_end.date().toString("yyyy-MM-dd")

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(10)
        self.status_label.setText("Preparing analysis...")

        from ..core.analyzer import CropixAnalyzer
        self.analyzer = CropixAnalyzer(
            layer=layer,
            date_start=date_start,
            date_end=date_end,
            indices=selected_indices,
            client_id=client_id,
            client_secret=client_secret,
            iface=self.iface,
            progress_callback=self.update_progress,
            done_callback=self.analysis_done,
            error_callback=self.analysis_error
        )
        self.analyzer.run()

    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status_label.setText(message)

    def analysis_done(self, results):
        self.run_btn.setEnabled(True)
        self.progress.setValue(100)
        self.status_label.setText("Analysis complete!")
        from ..report.generator import ReportGenerator
        report_path = ReportGenerator(results).generate()
        import webbrowser
        webbrowser.open(f"file://{report_path}")
        QMessageBox.information(self, "Done!",
            "Analysis complete.\nYour crop health report has been opened in the browser.")

    def analysis_error(self, error_msg):
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText("Analysis failed")
        QMessageBox.critical(self, "Error", f"Something went wrong:\n\n{error_msg}")