# 🎮 MyGameList

**Your games, your ratings, your notes.**

A personal game library for Windows and Android, with fast discovery, local storage, and a dark interface in English and Turkish. Track what you want to play, what you are playing, and what you have finished—without creating an account or entering an API key.

[**Download for Windows**](https://github.com/keremakcn/mygamelist/releases/latest) · [All releases](https://github.com/keremakcn/mygamelist/releases)

## Get started

1. Download the **MyGameList ZIP** from the latest release's **Assets**. Choose the app archive, not the source-code archive.
2. Extract it and open **`MyGameList.exe`**. No Python installation is needed.
3. Find a game and add it to your library. Use **Edit** to change its status, rating, notes, or favorite flag.

Discovery is ready to use through our shared catalog service. No API key is required. Your existing library remains available offline, including saved game details and covers that were downloaded successfully.

## Android beta

The first Android build is **1.0.0-android-beta.1**. Install the signed **APK** when attached to a release. The **AAB** is the Play Console upload package and cannot be installed by tapping it.

Android 7.0+ on 64-bit ARM devices is supported; x86_64 is included for compatible emulators. The phone layout includes two-column cards, touch controls, scrolling filters, and Turkish/English. Your selected language survives app restarts. Discovery uses the same key-free service as Windows.

Phone and desktop libraries are separate. Android updates preserve your library; uninstalling or clearing app storage deletes it. Android backup, import/export and cloud sync are not implemented.

**Release status:** signed packages and automated UI/application checks are available. Physical device testing is pending. Strict native RELRO checks flag third-party runtime libraries on 16 KB devices, so full 16 KB compatibility is not certified. Treat this as a beta testing package, not a verified production Play release. See [Android build notes](android/README.md), [Play submission notes](android/PLAY_STORE.md), and [QA results](QA_RESULTS.md).

## Screenshots

### Personal library
Track your games, ratings, favorites, and notes in one place.

![MyGameList personal library](screenshots/homepage.png)

![MyGameList personal library](screenshots/homepage2.png)

### Search and discovery
Find games, developers, and publishers with live search suggestions.

![MyGameList search and discovery](screenshots/search.png)

![MyGameList search and discovery](screenshots/searchfromdevelopers.png)

## What you can do

| Discover games | Manage your library |
|---|---|
| Search games, developers, or publishers | Track Want to Play, Playing, Played, and Dropped |
| See suggestions while typing | Filter your library instantly as you type |
| Browse a company's games from its name | Add games directly from search result cards |
| See Metacritic scores and open trailer searches | Give personal ratings from 0–10 and mark favorites |
| Find relevant matches ranked by popularity | Write notes with expandable previews on cards |
| Browse additional result pages | Undo deletion without losing notes or ratings |

The library shows **newest additions first** by default. You can filter by status or favorites and sort by name, Metacritic, personal rating, date added, or played date. Saving an edit returns you to the library.

### Two kinds of search

- **Discovery search** uses our shared service to query RAWG for games or companies. Games are selected by default; choose Developers or Publishers to browse those instead.
- **Library search** filters the games currently shown in your library, alongside your active status/favorites filter. It does not need an internet connection or an Enter key press.

Discovery suggestions appear after **three characters** and a short typing pause, with up to **five results**. Use **↑ / ↓** to select, **Enter** to open a selection, or **Escape** to close the list. Pressing Enter without a selection opens the full results page.

Game search supports partial titles such as `god war` and `modern warfare`. Matching all query words takes priority; popularity then orders games within the same match group. It also recognizes:

- **`gta` → `Grand Theft Auto`**, regardless of capitalization, when entered as a separate word.
- **`1–10` ↔ `I–X`**, so `gta 4` and `GTA IV` use equivalent searches.

Results depend on RAWG's catalog. A missing Metacritic score means no score is available from the supplied game data.

### Notes and undo

Notes appear in gray italic text on your cards. Long notes show a two-line preview; **Read more / Show less** expands or collapses the selected card. Other cards keep their height.

After deleting a game, click **Undo** in the temporary notification to restore its status, rating, note, favorite flag, played date, and original added-order position. If you have already re-added the game, undo will not overwrite the new entry.

## Updates, storage, and backups

**To update:** close MyGameList, extract the new release, and replace the old EXE. Your saved data is separate from the executable, so moving or replacing it preserves your library.

| How you run the app | Data location |
|---|---|
| Packaged Windows EXE | `%APPDATA%\MyGameList` (`AppData\Roaming`) |
| Python source | The project directory |
| Android | Private app storage: `files/library` (`games.db`, `game_images/`, `preferences.json`) |

The library and image cache use the same file structure on all platforms:

```text
games.db       Library, notes, ratings, favorites, dates, and cached game details
game_images/   Downloaded cover images
```

**Do not delete `%APPDATA%\MyGameList` when updating.** Source and EXE runs use separate locations, so a library created in one does not automatically appear in the other.

To back up Windows/source data, close the app and copy these files and the image folder to a safe location. To restore, close the app, keep a copy of the current data, and place the backup in the appropriate data directory. Backups contain your private notes and library; keep them private.

There is currently **no automatic backup, cloud sync, or account system**.

## Your thoughts stay yours

Your notes, ratings, favorites and playing history stay on your computer or phone. Searches and game-detail requests go through our shared discovery service to RAWG; your personal journal is not uploaded. Local storage is not encrypted.

## Run from source

Python 3.12 recommended. In Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe run_desktop.py
```

For browser development, run `app.py` and open `http://127.0.0.1:5000`. The desktop window uses an available local port automatically, so it can run alongside MyMovieList and MySeriesList.

To build the Windows executable:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm MyGameList.spec
```

The result is `dist/MyGameList.exe`. Only application assets are bundled; your database, covers and credentials are excluded.

## Troubleshooting

- **Discovery is unavailable:** check your connection and try again shortly. The shared service may be temporarily busy. Your saved library remains available.
- **The library looks empty after switching between source and EXE:** check the two storage locations above. Switching launch methods does not migrate your library.
- **Changes do not appear in the EXE:** rebuild it from the updated source.

For verification details, see [QA results](QA_RESULTS.md). Android build and installation details are in [android/README.md](android/README.md).

## License and credits

Personal project; no license has been specified.

Game data and artwork are provided by the [RAWG Video Games Database API](https://rawg.io/apidocs).
