# Should be executed in MNE-Environment or base with MNE installed
from PyQt5.QtWidgets import QApplication, QLabel
app = QApplication([])
label = QLabel('Hello World!')
label.show()
app.exec_()
