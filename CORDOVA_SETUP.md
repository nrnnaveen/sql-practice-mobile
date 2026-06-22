# Cordova APK Setup Guide

This guide explains how to build the SQL Practice mobile APK and configure Google OAuth so the **"Sign in with Google"** button works correctly inside the Cordova WebView.

---

## Why the WebView Needs Special Handling

Google blocks OAuth sign-in requests that originate from embedded WebViews (error **403: disallowed_useragent**). The app works around this by detecting the Cordova environment and opening the system browser (Chrome) instead:

```js
function googleLogin() {
    if (window.cordova) {
        // Opens system Chrome – Google allows OAuth here
        window.open("/login/google", "_system");
    } else {
        // Normal browser navigation
        window.location.href = "/login/google";
    }
}
```

The `cordova-plugin-inappbrowser` plugin (declared in `config.xml`) is required for `window.open(..., "_system")` to work.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Node.js | ≥ 16 | https://nodejs.org |
| Cordova CLI | ≥ 12 | `npm install -g cordova` |
| Android Studio | Latest | https://developer.android.com/studio |
| Java JDK | 11 or 17 | https://adoptium.net |
| Gradle | bundled with Android Studio | – |

---

## Step-by-Step Build Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/nrnnaveen/sql-practice-mobile.git
cd sql-practice-mobile
```

### 2. Install Cordova Dependencies

```bash
npm install
```

### 3. Add the Android Platform

```bash
cordova platform add android
```

### 4. Install Declared Plugins

Cordova reads `config.xml` and installs all `<plugin>` entries automatically when you add a platform. To install manually:

```bash
cordova plugin add cordova-plugin-inappbrowser
cordova plugin add cordova-plugin-whitelist
cordova plugin add cordova-plugin-statusbar
cordova plugin add cordova-plugin-splashscreen
cordova plugin add cordova-plugin-device
```

Verify with:

```bash
cordova plugin list
```

### 5. Set Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Key variables for the APK:

| Variable | Description |
|----------|-------------|
| `CORDOVA_BUILD_URL` | URL the WebView loads (your Render/Railway URL) |
| `CORDOVA_OAUTH_REDIRECT_URI` | Registered redirect URI in Google Cloud Console |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret |

### 6. Update `www/index.html`

The `www/index.html` entry point should load your backend URL:

```html
<script>
    window.location.href = "https://your-app.onrender.com";
</script>
```

Or configure Cordova to use a remote URL via the `<content src="...">` tag in `config.xml`.

### 7. Build the APK

**Debug build** (for testing):

```bash
cordova build android
```

The APK will be at:
```
platforms/android/app/build/outputs/apk/debug/app-debug.apk
```

**Release build** (for production/Play Store):

```bash
cordova build android --release
```

### 8. Install on a Device

```bash
# Via ADB (USB debugging enabled)
adb install platforms/android/app/build/outputs/apk/debug/app-debug.apk

# Or copy the APK file to your device and install manually
```

---

## Google Cloud Console Configuration

For OAuth to work from the APK you need to register the correct **Authorized redirect URIs** in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials):

1. Open your OAuth 2.0 Client ID.
2. Under **Authorised redirect URIs**, add:
   - `https://your-app.onrender.com/login/google/callback`
   - `http://localhost:5000/login/google/callback` (for local testing)
3. Under **Authorised JavaScript origins**, add:
   - `https://your-app.onrender.com`

> **Note:** The APK itself does **not** need a custom URI scheme. The system browser handles the OAuth flow and redirects back to your web server, which then sets the session cookie. The WebView reloads and picks up the authenticated session.

---

## OAuth Flow in the APK

```
User taps "Sign in with Google"
        │
        ▼
googleLogin() detects window.cordova
        │
        ▼
window.open("/login/google", "_system")
        │
        ▼
System Chrome opens Google sign-in page
        │
        ▼
User authenticates
        │
        ▼
Google redirects to /login/google/callback (on your server)
        │
        ▼
Server sets session cookie, redirects to /dashboard
        │
        ▼
Chrome closes (or user switches back to app)
        │
        ▼
WebView reloads / user is now logged in
```

---

## Troubleshooting

### Error 403: disallowed_useragent

The OAuth request is still going through the WebView instead of the system browser.

**Check:**
- `cordova-plugin-inappbrowser` is installed (`cordova plugin list`)
- `config.xml` declares the plugin
- The `googleLogin()` function in `app/templates/login.html` uses `window.open(..., "_system")`

### Blank screen on launch

The `www/index.html` entry point may not be redirecting to your server URL.

**Check:**
- `CORDOVA_BUILD_URL` is set in your environment
- The `<content src="...">` in `config.xml` points to the correct URL
- `cordova-plugin-whitelist` is installed and `<access origin="*" />` is in `config.xml`

### Google login redirects to localhost

The `GOOGLE_OAUTH_REDIRECT_URI` environment variable is not set on your server.

**Fix:** Set `GOOGLE_OAUTH_REDIRECT_URI=https://your-app.onrender.com/login/google/callback` on your Render/Railway deployment.

### Build fails with Gradle error

Ensure Android Studio and Java JDK are properly installed:

```bash
cordova requirements android
```

---

## iOS Build

```bash
cordova platform add ios
cordova build ios
```

Open the Xcode project and sign with your Apple Developer account:

```
platforms/ios/SQL Practice.xcworkspace
```

---

## Environment Variable Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Flask session secret key |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth client secret |
| `GOOGLE_OAUTH_REDIRECT_URI` | ✅ | Registered redirect URI |
| `APP_URL` | ✅ | Your app's public URL |
| `CORDOVA_BUILD_URL` | APK only | URL loaded by the WebView |
| `CORDOVA_OAUTH_REDIRECT_URI` | APK only | OAuth redirect URI for APK |
| `CORDOVA_DEBUG_MODE` | optional | Enable debug logging in APK |
