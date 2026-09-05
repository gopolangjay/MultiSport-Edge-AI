from pathlib import Path


def test_android_manifest_allows_internet_but_rejects_cleartext():
    manifest = Path("android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    assert 'android.permission.INTERNET' in manifest
    assert 'android:usesCleartextTraffic="false"' in manifest
