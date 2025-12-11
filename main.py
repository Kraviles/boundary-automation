import sys
import os
os.environ["QSG_RHI_BACKEND"] = "opengl"
from PySide6 import QtWidgets as qtw

import src.interface


if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)
    main_window = src.interface.MainWindow()
    main_window.show()
    sys.exit(app.exec())

