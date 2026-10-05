import concurrent.futures
import importlib
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError, URLError
import pytest
import game_client
from game_client import GameClient, GameDiscoveryError


def test_cache_single_flight_and_mutation_isolation(monkeypatch):
    client=GameClient(capacity=2)
    calls=[]
    def fetch(resource,params):
        calls.append(resource)
        time.sleep(.04)
        return {'results':[{'id':1,'name':'Cached game'}],'next':False}
    monkeypatch.setattr(client,'_request',fetch)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        data=list(pool.map(lambda _:client.get('games',search='Alien'),range(8)))
    assert calls == ['games']
    data[0]['results'].clear()
    assert len(client.get('games',search='Alien')['results']) == 1
    client.get('games',search='Other')
    client.get('games',search='Third')
    assert len(client.cache)==2


def test_error_cache_and_rate_limit_cooldown(monkeypatch):
    client=GameClient()
    calls=[]
    def fail(resource,params):
        calls.append(resource)
        raise GameDiscoveryError(429,60)
    monkeypatch.setattr(client,'_request',fail)
    for query in ['first','first','other']:
        with pytest.raises(GameDiscoveryError): client.get('games',search=query)
    assert len(calls)==1


def test_gateway_header_validation_and_no_client_credentials(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,*args): return b'{"id":123,"name":"Game"}'
    def open_request(request,timeout):
        assert request.full_url=='https://api.myshelf.cloud/rawg/games/123'
        assert request.get_header('User-agent')=='MyGameList/Windows'
        assert not request.get_header('Authorization')
        return Response()
    monkeypatch.setattr(game_client,'urlopen',open_request)
    assert GameClient().get('games/123')['id']==123
    with pytest.raises(ValueError): GameClient(base_url='http://localhost/rawg/')
    with pytest.raises(ValueError): GameClient().get('games',key='secret')
    with pytest.raises(ValueError): GameClient().get('../account')


@pytest.mark.parametrize('failure',[URLError('offline'),HTTPError('https://gateway.test',429,'Busy',{},None),ValueError('Bad JSON')])
def test_transport_failures_are_controlled(monkeypatch,failure):
    monkeypatch.setattr(game_client,'urlopen',lambda *a,**kw: (_ for _ in ()).throw(failure))
    with pytest.raises(GameDiscoveryError): GameClient().get('games',search='Alien')


@pytest.fixture
def library(tmp_path,monkeypatch):
    import app as module
    import database
    monkeypatch.setattr(database,'DB_NAME',str(tmp_path/'games.db'))
    monkeypatch.setattr(module,'GAME_IMAGES_DIR',str(tmp_path/'game_images'))
    database.init_db()
    def fetch(resource,**params):
        if params.get('search')=='offline': raise GameDiscoveryError()
        if resource.startswith('games/'):
            return {'id':int(resource.split('/')[1]),'name':'Offline favorite','description_raw':'Saved details'}
        return {'results':[{'id':123,'name':'Offline favorite'}],'next':False}
    monkeypatch.setattr(module.discovery,'get',fetch)
    client=module.app.test_client()
    client.get('/')
    with client.session_transaction() as s: csrf=s['csrf']
    def post(path,**values): return client.post(path,data={'csrf':csrf,**values})
    return module,database,client,post


def test_settings_no_token_and_csrf_host_protection(library):
    module,db,client,post=library
    assert b'Ready to explore' in client.get('/settings').data
    assert b'name="api_key"' not in client.get('/settings').data
    assert client.get('/setup').status_code==302
    assert post('/setup',api_key='should-not-save').status_code==405
    assert client.post('/library/add/123').status_code==400
    assert client.get('/',headers={'Host':'evil.example'}).status_code==400
    assert client.get('/game/0').status_code==404
    assert client.get('/game/999999999999999').status_code==404


def test_add_duplicate_journal_undo_and_offline(library,monkeypatch):
    module,db,client,post=library
    assert post('/library/add/123').status_code==302
    assert post('/library/add/123').status_code==302
    assert len(db.get_my_games())==1
    post('/edit/123',status='Played',my_rating='9',note='Private <script>note</script>',favorite='on',played_date='2026-10-05')
    before=dict(db.get_my_game_by_id(123))
    token=db.delete_with_undo(123)
    assert db.undo_delete(token)
    assert dict(db.get_my_game_by_id(123))==before
    assert not db.undo_delete(token)
    monkeypatch.setattr(module.discovery,'get',lambda *a,**kw: (_ for _ in ()).throw(GameDiscoveryError()))
    assert b'Saved details' in client.get('/game/123').data
    assert b'Private &lt;script&gt;note&lt;/script&gt;' in client.get('/edit/123').data
    assert client.get('/').status_code==200


@pytest.mark.parametrize('rating',['bad','nan','inf','11','-1'])
def test_invalid_rating_does_not_modify_journal(library,rating):
    module,db,client,post=library
    post('/library/add/123')
    before=dict(db.get_my_game_by_id(123))
    assert post('/edit/123',status='Played',my_rating=rating).status_code==400
    assert dict(db.get_my_game_by_id(123))==before


def test_search_error_empty_suggestions_and_companies(library,monkeypatch):
    module,db,client,post=library
    assert b'Offline favorite' in client.get('/search?q=Alien').data
    assert client.get('/search/suggestions?q=Al').json=={'results':[]}
    assert len(client.get('/search/suggestions?q=Alien').json['results'])==1
    assert client.get('/search?q=Valve&type=developers').status_code==200
    assert client.get('/search?q=Valve&type=developers&company=1').status_code==200
    assert b'Could not reach game discovery' in client.get('/search?q=offline').data
    assert client.get('/search/suggestions?q=offline').status_code==503
    monkeypatch.setattr(module.discovery,'get',lambda *a,**kw:{'results':[],'next':False})
    assert client.get('/search?q=nothing').status_code==200
