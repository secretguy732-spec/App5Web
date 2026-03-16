#!/usr/bin/env python3
"""
App5Web - Android Project Generator
Dijalankan oleh GitHub Actions untuk generate project Android lengkap.
"""

import os, struct, zlib, urllib.request

APP_NAME    = os.environ.get('APP_NAME',   'MyApp')
APP_URL     = os.environ.get('APP_URL',    'https://example.com')
PKG_ID      = os.environ.get('PKG_ID',    'com.app5web.myapp')
APP_VERSION = os.environ.get('APP_VERSION','1.0.0')
VERSION_CODE= os.environ.get('VERSION_CODE','1')
COLOR_P     = '#' + os.environ.get('COLOR_PRIMARY','3b82f6')
COLOR_A     = '#' + os.environ.get('COLOR_ACCENT', '8b5cf6')
COLOR_BG    = '#' + os.environ.get('COLOR_BG',     'ffffff')
SPLASH_TEXT = os.environ.get('SPLASH_TEXT','Loading...')
SPLASH_MS   = os.environ.get('SPLASH_MS', '2000')
JS_ENABLED  = os.environ.get('ENABLE_JS',      'true') == 'true'
ZOOM_ENABLED= os.environ.get('ENABLE_ZOOM',    'true') == 'true'
OFFLINE     = os.environ.get('ENABLE_OFFLINE', 'false') == 'true'
GEO         = os.environ.get('ENABLE_GEO',     'false') == 'true'
CAMERA      = os.environ.get('ENABLE_CAMERA',  'false') == 'true'
PERMISSIONS = [p.strip() for p in os.environ.get('PERMISSIONS','INTERNET').split(',') if p.strip()]
MIN_SDK     = os.environ.get('MIN_SDK',    '23')
TARGET_SDK  = os.environ.get('TARGET_SDK', '33')
ORIENTATION = os.environ.get('ORIENTATION','unspecified')

PKG_PATH = PKG_ID.replace('.','/')
BASE     = 'generated'

def w(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'w',encoding='utf-8') as f: f.write(content)
    print(f'  {path}')

def wb(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'wb') as f: f.write(data)
    print(f'  {path} (bin)')

# ─── AndroidManifest.xml ─────────────────────────────────────────────────────
perm_xml = '\n'.join(f'    <uses-permission android:name="android.permission.{p}"/>' for p in PERMISSIONS)

camera_provider = '''
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="${applicationId}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths"/>
        </provider>''' if CAMERA else ''

