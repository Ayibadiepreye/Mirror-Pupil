import os
import hashlib
from pathlib import Path

# Path to debug keystore
keystore_path = Path.home() / ".android" / "debug.keystore"

if not keystore_path.exists():
    print(f"Debug keystore not found at: {keystore_path}")
    print("\nYou need to build the Flutter app at least once to generate it.")
    print("Run: cd 'Lovable Frontend\\export\\mobile' && flutter build apk --debug")
    exit(1)

print(f"Found keystore at: {keystore_path}")
print("\nTo extract SHA-1, we need Java's keytool.")
print("\nSince you don't have Java installed, here's the easiest method:\n")
print("="*70)
print("INSTALL YOUR APK AND LET FIREBASE AUTO-DETECT THE SHA-1:")
print("="*70)
print("\n1. Transfer the APK to your Android phone:")
print("   File: Lovable Frontend\\export\\mobile\\build\\app\\outputs\\flutter-apk\\app-release.apk")
print("\n2. Install and open the app")
print("\n3. Try to sign in with Google (it will fail)")
print("\n4. Go to Firebase Console:")
print("   https://console.firebase.google.com/")
print("   → Your Project → Authentication → Sign-in method")
print("\n5. Firebase will detect the failed attempt and show:")
print("   'Certificate not authorized: SHA1: XX:XX:...'")
print("   with a button to add it automatically")
print("\n6. Click 'Add fingerprint' or 'Whitelist' button")
print("\n7. Try signing in on the app again - should work!")
print("\n" + "="*70)
print("\nOR - Install Java JDK to extract SHA-1 manually:")
print("Download from: https://adoptium.net/")
print("Then run: keytool -list -v -keystore \"%USERPROFILE%\\.android\\debug.keystore\" -alias androiddebugkey -storepass android -keypass android")
