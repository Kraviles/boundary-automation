import sys
import os
os.environ["QSG_RHI_BACKEND"] = "opengl"
from PySide6 import QtWidgets as qtw

from src.interface import MainWindow



if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())

prs = fetch_pull_requests()

summaries = [summarize_pr(pr) for pr in prs]
df = pd.DataFrame(summaries)
df.head()
