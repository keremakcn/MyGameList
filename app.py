import os
import re
import unicodedata
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
import secrets
import math
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import urlsplit
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify, flash, abort
from database import delete_with_undo, undo_delete
from paths import ASSET_DIR, DATA_DIR
from game_client import GameClient, GameDiscoveryError
from database import get_connection, get_my_games, get_my_games_stats, delete_from_my_list, get_my_game_by_id, update_my_game, get_owned_game_ids, update_status_only, init_db, get_local_game_data
from translations import t

TEMPLATE_DIR = str(ASSET_DIR / 'templates')
STATIC_DIR = str(ASSET_DIR / 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = secrets.token_hex(32)
app.config.update(ANDROID_APP=os.environ.get('MYGAMELIST_PLATFORM') == 'android',
                  SESSION_COOKIE_NAME='mygamelist_android' if os.environ.get('MYGAMELIST_PLATFORM') == 'android' else 'mygamelist', SESSION_COOKIE_HTTPONLY=True,
                  SESSION_COOKIE_SAMESITE='Strict', MAX_CONTENT_LENGTH=65536,
                  TRUSTED_HOSTS=['127.0.0.1','localhost','[::1]'])
discovery = GameClient()


@app.before_request
def protect_local_library():
    session.setdefault('csrf',secrets.token_hex(32))
    if request.method == 'POST' and not secrets.compare_digest(
            request.form.get('csrf','').encode(), session['csrf'].encode()):
        abort(400, 'Your session changed. Reload the page and try again.')


@app.after_request
def private_response(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response
init_db()
GAME_IMAGES_DIR = os.path.join(DATA_DIR, "game_images")
os.makedirs(GAME_IMAGES_DIR, exist_ok=True)


@app.route("/game_images/<path:filename>")
def game_image(filename):
    """Yerelde önbelleklenen oyun resimlerini sunar (exe içine gömülü değil, exe'nin yanındaki klasörden)."""
    return send_from_directory(GAME_IMAGES_DIR, filename)


def download_game_image(game_id, image_url):
    """Oyunun görselini indirip yerel klasöre kaydeder, dosya adını döner.
    İnternet yoksa ya da indirme başarısız olursa None döner (uygulama çökmez)."""
    if not image_url:
        return None
    parts = urlsplit(image_url)
    if parts.scheme != 'https' or parts.hostname != 'media.rawg.io' or parts.username or parts.password:
        return None
    try:
        with urlopen(Request(image_url,headers={'User-Agent':'MyGameList/Android' if app.config['ANDROID_APP'] else 'MyGameList/Windows'}),timeout=8) as response:
            if urlsplit(response.url).hostname != 'media.rawg.io':
                return None
            content_type = response.headers.get_content_type()
            extension = {'image/jpeg':'jpg','image/png':'png','image/webp':'webp'}.get(content_type)
            if not extension:
                return None
            data = response.read(8*1024*1024+1)
        if not data or len(data) > 8*1024*1024:
            return None
        filename = f'{game_id}.{extension}'
        path = Path(GAME_IMAGES_DIR) / filename
        temporary = path.with_name(path.name + '.' + secrets.token_hex(6) + '.tmp')
        try:
            temporary.write_bytes(data)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return filename
    except (URLError,OSError,ValueError):
        return None


def get_game_details_with_fallback(game_id):
    """Önce RAWG'dan canlı veri çekmeyi dener. Başarısız olursa (internet yok)
    ve oyun daha önce kütüphaneye eklenmişse, yerel veriden bir yedek oluşturur.
    (canlı_veri_dict, is_offline) tuple'ı döner. Hiçbiri yoksa (None, False) döner."""
    game = get_game_details(game_id)
    if game is not None:
        return game, False

    local = get_local_game_data(game_id)
    if local is None:
        return None, False

    fallback = {
        "id": local["id"],
        "name": local["name"],
        "released": local["release_date"],
        "metacritic": local["metacritic"],
        "background_image": None,
        "local_image_path": local["local_image_path"],
        "platforms": [{"platform": {"name": p.strip()}} for p in (local["platforms"] or "").split(",") if p.strip()],
        "genres": [{"name": g.strip()} for g in (local["genre"] or "").split(",") if g.strip()],
        "developers": [{"name": d.strip()} for d in (local["developer"] or "").split(",") if d.strip()],
        "publishers": [{"name": p.strip()} for p in (local["publisher"] or "").split(",") if p.strip()],
        "description_raw": local["description"],
    }
    return fallback, True


@app.context_processor
def inject_translation():
    return dict(t=t, current_lang=session.get('lang','en'))


def clean_description(text):
    """RAWG bazı oyunlarda açıklamayı birden fazla dilde birleşik veriyor.
    İngilizce olmayan kısmı, dil isimlerinden önce keserek temizler."""
    if not text:
        return text

    language_markers = [
        "Español", "Русский", "Français", "Deutsch", "Português",
        "Polski", "Italiano", "Türkçe", "Nederlands", "Čeština",
        "日本語", "한국어", "中文", "Svenska", "Dansk", "Norsk"
    ]

    cut_at = len(text)
    for marker in language_markers:
        idx = text.find(marker)
        if idx != -1:
            cut_at = min(cut_at, idx)

    return text[:cut_at].strip()


def get_game_details(game_id):
    """RAWG API'den tek bir oyunun detaylı bilgisini çeker.
    Hata olursa veya oyun bulunamazsa None döner."""
    if not 1 <= game_id <= 9999999999:
        return None
    try:
        data = discovery.get(f'games/{game_id}')
    except GameDiscoveryError:
        return None

    if data.get("description_raw"):
        data["description_raw"] = clean_description(data["description_raw"])

    return data


def save_game_to_db(game, local_image_filename=None):
    """RAWG'dan gelen oyun verisini games tablosuna kaydeder/günceller.
    local_image_filename verilmişse ve daha önce kaydedilmemişse resim yolunu da kaydeder."""
    conn = get_connection()
    cursor = conn.cursor()

    genres = ", ".join(g["name"] for g in game.get("genres", []))
    platforms = ", ".join(p["platform"]["name"] for p in game.get("platforms", []))
    developer = ", ".join(d["name"] for d in game.get("developers", []))
    publisher = ", ".join(p["name"] for p in game.get("publishers", []))
    description = game.get("description_raw") or ""

    cursor.execute("""
        INSERT OR IGNORE INTO games (id, name, release_date, metacritic, genre, platforms, developer, publisher, description, cover_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        game["id"], game["name"], game.get("released"), game.get("metacritic"),
        genres, platforms, developer, publisher, description, game.get("background_image")
    ))

    cursor.execute("""
        UPDATE games SET name=?, release_date=?, metacritic=?, genre=?, platforms=?,
                          developer=?, publisher=?, description=?, cover_url=?
        WHERE id=?
    """, (
        game["name"], game.get("released"), game.get("metacritic"), genres, platforms,
        developer, publisher, description, game.get("background_image"), game["id"]
    ))

    if local_image_filename:
        cursor.execute("""
            UPDATE games SET local_image_path=?
            WHERE id=? AND (local_image_path IS NULL OR local_image_path='')
        """, (local_image_filename, game["id"]))

    conn.commit()
    conn.close()





def add_to_my_list(game_id):
    """Oyunu my_games tablosuna ekler, zaten varsa hiçbir şey yapmaz."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO my_games (game_id, status)
        VALUES (?, 'Want to Play')
    """, (game_id,))

    conn.commit()
    conn.close()


def is_in_my_list(game_id):
    """Oyun zaten listede mi kontrol eder."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM my_games WHERE game_id = ?", (game_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None




@app.get('/setup')
def setup():
    return redirect(url_for('settings'))


@app.get('/settings')
def settings():
    return render_template('settings.html')


@app.route("/set-language/<lang>")
def set_language(lang):
    """Kullanıcının dil tercihini session'a kaydeder, geldiği sayfaya geri döner."""
    if lang in ("tr", "en"):
        session["lang"] = lang
    referrer = request.referrer
    parts = urlsplit(referrer or '')
    if parts.netloc != request.host or parts.scheme not in ('http','https'):
        referrer = url_for('index')
    return redirect(referrer)


@app.route("/", methods=["GET", "POST"])
def index():
    """Ana sayfa: dashboard olarak çalışır, stats + filtrelenmiş/sıralanmış oyun listesini gösterir."""
    if request.method == "POST":
        game_id_to_delete = request.form.get("delete_game_id", type=int)
        if game_id_to_delete:
            token = delete_with_undo(game_id_to_delete)
            if token:
                flash({"token": token}, "undo")
        return redirect(url_for("index", filter=request.args.get("filter", "all"), sort=request.args.get("sort", "recent")))

    filter_by = request.args.get("filter", "all")
    sort_by = request.args.get("sort", "recent")

    games = get_my_games(filter_by=filter_by, sort_by=sort_by)
    stats = get_my_games_stats()

    return render_template(
        "index.html",
        games=games,
        stats=stats,
        current_filter=filter_by,
        current_sort=sort_by
    )


@app.route("/library/undo", methods=["POST"])
def restore_library_game():
    restored = undo_delete(request.form.get("token", ""))
    flash(t("undo_success") if restored else t("undo_unavailable"), "notice")
    return redirect(url_for("index", filter=request.form.get("filter", "all"), sort=request.form.get("sort", "recent")))


@app.route("/library/add/<int:game_id>", methods=["POST"])
def quick_add_game(game_id):
    success = is_in_my_list(game_id)
    if not success:
        game, is_offline = get_game_details_with_fallback(game_id)
        if game is not None:
            if not is_offline:
                local_filename = download_game_image(game_id, game.get("background_image"))
                save_game_to_db(game, local_image_filename=local_filename)
            add_to_my_list(game_id)
            success = True
    if request.accept_mimetypes.best == "application/json":
        return jsonify(ok=success, message=t("quick_added") if success else t("quick_add_error")), 200 if success else 502
    flash(t("quick_added") if success else t("quick_add_error"), "notice")
    return redirect(url_for("search", q=request.form.get("q", ""), type=request.form.get("type", "games"),
                            company=request.form.get("company", ""), company_name=request.form.get("company_name", ""), page=request.form.get("page", 1)))


def rawg_search_page(resource, params):
    """Fetch a page without exposing the API key or upstream pagination URLs."""
    try:
        data = discovery.get(resource, **params)
        results = [item for item in data['results']
                   if isinstance(item,dict) and isinstance(item.get('id'),int) and item['id'] > 0 and item.get('name')]
        return results, bool(data.get('next')), False
    except GameDiscoveryError:
        return [], False, True


ROMAN_NUMBERS = {
    "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5",
    "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10",
}


def expand_game_alias(query):
    """Only expand a standalone GTA token; leave the text in the UI unchanged."""
    return re.sub(r"\bgta\b", "Grand Theft Auto", query, flags=re.IGNORECASE)


def game_query_variants(query):
    """Use the same pair of API searches for numeric and Roman input."""
    expanded = expand_game_alias(query)
    numeric = re.sub(r"\b[^\W_]+\b", lambda match: ROMAN_NUMBERS.get(match[0].casefold(), match[0]), expanded)
    to_roman = {number: roman.upper() for roman, number in ROMAN_NUMBERS.items()}
    roman = re.sub(r"\b[0-9]+\b", lambda match: to_roman.get(match[0], match[0]), numeric)
    return list(dict.fromkeys([numeric, roman]))


def search_words(text):
    """Ignore punctuation, case and accents when comparing game names."""
    normalized = unicodedata.normalize("NFKD", text.casefold()).replace("ı", "i")
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return [ROMAN_NUMBERS.get(word, word) for word in re.findall(r"[^\W_]+", normalized)]


def rank_game_results(results, query):
    """Match every query word first, then prefer popular games in that group."""
    words = search_words(expand_game_alias(query))
    if not words:
        return results
    phrase = " ".join(words)

    def relevance(game):
        title_words = search_words(game["name"])
        title = " ".join(title_words)
        try:
            popularity = max(0, int(game.get("added") or 0))
        except (TypeError, ValueError, OverflowError):
            popularity = 0
        # Exact words keep "Witchery" below "The Witcher", even if popular.
        if all(word in title_words for word in words):
            return 0, 0, -popularity, title != phrase
        # Prefixes still support suggestions while the final word is being typed.
        matches = sum(any(token == word if word.isdigit() else token.startswith(word)
                          for token in title_words) for word in words)
        if matches == len(words):
            return 1, 0, -popularity, title != phrase
        fuzzy_matches = sum(any(
            (token == word if word.isdigit() else token.startswith(word) or
             (len(word) >= 4 and SequenceMatcher(None, word, token).ratio() >= 0.75))
            for token in title_words
        ) for word in words)
        if fuzzy_matches == len(words):
            return 2, 0, -popularity, title != phrase
        return 3, -matches, -popularity, title != phrase

    # Stable sorting preserves RAWG relevance within equally ranked matches.
    return sorted(results, key=relevance)


def search_game_page(query, page=1):
    """Merge numeric/Roman searches, deduplicate and apply the existing ranking."""
    variants = game_query_variants(query)

    def fetch_variant(variant):
        return rawg_search_page("games", {
            "search": variant, "page": page, "page_size": 40,
            "exclude_additions": "true",
        })

    if len(variants) == 1:
        pages = [fetch_variant(variants[0])]
    else:
        # Independent requests run together, rather than adding their wait times.
        with ThreadPoolExecutor(max_workers=2) as executor:
            pages = list(executor.map(fetch_variant, variants))
    unique = {}
    for results, _, failed in pages:
        if not failed:
            for game in results:
                unique.setdefault(game["id"], game)
    has_next = any(next_page for _, next_page, failed in pages if not failed)
    failed = all(error for _, _, error in pages)
    return rank_game_results(list(unique.values()), query), has_next, failed


@app.route("/search/suggestions")
def search_suggestions():
    """Return a small suggestion list; the RAWG key stays on the server."""
    query = request.args.get("q", "").strip()[:200]
    mode = request.args.get("type", "games")
    if mode not in ("games", "developers", "publishers"):
        mode = "games"
    if len(query) < 3:
        return jsonify(results=[])
    params = {"search": query, "page_size": 5}
    if mode == "games":
        results, _, failed = search_game_page(query)
    else:
        results, _, failed = rawg_search_page(mode, params)
    if failed:
        return jsonify(results=[], error=True), 503
    suggestions = []
    for item in results[:5]:
        target = (url_for("game_detail", game_id=item["id"], q=query)
                  if mode == "games" else
                  url_for("search", type=mode, q=query, company=item["id"], company_name=item["name"]))
        image = item.get("background_image" if mode == "games" else "image_background")
        if not isinstance(image, str) or not image.startswith("https://"):
            image = None
        suggestions.append({"name": item["name"], "image": image, "url": target})
    return jsonify(results=suggestions)


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()[:200]
    mode = request.args.get("type", "games")
    if mode not in ("games", "developers", "publishers"):
        mode = "games"
    page = min(500, max(1, request.args.get("page", 1, type=int) or 1))
    company_id = request.args.get("company", type=int)
    company_name = request.args.get("company_name", "").strip()
    if mode == "games" or not company_id or company_id < 1:
        company_id = None
        company_name = ""
    results, has_next, failed = [], False, False
    if query or company_id:
        params = {"page": page, "page_size": 20}
        if company_id:
            resource = "games"
            params.update({mode: company_id, "ordering": "-added", "exclude_additions": "true"})
        elif mode == "games":
            resource = "games"
        else:
            resource = mode
            params["search"] = query
        if mode == "games" and not company_id:
            results, has_next, failed = search_game_page(query, page)
        else:
            results, has_next, failed = rawg_search_page(resource, params)
    company_results = mode != "games" and company_id is None
    owned_ids = set() if company_results else get_owned_game_ids([g["id"] for g in results])
    return render_template(
        "search.html", query=query, results=results, owned_ids=owned_ids,
        search_type=mode, company_results=company_results, company_id=company_id,
        company_name=company_name, page=page, has_next=has_next, search_failed=failed,
    )


@app.route("/game/<int:game_id>", methods=["GET", "POST"])
def game_detail(game_id):
    """Tek bir oyunun detay sayfasını gösterir. İnternet yoksa ve oyun kütüphanedeyse
    yerel önbellekten gösterir. Listeye ekleme ve düzenleme isteklerini işler."""
    game, is_offline = get_game_details_with_fallback(game_id)

    if game is None:
        return render_template("game.html", game=None), 404

    if request.method == "POST":
        if not is_offline:
            local_filename = download_game_image(game_id, game.get("background_image"))
            save_game_to_db(game, local_image_filename=local_filename)
        add_to_my_list(game_id)

    in_list = is_in_my_list(game_id)
    my_game = get_my_game_by_id(game_id) if in_list else None
    search_query = request.args.get("q") or request.args.get("company_name")

    return render_template(
        "game.html", game=game, in_list=in_list, my_game=my_game,
        search_query=search_query, is_offline=is_offline
    )


@app.route("/edit/<int:game_id>", methods=["GET", "POST"])
def edit_game(game_id):
    """Listedeki bir oyunun status, rating, not, favori ve tarihini düzenler."""
    my_game = get_my_game_by_id(game_id)

    if my_game is None:
        return render_template("edit.html", game=None), 404

    if request.method == "POST":
        status = request.form.get("status")
        note = request.form.get("note", "").strip()
        played_date = request.form.get("played_date") or None
        favorite = 1 if request.form.get("favorite") == "on" else 0

        rating_raw = request.form.get("my_rating", "").strip()
        try:
            my_rating = float(rating_raw) if rating_raw else None
        except ValueError:
            abort(400, 'Invalid rating.')
        if status not in ('Want to Play','Playing','Played','Dropped') or (
                my_rating is not None and (not math.isfinite(my_rating) or not 0 <= my_rating <= 10)):
            abort(400, 'Invalid journal values.')

        update_my_game(game_id, status, my_rating, note, favorite, played_date)

        return redirect(url_for("index"))

    return render_template("edit.html", game=my_game)

@app.route("/quick-status/<int:game_id>", methods=["POST"])
def quick_status(game_id):
    """Tek tıkla status değiştirir (ör. Want to Play → Played), formu açmadan."""
    status = request.form.get("status")
    if status in ("Want to Play", "Playing", "Played", "Dropped"):
        update_status_only(game_id, status)

    filter_by = request.form.get("filter", "all")
    sort_by = request.form.get("sort", "recent")
    return redirect(url_for("index", filter=filter_by, sort=sort_by))

@app.errorhandler(404)
def page_not_found(e):
    """Var olmayan bir URL'ye gidilirse tema ile uyumlu 404 sayfasını gösterir."""
    return render_template("404.html"), 404


if __name__ == "__main__":
    from waitress import serve
    serve(app,host='127.0.0.1',port=5000)
