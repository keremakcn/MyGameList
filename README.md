# 🎮 MyGameList

A personal video game tracking app. Think of it as the game version of [MyAnimeList](https://myanimelist.net/): search for games, add them to your library, track your status, rate them yourself, write notes, and mark favorites.

Powered by the [RAWG Video Games Database API](https://rawg.io/apidocs) for game data (Metacritic score, cover art, platforms, genres, developer, publisher). Your personal relationship with a game (status, rating, notes, favorites) is kept completely separate from that data.

Currently built as a single-user app, but the database is designed so it can evolve into a multi-user system (with accounts) later without a rewrite.

---

## ✨ Features

- 🔍 **Game search** — search via the RAWG API, results shown as cards, already-owned games are marked
- 📚 **Personal library** — status tracking (Want to Play / Playing / Played / Dropped)
- ⚡ **Quick actions** — mark a game as Played with one click, right from the library card, no form required
- ⭐ **Your own rating** — a 0–10 scale, fully independent from Metacritic
- 📝 **Notes** — write your own thoughts on each game
- ❤️ **Favorites** — mark your all-time favorites
- 📅 **Played date** — record when you finished a game
- 🎬 **Trailer shortcut** — jump straight to a YouTube search for any game's trailer
- 🔀 **Filtering & sorting** — filter by status/favorites, sort by name, Metacritic, your rating, or date added
- 📡 **Offline-friendly** — cover art and details for games already in your library are cached locally, so your library stays usable without an internet connection
- 🌐 **Bilingual** — Turkish / English, switch instantly
- 🎨 **Custom design** — dark theme, cartridge/HUD-inspired look
- 🖥️ **Desktop app** — packaged as a standalone Windows app with its own window and icon, no browser required
- ⚙️ **No hard lock-in** — the app works even without an API key set; search and adding new games are simply disabled until you add one from Settings
- 🛡️ **Resilient error handling** — the app won't crash if the RAWG API fails, returns incomplete data, or the connection drops

---

## 📥 Download (No Setup Required)

If you just want to use the app without touching code:

1. Download the latest `MyGameList.zip` from the [**Releases**](https://github.com/keremakcn/mygamelist/releases) page.
2. Extract it — right-click the zip → **Extract All** — to any folder you like (this folder will hold your library, so keep it somewhere permanent, like Documents).
3. Double-click `MyGameList.exe` inside the extracted folder.
4. On first launch, you'll see a short setup screen asking for a free RAWG API key. Get one at [rawg.io/apidocs](https://rawg.io/apidocs) (sign up, copy your key, paste it in). You'll only need to do this once.
5. That's it — the app opens in its own window from then on.

> 💡 Your data (API key, library, and cached cover art) is stored in `%APPDATA%\MyGameList`, completely independent of where the exe itself lives. You can move, rename, or even delete and redownload the exe — your library stays untouched. If you ever want to fully reset the app, just delete that folder.

Don't have a RAWG API key yet? No problem — the app still opens normally. You'll see a banner at the top prompting you to add one whenever you're ready, via the ⚙ **Settings** link in the navigation bar.
---

## 🛠️ Running from Source (Developers)

### Requirements
- Python 3.10+
- A free [RAWG API key](https://rawg.io/apidocs)

### Steps

1. Clone the repo:
   ```bash
   git clone https://github.com/keremakcn/mygamelist.git
   cd mygamelist
   ```

2. Create and activate a virtual environment *(recommended, not required)*:
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS / Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and add your API key:
   ```
   RAWG_API_KEY=your_key_here
   ```

5. Create the database:
   ```bash
   python database.py
   ```

6. Run the app:
   ```bash
   python app.py
   ```

7. Open in your browser: **http://127.0.0.1:5000**

### Building the desktop app yourself

```bash
pip install pywebview pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name MyGameList --icon icon.ico --add-data "templates;templates" --add-data "static;static" run_desktop.py
```

The packaged app will be at `dist/MyGameList.exe`.

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite |
| Frontend | HTML, CSS, Jinja2 |
| Desktop shell | PyWebView |
| Packaging | PyInstaller |
| External API | [RAWG Video Games Database](https://rawg.io/apidocs) |

---

## 📁 Project Structure

```
mygamelist/
├── app.py                # Flask routes, RAWG API logic, setup flow
├── database.py            # SQLite connection and queries
├── translations.py        # TR/EN translation strings
├── run_desktop.py          # Entry point for the packaged desktop app
├── icon.ico                # App icon (exe + window)
├── requirements.txt         # Python dependencies
├── .env.example               # Example environment file
├── .env                          # RAWG API key (not committed)
├── games.db                       # SQLite database (not committed)
├── config.json                     # Saved API key from the setup screen (not committed)
├── game_images/                     # Locally cached cover art (not committed)
├── templates/                        # Jinja2 HTML templates
│   ├── layout.html
│   ├── index.html
│   ├── search.html
│   ├── game.html
│   ├── edit.html
│   ├── setup.html
│   └── 404.html
└── static/
    └── style.css
```

---

## 🗄️ Database Design

RAWG's **objective data** and your **personal data** are deliberately split into two tables:

### `games`
Game data pulled from RAWG — name, Metacritic score, platforms, genres, developer, publisher, description, and a locally cached cover image path (used when offline).

### `my_games`
Your relationship with that game — status, your rating, your note, favorite flag, played date.

```
games                    my_games
------                    ---------
id (RAWG id)  ◄──────────  game_id
name                       status
metacritic                 my_rating
platforms                  note
local_image_path            favorite
...                          played_date
```

**Why this matters:** if a login system is added later, only the `my_games` table needs a `user_id` column. The `games` table can stay shared across all users, so the same game is never fetched from RAWG twice.

---

## 🔑 How the API key setup works

The app looks for your RAWG API key in this order:

1. A `.env` file next to the app (used mainly for local development)
2. `config.json`, saved automatically the first time you complete the in-app setup screen

If neither exists, the app redirects every page to the setup screen until a valid key is entered and tested against the RAWG API. This means anyone downloading the packaged `.exe` gets their own key and their own request quota — no key is ever bundled into the app itself.

---

## 🗺️ Roadmap

- [x] RAWG API integration and search
- [x] SQLite database, library management
- [x] Filtering and sorting
- [x] TR/EN language support
- [x] Custom design, dark theme
- [x] Offline caching for library games
- [x] In-app API key setup flow
- [x] Desktop `.exe` packaging with custom icon
- [ ] User accounts (signup/login), multi-user support
- [ ] Web deployment (a version anyone can use with their own account)

---

## 📄 License

Personal project, no license specified.

---

## 🙏 Acknowledgments

Game data provided by the [RAWG Video Games Database API](https://rawg.io/apidocs).
