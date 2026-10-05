# MyGameList — Play submission preparation

The signed `MyGameList-1.0.0-android-beta.1.aab` is a Play Console upload artifact, not an installable download. The APK is for direct installation. No store submission has been made.

| Field | Build value |
|---|---|
| Name | MyGameList |
| Application ID | `com.mygamelist` |
| Version code | 1 |
| Version name | 1.0.0-android-beta.1 |
| Target / minimum Android SDK | 36 / 24 |
| ABIs | arm64-v8a, x86_64 |
| Signing certificate SHA-256 | `301ac031541c03c40676dd4da34ed6320afe8be29780d1e35b550c26ae7193a5` |

## Release gate

Start with an internal test release. This build has passed shared application, browser layout, package-structure and signing checks. It has **not** been installed on a physical Android device. The strict 16 KB RELRO-end inspection flags prebuilt Chaquopy/Python libraries even though PT_LOAD and ZIP alignment pass. Resolve and validate those native-runtime findings before production rollout; do not claim full 16 KB compatibility based only on alignment.

Test installation, device keyboard, Back gestures, orientation, background/resume, process death, offline covers/details, language persistence, add/edit/duplicate handling, delete/Undo, and update-without-data-loss on actual devices. Include a 16 KB Android environment. See Google's [16 KB device guidance](https://developer.android.com/guide/practices/page-sizes).

## Console setup

1. Create the MyGameList application in your own Play Console account. Ensure this application ID is available and intended to remain permanent.
2. Configure Play App Signing and keep the local signing key backed up. Play signing and your GitHub APK signing can affect whether one distribution can update the other; confirm the signing arrangement before release.
3. Upload the AAB to Internal testing, review the generated APK/device checks, and complete any account-specific testing requirements.
4. Add the store description, app icon, feature graphic and genuine Android screenshots. Browser QA images are not evidence of a device installation.
5. Complete App content, content rating, ads declaration, app access, target audience, Data safety, and a publicly accessible privacy policy. There are no in-app ads, user accounts or login credentials in this build.

See Google's [review preparation](https://support.google.com/googleplay/android-developer/answer/9859455?hl=en) and [Data safety instructions](https://support.google.com/googleplay/android-developer/answer/10787469?hl=en).

## Data facts for an accurate privacy policy

- Notes, ratings, favorites, statuses, played dates, cached game details, downloaded covers and selected language remain in private phone storage. Journal data is not uploaded by this app.
- Searches, game IDs and developer/publisher requests are sent over HTTPS through `api.myshelf.cloud` to RAWG. Cloudflare and RAWG process network/request information, including information needed to deliver responses. Verify actual infrastructure logs and retention before making declarations.
- External HTTPS links open in the user's browser. Remote covers can be fetched from `media.rawg.io`.
- There is no app analytics, advertising SDK, account system, automatic cloud backup or device-to-desktop sync. Local SQLite is not encrypted by the application.
- Uninstalling or clearing app data removes the local journal. Android export/import is not implemented.

Do not automatically select “no data collected” just because notes are stored locally. Assess the actual search service and provider handling under Google's definitions. Publish an accurate policy with your developer contact details; no policy URL has been published by this build task.

## Updates

Increment versionCode on every Play upload. Keep the same application ID and appropriate signing key. Never attach `.android-signing/release.jks` or `android/keystore.properties` to a release or commit them to Git.
