"""Bind a free loopback port before opening the Windows application."""
import threading
import webview
from waitress import create_server
from app import app
from paths import ASSET_DIR

if __name__ == '__main__':
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True
    webview.settings['ALLOW_FILE_URLS'] = False
    server = create_server(app, host='127.0.0.1', port=0, threads=4)
    threading.Thread(target=server.run,daemon=True).start()
    try:
        webview.create_window('MyGameList',f'http://127.0.0.1:{server.effective_port}',
                              width=1100,height=750,min_size=(700,500),background_color='#101014')
        webview.start(icon=str(ASSET_DIR / 'static' / 'branding' / 'mygamelist.ico'))
    finally:
        server.close()
