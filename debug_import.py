import sys
import os
import src.interface

print(f"Successfully imported src.interface")

if hasattr(src.interface, 'MainWindow'):
    print(f"src.interface has attribute MainWindow")
    # You can even try to instantiate it
    try:
        mw = src.interface.MainWindow()
        print(f"Successfully instantiated MainWindow")
    except Exception as e:
        print(f"Error instantiating MainWindow: {e}")
else:
    print(f"src.interface DOES NOT have attribute MainWindow")
