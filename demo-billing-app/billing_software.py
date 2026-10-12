import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel

class StandaloneBillingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enterprise Billing Portal")
        self.setGeometry(220, 200, 460, 350)
        self.setStyleSheet("background-color: #13131f; color: white; font-family: 'Segoe UI';")

        layout = QVBoxLayout()
        self.status_banner = QLabel("Status: Waiting for Employee Action...")
        self.status_banner.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #38bdf8; "
            "background-color: #1e293b; padding: 10px; border-radius: 6px;"
        )
        layout.addWidget(self.status_banner)

        btn_style = """
            QPushButton {
                background-color: #1e1e30;
                color: white;
                border: 1px solid #383854;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-height: 55px;
            }
            QPushButton:hover {
                background-color: #2a1b38;
                border: 1.5px solid #fc038c;
            }
        """

        self.btn1 = QPushButton("Open Customer Invoices")
        self.btn1.setAccessibleName("Open Customer Invoices")
        self.btn1.setStyleSheet(btn_style)
        self.btn1.clicked.connect(self.on_click_invoices)
        layout.addWidget(self.btn1)

        self.btn2 = QPushButton("Verify Account Balance")
        self.btn2.setAccessibleName("Verify Account Balance")
        self.btn2.setStyleSheet(btn_style)
        self.btn2.clicked.connect(self.on_click_verify)
        layout.addWidget(self.btn2)

        self.btn3 = QPushButton("Approve & Issue Refund")
        self.btn3.setAccessibleName("Approve & Issue Refund")
        self.btn3.setStyleSheet(btn_style)
        self.btn3.clicked.connect(self.on_click_refund)
        layout.addWidget(self.btn3)

        self.setLayout(layout)

    def on_click_invoices(self):
        self.status_banner.setText("Status: Invoices Loaded")
        self.btn1.setText("Open Customer Invoices (Done)")
        self.btn1.setAccessibleName("Open Customer Invoices (Done)")
        print("[Billing App] Step 1 Clicked!")

    def on_click_verify(self):
        self.status_banner.setText("Status: Balance Verified")
        self.btn2.setText("Verify Account Balance (Done)")
        self.btn2.setAccessibleName("Verify Account Balance (Done)")
        print("[Billing App] Step 2 Clicked!")

    def on_click_refund(self):
        self.status_banner.setText("Status: Refund Approved!")
        self.btn3.setText("Approve & Issue Refund (Done)")
        self.btn3.setAccessibleName("Approve & Issue Refund (Done)")
        self.status_banner.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #4ade80; "
            "background-color: #14532d; padding: 10px; border-radius: 6px;"
        )
        print("[Billing App] Step 3 Clicked!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = StandaloneBillingApp()
    win.show()
    sys.exit(app.exec())