w(f'{BASE}/app/src/main/AndroidManifest.xml', f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{PKG_ID}">
{perm_xml}
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/AppTheme"
        android:hardwareAccelerated="true"
        android:usesCleartextTraffic="true">
        <activity android:name=".SplashActivity" android:exported="true"
            android:screenOrientation="{ORIENTATION}" android:theme="@style/SplashTheme">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
        <activity android:name=".MainActivity" android:exported="false"
            android:screenOrientation="{ORIENTATION}" android:theme="@style/AppTheme"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:windowSoftInputMode="adjustResize"/>{camera_provider}
    </application>
</manifest>''')

# ─── SplashActivity.java ──────────────────────────────────────────────────────
w(f'{BASE}/app/src/main/java/{PKG_PATH}/SplashActivity.java', f'''package {PKG_ID};
import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
public class SplashActivity extends Activity {{
    @Override protected void onCreate(Bundle s) {{
        super.onCreate(s);
        setContentView(R.layout.activity_splash);
        new Handler(Looper.getMainLooper()).postDelayed(() -> {{
            startActivity(new Intent(this, MainActivity.class));
            finish();
        }}, {SPLASH_MS});
    }}
}}''')

# ─── MainActivity.java ────────────────────────────────────────────────────────
cam_imports = '''
import android.net.Uri; import android.content.Intent;
import android.provider.MediaStore; import androidx.core.content.FileProvider;
import java.io.File; import java.io.IOException;
import java.text.SimpleDateFormat; import java.util.Date; import java.util.Locale;''' if CAMERA else ''

cam_fields = '''
    private ValueCallback<Uri[]> fileCb; private Uri camUri;
    private static final int FC_REQ = 100;''' if CAMERA else ''

cam_result = '''
    @Override protected void onActivityResult(int rq, int rs, Intent d) {
        if (rq == FC_REQ) {
            if (fileCb == null) return;
            Uri[] res = null;
            if (rs == RESULT_OK) res = d!=null&&d.getData()!=null ? new Uri[]{d.getData()} : camUri!=null ? new Uri[]{camUri} : null;
            fileCb.onReceiveValue(res); fileCb = null;
        }
        super.onActivityResult(rq, rs, d);
    }''' if CAMERA else ''

cam_chrome = '''
            @Override public boolean onShowFileChooser(WebView wv, ValueCallback<Uri[]> cb, FileChooserParams fp) {
                fileCb = cb;
                startActivityForResult(Intent.createChooser(fp.createIntent(),"Choose"), FC_REQ);
                return true;
            }''' if CAMERA else ''

cache_line = 's.setAppCacheEnabled(true); s.setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);' if OFFLINE else 's.setCacheMode(WebSettings.LOAD_DEFAULT);'
geo_line   = 's.setGeolocationEnabled(true);' if GEO else ''

w(f'{BASE}/app/src/main/java/{PKG_PATH}/MainActivity.java', f'''package {PKG_ID};
import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.*;
import android.widget.ProgressBar;{cam_imports}

public class MainActivity extends Activity {{{cam_fields}
    private WebView wv; private ProgressBar pb;
    private static final String URL = "{APP_URL}";

    @SuppressLint("SetJavaScriptEnabled")
    @Override protected void onCreate(Bundle s) {{
        super.onCreate(s);
        setContentView(R.layout.activity_main);
        wv = findViewById(R.id.webView);
        pb = findViewById(R.id.progressBar);
        WebSettings ws = wv.getSettings();
        ws.setJavaScriptEnabled({str(JS_ENABLED).lower()});
        ws.setDomStorageEnabled(true); ws.setDatabaseEnabled(true);
        ws.setAllowFileAccess(true); ws.setAllowContentAccess(true);
        ws.setSupportZoom({str(ZOOM_ENABLED).lower()});
        ws.setBuiltInZoomControls({str(ZOOM_ENABLED).lower()});
        ws.setDisplayZoomControls(false);
        ws.setLoadWithOverviewMode(true); ws.setUseWideViewPort(true);
        ws.setMediaPlaybackRequiresUserGesture(false);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        {cache_line}
        {geo_line}
        wv.setWebViewClient(new WebViewClient() {{
            @Override public void onPageStarted(WebView v, String u, Bitmap f) {{ if(pb!=null) pb.setVisibility(View.VISIBLE); }}
            @Override public void onPageFinished(WebView v, String u) {{ if(pb!=null) pb.setVisibility(View.GONE); }}
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {{ v.loadUrl(r.getUrl().toString()); return true; }}
            @Override public void onReceivedError(WebView v, WebResourceRequest r, WebResourceError e) {{
                v.loadData("<html><body style='background:#111;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center'><div><h2>No Connection</h2><p>Check internet and try again.</p><button onclick=location.reload() style='background:#3b82f6;color:#fff;border:none;padding:12px 24px;border-radius:8px;font-size:16px'>Retry</button></div></body></html>","text/html","UTF-8");
            }}
        }});
        wv.setWebChromeClient(new WebChromeClient() {{
            @Override public void onProgressChanged(WebView v, int p) {{
                if(pb!=null){{ pb.setProgress(p); pb.setVisibility(p<100?View.VISIBLE:View.GONE); }}
            }}{cam_chrome}
        }});
        wv.loadUrl(URL);
    }}
    @Override public boolean onKeyDown(int k, KeyEvent e) {{
        if(k==KeyEvent.KEYCODE_BACK && wv.canGoBack()){{ wv.goBack(); return true; }}
        return super.onKeyDown(k,e);
    }}{cam_result}
}}''')

# ─── Layouts ──────────────────────────────────────────────────────────────────
w(f'{BASE}/app/src/main/res/layout/activity_main.xml', '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent" android:layout_height="match_parent"
    android:orientation="vertical">
    <ProgressBar android:id="@+id/progressBar"
        style="?android:attr/progressBarStyleHorizontal"
        android:layout_width="match_parent" android:layout_height="3dp"
        android:max="100" android:visibility="gone"/>
    <WebView android:id="@+id/webView"
        android:layout_width="match_parent" android:layout_height="0dp"
        android:layout_weight="1"/>
</LinearLayout>''')

w(f'{BASE}/app/src/main/res/layout/activity_splash.xml', f'''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent" android:layout_height="match_parent"
    android:gravity="center" android:orientation="vertical"
    android:background="@color/colorPrimary" android:padding="40dp">
    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="@string/app_name" android:textColor="#FFFFFF"
        android:textSize="34sp" android:textStyle="bold" android:layout_marginBottom="14dp"/>
    <View android:layout_width="56dp" android:layout_height="3dp"
        android:background="#44FFFFFF" android:layout_marginBottom="18dp"/>
    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="@string/splash_text" android:textColor="#BBFFFFFF" android:textSize="15sp"/>
</LinearLayout>''')

# ─── Values ───────────────────────────────────────────────────────────────────
w(f'{BASE}/app/src/main/res/values/strings.xml', f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{APP_NAME}</string>
    <string name="splash_text">{SPLASH_TEXT}</string>
</resources>''')

w(f'{BASE}/app/src/main/res/values/colors.xml', f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="colorPrimary">{COLOR_P}</color>
    <color name="colorPrimaryDark">{COLOR_P}</color>
    <color name="colorAccent">{COLOR_A}</color>
    <color name="colorBackground">{COLOR_BG}</color>
</resources>''')

