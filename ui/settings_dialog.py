from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QGroupBox, QMessageBox, QFrame
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsSettings


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cropix — Settings")
        self.setMinimumWidth(460)
        self.settings = QgsSettings()
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
            QLineEdit {
                border: 1px solid #dde8dd;
                border-radius: 6px;
                padding: 8px 12px;
                background: #fafffe;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #2d7a2d; }
            QLabel { font-size: 12px; }
        """)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Banner ───────────────────────────────────────
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0d2e0d, stop:1 #2d7a2d
                );
            }
        """)
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(24, 18, 24, 18)
        banner_layout.setSpacing(3)

        title = QLabel("Settings")
        title.setStyleSheet(
            "color: white; font-size: 17px; font-weight: bold; background: transparent;"
        )
        title.setAlignment(Qt.AlignCenter)

        sub = QLabel("Configure your Sentinel Hub OAuth credentials")
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.65); font-size: 10px; background: transparent;"
        )
        sub.setAlignment(Qt.AlignCenter)

        banner_layout.addWidget(title)
        banner_layout.addWidget(sub)
        layout.addWidget(banner)

        # ── Body ─────────────────────────────────────────
        body = QFrame()
        body.setStyleSheet("QFrame { background: #f4f6f4; }")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 16, 20, 16)
        body_layout.setSpacing(12)

        # OAuth credentials
        oauth_group = QGroupBox("Sentinel Hub OAuth Credentials")
        oauth_layout = QVBoxLayout()
        oauth_layout.setContentsMargins(14, 8, 14, 14)
        oauth_layout.setSpacing(8)

        info = QLabel(
            "Get your free OAuth client at:\n"
            "shapps.dataspace.copernicus.eu  →  Dashboard  →  OAuth Clients"
        )
        info.setStyleSheet("""
            color: #555;
            font-size: 11px;
            background: #f0f7f0;
            border: 1px solid #c8e6c8;
            border-radius: 6px;
            padding: 8px 12px;
        """)
        info.setWordWrap(True)
        oauth_layout.addWidget(info)

        lbl1 = QLabel("Client ID:")
        lbl1.setStyleSheet("color: #555; font-size: 11px; margin-top: 4px;")
        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("sh-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")

        lbl2 = QLabel("Client Secret:")
        lbl2.setStyleSheet("color: #555; font-size: 11px;")
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setEchoMode(QLineEdit.Password)
        self.client_secret_input.setPlaceholderText("••••••••••••••••••••••••")

        test_btn = QPushButton("Test Connection")
        test_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #2d7a2d;
                border-radius: 7px;
                padding: 8px 16px;
                background: white;
                color: #2d7a2d;
                font-size: 12px;
                font-weight: bold;
                margin-top: 4px;
            }
            QPushButton:hover { background: #f0f7f0; }
        """)
        test_btn.clicked.connect(self.test_connection)

        oauth_layout.addWidget(lbl1)
        oauth_layout.addWidget(self.client_id_input)
        oauth_layout.addWidget(lbl2)
        oauth_layout.addWidget(self.client_secret_input)
        oauth_layout.addWidget(test_btn)
        oauth_group.setLayout(oauth_layout)
        body_layout.addWidget(oauth_group)

        # Download settings
        dl_group = QGroupBox("Download Settings")
        dl_layout = QHBoxLayout()
        dl_layout.setContentsMargins(14, 8, 14, 14)
        dl_layout.setAlignment(Qt.AlignLeft)
        dl_layout.setSpacing(10)

        cloud_lbl = QLabel("Max cloud cover (%):")
        cloud_lbl.setStyleSheet("color: #555; font-size: 11px;")
        self.cloud_input = QLineEdit()
        self.cloud_input.setPlaceholderText("30")
        self.cloud_input.setMaximumWidth(70)
        self.cloud_input.setToolTip(
            "Scenes with cloud cover above this value will be skipped."
        )

        dl_layout.addWidget(cloud_lbl)
        dl_layout.addWidget(self.cloud_input)
        dl_layout.addStretch()
        dl_group.setLayout(dl_layout)
        body_layout.addWidget(dl_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a5c1a, stop:1 #2d7a2d
                );
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #145014, stop:1 #256325
                );
            }
        """)
        save_btn.clicked.connect(self.save_settings)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 9px 18px;
                background: white;
                color: #888;
                font-size: 12px;
            }
            QPushButton:hover { background: #f0f0f0; }
        """)
        cancel_btn.clicked.connect(self.close)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        body_layout.addLayout(btn_layout)

        layout.addWidget(body)
        self.setLayout(layout)

    def load_settings(self):
        self.client_id_input.setText(
            self.settings.value("cropix/client_id", "")
        )
        self.client_secret_input.setText(
            self.settings.value("cropix/client_secret", "")
        )
        self.cloud_input.setText(
            self.settings.value("cropix/max_cloud", "30")
        )

    def save_settings(self):
        self.settings.setValue(
            "cropix/client_id", self.client_id_input.text().strip()
        )
        self.settings.setValue(
            "cropix/client_secret", self.client_secret_input.text()
        )
        self.settings.setValue(
            "cropix/max_cloud", self.cloud_input.text() or "30"
        )
        QMessageBox.information(self, "Saved", "Settings saved successfully.")
        self.close()

    def test_connection(self):
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text()

        if not client_id or not client_secret:
            QMessageBox.warning(
                self, "Missing Credentials",
                "Please enter your Client ID and Client Secret first."
            )
            return

        try:
            from sentinelhub import SHConfig, SentinelHubSession
            config = SHConfig()
            config.sh_client_id = client_id
            config.sh_client_secret = client_secret
            config.sh_base_url = "https://sh.dataspace.copernicus.eu"
            config.sh_token_url = (
                "https://identity.dataspace.copernicus.eu"
                "/auth/realms/CDSE/protocol/openid-connect/token"
            )

            session = SentinelHubSession(config=config)
            _ = session.token

            QMessageBox.information(
                self, "Connection Successful",
                "OAuth credentials are valid.\n"
                "You are ready to download Sentinel-2 data."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Connection Failed",
                f"Could not authenticate:\n\n{str(e)}"
            )