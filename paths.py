"""Keep installed Windows libraries in their original AppData location."""
import os
from pathlib import Path
import sys

APP_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
ASSET_DIR = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
DATA_DIR = Path(os.environ['MYGAMELIST_DATA_DIR']) if os.environ.get('MYGAMELIST_DATA_DIR') else (
    Path(os.environ.get('APPDATA', str(APP_DIR))) / 'MyGameList' if getattr(sys,'frozen',False) else APP_DIR)
DATA_DIR.mkdir(parents=True,exist_ok=True)