w(f'{BASE}/app/src/main/res/values/styles.xml', '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="Theme.AppCompat.Light.NoActionBar">
        <item name="colorPrimary">@color/colorPrimary</item>
        <item name="colorPrimaryDark">@color/colorPrimaryDark</item>
        <item name="colorAccent">@color/colorAccent</item>
        <item name="android:windowBackground">@color/colorBackground</item>
    </style>
    <style name="SplashTheme" parent="Theme.AppCompat.NoActionBar">
        <item name="android:windowBackground">@color/colorPrimary</item>
        <item name="colorPrimary">@color/colorPrimary</item>
    </style>
</resources>''')

if CAMERA:
    w(f'{BASE}/app/src/main/res/xml/file_paths.xml', '''<?xml version="1.0" encoding="utf-8"?>
<paths><cache-path name="cam" path="."/><external-path name="ext" path="."/></paths>''')

# ─── Icons: generate real PNG for every density ───────────────────────────────
def make_png(size, hex_color):
    r,g,b = int(hex_color[1:3],16), int(hex_color[3:5],16), int(hex_color[5:7],16)
    def chunk(tag, data):
        crc = zlib.crc32(tag+data)&0xFFFFFFFF
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',crc)
    raw  = (b'\x00'+bytes([r,g,b]*size))*size
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB',size,size,8,2,0,0,0))
            + chunk(b'IDAT', zlib.compress(raw,9))
            + chunk(b'IEND', b''))

clean_hex = COLOR_P.lstrip('#').ljust(6,'0')[:6]
for folder, size in [('mipmap-mdpi',48),('mipmap-hdpi',72),('mipmap-xhdpi',96),
                     ('mipmap-xxhdpi',144),('mipmap-xxxhdpi',192)]:
    png = make_png(size, '#'+clean_hex)
    wb(f'{BASE}/app/src/main/res/{folder}/ic_launcher.png', png)
    wb(f'{BASE}/app/src/main/res/{folder}/ic_launcher_round.png', png)

w(f'{BASE}/app/src/main/res/drawable/ic_launcher_foreground.xml', f'''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
  <path android:fillColor="#FFFFFF"
    android:pathData="M54,22L68,46L96,46L74,64L82,90L54,74L26,90L34,64L12,46L40,46Z"/>
</vector>''')

w(f'{BASE}/app/src/main/res/drawable/ic_launcher_background.xml', f'''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android">
    <solid android:color="{COLOR_P}"/>
</shape>''')

w(f'{BASE}/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml', '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>''')

w(f'{BASE}/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml', '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>''')

# ─── Gradle ───────────────────────────────────────────────────────────────────
w(f'{BASE}/settings.gradle', f'rootProject.name = "{APP_NAME}"\ninclude \':app\'\n')

w(f'{BASE}/build.gradle', '''buildscript {
    repositories { google(); mavenCentral() }
    dependencies { classpath 'com.android.tools.build:gradle:8.2.2' }
}
allprojects { repositories { google(); mavenCentral() } }
''')

w(f'{BASE}/app/build.gradle', f'''plugins {{ id 'com.android.application' }}
android {{
    namespace '{PKG_ID}'
    compileSdk {TARGET_SDK}
    defaultConfig {{
        applicationId "{PKG_ID}"
        minSdk {MIN_SDK}
        targetSdk {TARGET_SDK}
        versionCode {VERSION_CODE}
        versionName "{APP_VERSION}"
    }}
    buildTypes {{
        debug {{ debuggable true; minifyEnabled false }}
        release {{ minifyEnabled false }}
    }}
    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }}
}}
dependencies {{
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'androidx.core:core:1.12.0'
}}
''')

w(f'{BASE}/gradle.properties',
  'android.useAndroidX=true\nandroid.enableJetifier=true\norg.gradle.jvmargs=-Xmx2048m\norg.gradle.daemon=false\n')

w(f'{BASE}/gradle/wrapper/gradle-wrapper.properties',
  'distributionBase=GRADLE_USER_HOME\ndistributionPath=wrapper/dists\n'
  'distributionUrl=https\\://services.gradle.org/distributions/gradle-8.2-bin.zip\n'
  'zipStoreBase=GRADLE_USER_HOME\nzipStorePath=wrapper/dists\n')

w(f'{BASE}/gradlew', '''#!/bin/sh
APP_HOME="$(cd "$(dirname "$0")" && pwd)"
JAR="$APP_HOME/gradle/wrapper/gradle-wrapper.jar"
JAVACMD="${JAVA_HOME:+$JAVA_HOME/bin/}java"
exec "$JAVACMD" -classpath "$JAR" org.gradle.wrapper.GradleWrapperMain "$@"
''')
os.chmod(f'{BASE}/gradlew', 0o755)

# Download gradle-wrapper.jar
print("Downloading gradle-wrapper.jar...")
for url in [
    "https://github.com/gradle/gradle/raw/v8.2.0/gradle/wrapper/gradle-wrapper.jar",
    "https://raw.githubusercontent.com/gradle/gradle/v8.2.0/gradle/wrapper/gradle-wrapper.jar",
]:
    try:
        urllib.request.urlretrieve(url, f'{BASE}/gradle/wrapper/gradle-wrapper.jar')
        print("  OK"); break
    except Exception as e:
        print(f"  failed: {e}")

print(f"\n✓ Done! {APP_NAME} | {PKG_ID} | {APP_URL} | SDK {MIN_SDK}→{TARGET_SDK}")
