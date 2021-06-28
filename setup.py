import os
import sys
import PyQt5
from cx_Freeze import setup, Executable

base = None
if sys.platform == "win32":
    base = "Win32GUI"

include_files = [(os.path.dirname(PyQt5.__file__), "lib")]
packages = ["sys", "numpy"]
options = {
    'build_exe': {
        'include_files':include_files,
        'packages':packages,
    },
}

executables = [Executable("main.py", base=base)]

setup(
    name="PanyImage",
    version="1.0.0",
    description="PanyImage v1.0.0",
    options=options,
    executables=executables,
)