"""Buduje plik .exe: python build_exe.py  (wynik: dist/RadarOkazji.exe)."""
import subprocess
import sys


def main() -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                           "requirements.txt", "pyinstaller"])
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
        "--windowed", "--name", "RadarOkazji", "app.py"])
    print("\nGotowe: dist/RadarOkazji.exe")


if __name__ == "__main__":
    main()
