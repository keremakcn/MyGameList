# MyGameList Android Beta

The Android shell runs the shared Flask application and SQLite library entirely on the phone, using Chaquopy and Android WebView. Discovery requests go through `https://api.myshelf.cloud`; the app contains no RAWG token.

## Install

Install `MyGameList-1.0.0-android-beta.1.apk` when it is attached to a GitHub release. Android 7.0+ is required; supported ABIs are arm64-v8a and x86_64. There is no desktop-to-phone sync. The AAB is for Google Play submission, not direct installation.

## Build

Use Java 17, Android SDK platform 36, Python 3.13 and the included Gradle wrapper. Set `JAVA_HOME` and `ANDROID_HOME` to your installations. From the repository root on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\scripts\create_android_signing.ps1 -Keytool (Join-Path $env:JAVA_HOME 'bin/keytool.exe')
.\scripts\build_android.ps1 -Release
```

Release output goes to `dist/android/1.0.0-android-beta.1/`, with APK, AAB and SHA-256 checksums. Increase Android `versionCode` for each published update. Keep the original application ID and signing key when issuing updates.

**Back up `.android-signing/release.jks` and `android/keystore.properties` together in a secure location.** They are private, ignored by Git, and must never be included in releases. Losing the signing key prevents updates to existing installations. The manual GitHub Actions workflow also supports debug builds and signed release builds after configuring its four Android signing secrets.

## Storage and security

- Saved language: `getFilesDir()/library/preferences.json`; the initial language follows the device (Turkish or English).
- Private library: `getFilesDir()/library/games.db`. Windows continues to use `%APPDATA%/MyGameList/games.db`.
- Updates preserve data; uninstalling or clearing app storage deletes it. Automatic Android backup/device transfer is disabled; Android import/export is not implemented.
- The embedded server binds to `127.0.0.1` on a random port, guarded by a per-process native bootstrap token and HttpOnly cookie. CSRF checks remain enabled.
- No JavaScript-to-native bridge, file access, third-party cookies or unencrypted remote requests are enabled. External HTTPS links open in the default browser.
- Local SQLite storage is not encrypted. Discovery searches are sent to the catalog service; journal data is not.

## Play Console

The signed AAB uses application ID `com.mygamelist`, version code `1`, target SDK `36`. Read [PLAY_STORE.md](PLAY_STORE.md) before uploading. No Play Console upload or public publication has been performed.

## Validation limits

Automated shared-app, native-session, responsive UI, signing and package checks are run before release. Physical Android device testing is still required for keyboard behavior, Back navigation, lifecycle recovery and device-specific WebView behavior. Publish as Android Beta until those checks are completed.

All native PT_LOAD segments are at least 16 KB aligned; APK ZIP alignment and AAB PAGE_ALIGNMENT_16K pass. The stricter RELRO-end check flags third-party Chaquopy/Python libraries. This is unresolved; alignment alone does not prove runtime compatibility. Test on real 4 KB and 16 KB devices and resolve the native-runtime findings before treating this as a production release. The first build remains Beta.
