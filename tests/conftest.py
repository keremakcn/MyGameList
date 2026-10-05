"""Import the application only after selecting an isolated, temporary library."""
import atexit
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
folder=tempfile.TemporaryDirectory(prefix='mygamelist-tests-')
previous=os.environ.get('MYGAMELIST_DATA_DIR')
os.environ['MYGAMELIST_DATA_DIR']=folder.name
def cleanup():
    if previous is None: os.environ.pop('MYGAMELIST_DATA_DIR',None)
    else: os.environ['MYGAMELIST_DATA_DIR']=previous
    folder.cleanup()
atexit.register(cleanup)
