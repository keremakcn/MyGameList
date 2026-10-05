"""A separate demo library for desktop browser checks."""
import os
import sys
from pathlib import Path
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
folder=tempfile.TemporaryDirectory(prefix='mygamelist-preview-')
os.environ['MYGAMELIST_DATA_DIR']=folder.name
from app import app,discovery,save_game_to_db,add_to_my_list
from game_client import GameDiscoveryError
from waitress import serve

def game(number):
    return {'id':number,'name':{123:'Portal',124:'A very long game title for desktop layout checks',125:'Another game'}.get(number,'Unavailable'),
            'released':'2011-04-19','description_raw':'A private gaming journal and a memorable adventure.',
            'genres':[{'name':'Puzzle'}],'platforms':[{'platform':{'name':'PC'}}],
            'developers':[{'id':1,'name':'Valve'}],'publishers':[{'id':2,'name':'Publisher'}],
            'metacritic':95,'background_image':None}
def get(resource,**params):
    if params.get('search')=='offline' or resource=='games/999': raise GameDiscoveryError()
    if resource.startswith('games/'): return game(int(resource.split('/')[1]))
    if params.get('search')=='nothing': return {'results':[],'next':False}
    if resource in ('developers','publishers'): return {'results':[{'id':1,'name':'Valve','games_count':3}],'next':False}
    return {'results':[game(123),game(124),game(125)],'next':False}
discovery.get=get
save_game_to_db(game(125))
add_to_my_list(125)
if __name__=='__main__': serve(app,host='127.0.0.1',port=5064)
