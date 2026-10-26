import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel

class StandaloneCRMApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enterprise CRM Portal")
        self.setGeometry(720, 200, 480, 360)
        self.setStyleSheet("background-color: #0f172a; color: white; font-family: 'Segoe UI';")

        layout = QVBoxLayout()
        self.status_banner = QLabel("CRM Status: Waiting for Account Rep...")
        self.status_banner.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #a78bfa; "
            "background-color: #1e1b4b; padding: 12px; border-radius: 8px;"
        )
        layout.addWidget(self.status_banner)

        btn_style = """
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #475569;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-height: 55px;
            }
            QPushButton:hover {
                background-color: #334155;
                border: 1.5px solid #a855f7;
            }
        """

        self.btn1 = QPushButton("Create Customer Record")
        self.btn1.setAccessibleName("Create Customer Record")
        self.btn1.setStyleSheet(btn_style)
        self.btn1.clicked.connect(self.on_click_record)
        layout.addWidget(self.btn1)

        self.btn2 = QPushButton("Configure Credit Limit")
        self.btn2.setAccessibleName("Configure Credit Limit")
        self.btn2.setStyleSheet(btn_style)
        self.btn2.clicked.connect(self.on_click_credit)
        layout.addWidget(self.btn2)

        self.btn3 = QPushButton("Dispatch Onboarding Welcome")
        self.btn3.setAccessibleName("Dispatch Onboarding Welcome")
        self.btn3.setStyleSheet(btn_style)
        self.btn3.clicked.connect(self.on_click_dispatch)
        layout.addWidget(self.btn3)

        self.setLayout(layout)

    def on_click_record(self):
        self.status_banner.setText("CRM Status: Customer Record Created")
        self.btn1.setText("Create Customer Record (Done)")
        self.btn1.setAccessibleName("Create Customer Record (Done)")
        print("[CRM App] Step 1: Customer Record Created!")

    def on_click_credit(self):
        self.status_banner.setText("CRM Status: Credit Limit Approved ($50,000)")
        self.btn2.setText("Configure Credit Limit (Done)")
        self.btn2.setAccessibleName("Configure Credit Limit (Done)")
        print("[CRM App] Step 2: Credit Limit Configured!")

    def on_click_dispatch(self):
        self.status_banner.setText("CRM Status: Welcome Package Dispatched!")
        self.btn3.setText("Dispatch Onboarding Welcome (Done)")
        self.btn3.setAccessibleName("Dispatch Onboarding Welcome (Done)")
        self.status_banner.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #4ade80; "
            "background-color: #14532d; padding: 12px; border-radius: 8px;"
        )
        print("[CRM App] Step 3: Welcome Dispatched!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = StandaloneCRMApp()
    win.show()
    sys.exit(app.exec())
