"""Serve the shared journal on-device, protected by a native bootstrap token."""
import json
import os
from pathlib import Path
import secrets
import sys
import threading

_lock = threading.Lock()
_server = None
_connection = None

def create_android_app(data_directory, token, initial_language="en"):
    # The shared desktop app initializes SQLite on import. Select private storage first.
    if any(name in sys.modules for name in ("app", "paths", "database")):
        raise RuntimeError("Initialize Android storage before importing the shared application.")
    folder = Path(data_directory).resolve() / "library"
    folder.mkdir(parents=True, exist_ok=True)
    os.environ["MYGAMELIST_DATA_DIR"] = str(folder)
    os.environ["MYGAMELIST_PLATFORM"] = "android"
    from flask import abort, redirect, request, session
    from app import app
    import database
    if Path(database.DB_NAME).resolve() != folder / "games.db":
        raise RuntimeError("Library storage was not initialized in the private app directory.")

    language_file = folder / "preferences.json"
    language = initial_language if initial_language in ("tr", "en") else "en"
    try:
        saved = json.loads(language_file.read_text(encoding="utf-8"))
        if saved.get("language") in ("tr", "en"):
            language = saved["language"]
    except (OSError, ValueError, AttributeError):
        pass
    preference_lock = threading.Lock()

    @app.after_request
    def save_android_language(response):
        nonlocal language
        if request.endpoint == "set_language" and response.status_code == 302:
            with preference_lock:
                language = session.get("lang", language)
                temporary = language_file.with_suffix(".tmp")
                try:
                    temporary.write_text(json.dumps({"language": language}), encoding="utf-8")
                    temporary.replace(language_file)
                except OSError:
                    app.logger.warning("Could not persist the Android language preference.")
                finally:
                    temporary.unlink(missing_ok=True)
        return response

    @app.before_request
    def require_native_session():
        if request.endpoint == "native_bootstrap":
            return None
        if not secrets.compare_digest(request.cookies.get("native_access", "").encode("utf-8"), token.encode("ascii")):
            abort(403)
        session.setdefault("lang", language)

    @app.get("/_native/start")
    def native_bootstrap():
        if not secrets.compare_digest(request.headers.get("X-Native-Token", "").encode("utf-8"), token.encode("ascii")):
            abort(403)
        response = redirect("/")
        response.set_cookie("native_access", token, httponly=True, samesite="Strict")
        return response
    return app

def start(data_directory, initial_language="en"):
    global _server, _connection
    from waitress import create_server
    with _lock:
        if _server is None:
            token = secrets.token_urlsafe(32)
            app = create_android_app(data_directory, token, initial_language)
            _server = create_server(app, host="127.0.0.1", port=0, threads=4)
            threading.Thread(target=_server.run, daemon=True, name="library-http").start()
            _connection = {"url": f"http://127.0.0.1:{_server.effective_port}", "token": token}
        return json.dumps(_connection)
