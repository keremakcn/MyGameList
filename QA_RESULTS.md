# MyGameList Windows shared-discovery update — 2026-10-05

- 14 isolated Python tests passed: cache coalescing and mutation isolation, bounded cache, rate-limit cooldown, credential-free headers, invalid gateway/resource rejection, network/HTTP/JSON errors, key-free Settings, CSRF/host protection, controlled invalid game IDs, duplicate additions, journal validation, offline fallback and Undo metadata/order preservation.
- 30 desktop layout/page checks passed at 800, 1100 and 1550px. Library, Settings, search initial/results/error/empty, developers, publishers, details and edit views showed no horizontal overflow or JavaScript errors.
- Browser flows passed: bilingual key-free Settings, quick-add without closing results, duplicate disabled state, note/rating/favorite save, developer-to-games navigation and keyboard autocomplete. Desktop Settings screenshot inspected. Favorite control now supports keyboard focus while preserving the existing appearance.
- Cloudflare regression tests passed for both providers: allowlists, query/key injection rejection, cache isolation, limits, secret-free pagination, malformed responses and upstream failures. Existing movie/TV routes remain unchanged.
- Live gateway health, Portal game search, Alien movie search and Dark TV search passed after deployment. RAWG key is stored as a Cloudflare Secret; no provider credential is sent by MyGameList.
- Windows EXE built with PyInstaller. Packaged startup, key-free Settings, live game search and addition, local cover download, journal save and Undo preservation passed using a temporary data folder. Only test-owned processes were closed.
- Installed data location remains %APPDATA%/MyGameList; source data remains in the project folder. MYGAMELIST_DATA_DIR provides an explicit override for isolated QA. No personal database was opened for these tests. Obsolete local RAWG credential fields were removed after live service verification.
- Final EXE archive excludes personal database, config.json, .env and game_images. Release ZIP contains only the EXE and installation note; ZIP integrity and SHA-256 were verified.

## Run checks

Install requirements-dev.txt and run `python -m pytest -q`. Tests select an isolated data folder before importing the app.

For browser checks, run `python tests/preview.py`, set PLAYWRIGHT_MODULE and EDGE_PATH for your Playwright/Chromium installation, then run `node tests/browser.cjs`. Preview uses a temporary example library on port 5064.

The shared Worker source is maintained in the MyMovieList repository under cloudflare/watchlist-api. Run `node --test worker.test.js games.test.js` there.

## Limits

RAWG free-plan usage is shared across users. Cache and per-location rate limits reduce traffic but are not a strict global monthly quota cap. This Windows EXE is unsigned. Android validation is recorded below.


## MyGameList Android 1.0.0-beta.1 — 2026-10-05

- 17 Python tests passed, including fresh-process Android private-path selection, native-only bootstrap authentication, HttpOnly cookie, CSRF/host rejection, concurrent startup using one loopback server, journal/cover persistence, original order after Undo, and language persistence across process restart. Tests use temporary libraries; personal Windows/source data is excluded.
- 132 Turkish/English mobile/tablet page checks passed at 320, 360, 390, 412, 640 and 844px. Search, company navigation, loading/error/empty results, game details, long titles, edit, Settings and library have no document horizontal overflow or JavaScript exceptions.
- Touch flows passed for direct add, disabled duplicate action, suggestions selection, developer-to-game navigation, notes/rating/favorite/played-date save, delete/Undo and restored ordering. Phone library and edit screenshots were visually inspected. Local cached cover rendering on the edit page was corrected.
- 30 desktop page/layout checks and desktop interaction checks passed after shared mobile changes. The Windows EXE was not rebuilt during this Android task.
- Release APK and AAB built with Java 17, Android Gradle Plugin 8.13.2, Chaquopy 17.0.0 and embedded Python 3.13.9. Android target 36, minimum 24, arm64-v8a and x86_64; app ID com.mygamelist; versionCode 1. Native startup/recovery strings are Turkish/English; first-run language follows the device.
- APK v2 signature verified with the MyGameList RSA-4096 certificate; signed AAB verified with jarsigner. Bundletool 1.18.1 accepts the AAB structure. ZIP 16 KB alignment and AAB PAGE_ALIGNMENT_16K pass.
- **Unresolved 16 KB finding:** strict inspection of PT_GNU_RELRO end alignment flags multiple prebuilt Chaquopy/Python native libraries. All PT_LOAD segments are at least 16 KB aligned, but this does not prove runtime compatibility. Full 16 KB device support is not certified. Do not promote this build to a production Play release until the native-runtime findings and on-device behavior are verified/resolved. Packages are Beta testing artifacts.
- Package-source allowlist excludes .env, config.json, private databases, downloaded personal covers, desktop executables, tests and signing keys. The APK/AAB ZIP integrity is verified recursively, including Chaquopy asset archives. Private signing files are Git-ignored and retained locally for future updates.
- No physical Android/emulator installation was performed. Back gestures, keyboard/IME, lifecycle recovery, actual HTTPS transport in the Android runtime and update-without-data-loss need on-device testing. No Play Console or GitHub upload was performed.

For mobile browser checks, start `python tests/preview.py` with `MYGAMELIST_PLATFORM=android`, then run `node tests/mobile.cjs` with the same Playwright environment variables used for desktop checks. These checks emulate phone screens; they do not replace native device testing.


## Purple G branding update — 2026-10-05

- The approved purple G/controller artwork is used in the README, navbar, favicon, Windows EXE resources, native window icon and Android launcher. Artwork was resized/converted without redesigning it. The ICO contains 16, 20, 24, 32, 40, 48, 64, 128 and 256px sizes. Small Windows icons and representative circular/rounded Android mask previews were visually inspected.
- 17 isolated Python tests passed. 132 bilingual mobile/tablet page checks and 30 desktop page checks plus their interaction flows passed after branding changes. Desktop and phone Settings screenshots were visually inspected; no horizontal overflow or JavaScript exceptions were detected.
- Windows EXE rebuilt and launched with a separate temporary library. Library and Settings returned the new navbar/logo; packaged favicon bytes matched the approved ICO. All nine icon payloads in the executable's PE resources matched the source ICO. Only the test-owned application processes were stopped. Personal libraries were not opened or modified.
- Signed APK/AAB rebuilt as 1.0.0-android-beta.2, versionCode 2. Application ID and original signing certificate remain unchanged. APK v2 signing, AAB signing/structure, ZIP alignment, AAB page-alignment configuration and update metadata checks passed. Android Lint completed with zero errors and two launcher-icon warnings.
- Recursive package checks confirmed the approved Android launcher and shared branding files are included. Personal databases, covers, configuration, provider credentials and signing keys are excluded. Windows ZIP contains only the EXE and INSTALL.txt; ZIP integrity, EXE equality and release SHA-256 checksums passed.
- Known Android limit remains: 98, 98 third-party native libraries flagged by the strict RELRO-end inspection in APK/AAB respectively; all PT_LOAD checks passed. No physical-device installation or update test was performed, and full 16 KB compatibility is not certified. Android remains Beta. No GitHub or Play upload was performed.
