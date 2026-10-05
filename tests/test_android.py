"""Exercise native startup in fresh processes, before global desktop app imports."""
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BRIDGE=ROOT/'android/app/src/main/python'

def run_script(script,folder):
    env=os.environ.copy()
    env.pop('MYGAMELIST_PLATFORM',None)
    result=subprocess.run([sys.executable,'-c',script,str(folder)],cwd=ROOT,env=env,
                          capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=40)
    assert result.returncode==0,result.stdout+result.stderr

IMPORTS="import sys;sys.path.insert(0,'android/app/src/main/python');import android_bridge\n"

def test_native_guard_private_storage_and_restart(tmp_path):
    run_script(IMPORTS+r"""
from pathlib import Path
import secrets
from game_client import GameDiscoveryError
token=secrets.token_urlsafe(32)
app=android_bridge.create_android_app(sys.argv[1],token)
import app as module
import database
assert Path(database.DB_NAME)==Path(sys.argv[1])/'library/games.db'
assert app.config['ANDROID_APP']
assert app.config['SESSION_COOKIE_NAME']=='mygamelist_android'
client=app.test_client()
assert client.get('/').status_code==403
assert client.get('/static/style.css').status_code==403
assert client.get('/_native/start').status_code==403
assert client.get('/_native/start',headers={'X-Native-Token':'wrong'}).status_code==403
response=client.get('/_native/start',headers={'X-Native-Token':token})
assert response.status_code==302
cookies=response.headers.getlist('Set-Cookie')
assert any('native_access=' in x and 'HttpOnly' in x and 'SameSite=Strict' in x for x in cookies)
assert client.get('/').status_code==200
assert b'fonts.googleapis.com' not in client.get('/').data
assert b'class="android-app"' in client.get('/').data
# Native authentication rejects cross-host requests before their routing error.
assert client.get('/',headers={'Host':'evil.example'}).status_code==403
assert client.post('/library/add/123').status_code==400
with client.session_transaction() as session: csrf=session['csrf']
def post(path,**data):return client.post(path,data={'csrf':csrf,**data})
module.discovery.get=lambda resource,**params:{'id':int(resource.split('/')[1]),'name':'Portal','description_raw':'Cached game details'}
assert post('/library/add/123').status_code==302
post('/library/add/124')
post('/library/add/123')
assert len(database.get_my_games())==2
assert post('/edit/123',status='Played',my_rating='9',note='Android özel not 🕹️',favorite='on',played_date='2026-10-05').status_code==302
before=database.get_my_game_by_id(123)
order=[row['game_id'] for row in database.get_my_games()]
undo=database.delete_with_undo(123)
assert database.undo_delete(undo)
assert database.get_my_game_by_id(123)==before
assert [row['game_id'] for row in database.get_my_games()]==order
assert not database.undo_delete(undo)
connection=database.get_connection()
connection.execute("UPDATE games SET local_image_path='123.png' WHERE id=123")
connection.commit();connection.close()
(Path(module.GAME_IMAGES_DIR)/'123.png').write_bytes(b'cached-cover-test')
assert b'/game_images/123.png' in client.get('/edit/123').data
assert client.get('/game_images/123.png').data==b'cached-cover-test'
module.discovery.get=lambda *a,**kw:(_ for _ in ()).throw(GameDiscoveryError())
assert b'Cached game details' in client.get('/game/123').data
assert client.get('/settings').status_code==200
assert b'name="api_key"' not in client.get('/settings').data
assert client.get('/set-language/tr').status_code==302
assert b'<html lang="tr">' in client.get('/').data
""",tmp_path)
    run_script(IMPORTS+r"""
import secrets
token=secrets.token_urlsafe(32)
app=android_bridge.create_android_app(sys.argv[1],token)
client=app.test_client()
client.get('/_native/start',headers={'X-Native-Token':token})
assert b'<html lang="tr">' in client.get('/').data
import database
game=database.get_my_game_by_id(123)
assert game['note']=='Android özel not 🕹️'
assert game['my_rating']==9
assert game['favorite']==1
assert game['played_date']=='2026-10-05'
assert game['local_image_path']=='123.png'
assert len(database.get_my_games())==2
""",tmp_path)

def test_native_server_single_start_and_http_bootstrap(tmp_path):
    run_script(IMPORTS+r"""
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen,build_opener,HTTPCookieProcessor
from urllib.error import HTTPError
from http.cookiejar import CookieJar
with ThreadPoolExecutor(max_workers=6) as pool:
    connections=list(pool.map(lambda _:json.loads(android_bridge.start(sys.argv[1])),range(6)))
assert all(connection==connections[0] for connection in connections)
connection=connections[0]
assert connection['url'].startswith('http://127.0.0.1:')
try: urlopen(connection['url']+'/',timeout=5);raise AssertionError('unguarded library')
except HTTPError as error: assert error.code==403
opener=build_opener(HTTPCookieProcessor(CookieJar()))
request=Request(connection['url']+'/_native/start',headers={'X-Native-Token':connection['token']})
with opener.open(request,timeout=5) as response:assert response.status==200
with opener.open(connection['url']+'/settings',timeout=5) as response:assert response.status==200
""",tmp_path)

def test_native_rejects_desktop_import_before_initialization(tmp_path):
    run_script(IMPORTS+r"""
import os
os.environ['MYGAMELIST_DATA_DIR']=sys.argv[1]
import paths
try:android_bridge.create_android_app(sys.argv[1],'token');raise AssertionError('must reject reused desktop state')
except RuntimeError:pass
""",tmp_path)
