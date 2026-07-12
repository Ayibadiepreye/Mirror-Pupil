"""
Extract SHA-1 fingerprint from Android debug keystore without Java
"""
import os
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography import x509
except ImportError:
    print("Installing required library...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'cryptography'])
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
    from cryptography import x509

import jks

# Install jks library if not present
try:
    import jks
except ImportError:
    print("Installing jks library...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'pyjks'])
    import jks

# Path to debug keystore
keystore_path = Path.home() / ".android" / "debug.keystore"
keystore_password = "android"
alias = "androiddebugkey"
key_password = "android"

if not keystore_path.exists():
    print(f"❌ Debug keystore not found at: {keystore_path}")
    print("\nBuild the Flutter app first to generate it:")
    print("cd 'Lovable Frontend\\export\\mobile' && flutter build apk")
    exit(1)

print(f"✅ Found keystore at: {keystore_path}\n")
print("Extracting SHA-1 fingerprint...\n")

try:
    # Try loading as different keystore types
    ks = None
    for store_type in ['jks', 'jceks', 'bks', 'uber']:
        try:
            if store_type == 'jks':
                ks = jks.KeyStore.load(str(keystore_path), keystore_password)
            elif store_type == 'jceks':
                ks = jks.KeyStore.load(str(keystore_path), keystore_password, try_decrypt_keys=False)
            elif store_type == 'bks':
                ks = jks.BksKeyStore.load(str(keystore_path), keystore_password)
            elif store_type == 'uber':
                ks = jks.UberKeyStore.load(str(keystore_path), keystore_password)
            print(f"✅ Loaded as {store_type.upper()} keystore")
            break
        except:
            continue
    
    if not ks:
        raise Exception("Could not load keystore in any known format")
    
    # Get the private key entry
    pk_entry = ks.private_keys.get(alias) or ks.private_keys.get('key0') or list(ks.private_keys.values())[0]
    
    # Get the first certificate in the chain
    cert_chain = pk_entry.cert_chain
    if not cert_chain:
        print("❌ No certificate found in keystore")
        exit(1)
    
    # Parse the certificate
    cert_data = cert_chain[0][1]
    cert = x509.load_der_x509_certificate(cert_data, default_backend())
    
    # Calculate SHA-1 fingerprint
    fingerprint = cert.fingerprint(hashes.SHA1())
    sha1 = ':'.join('{:02X}'.format(b) for b in fingerprint)
    
    # Calculate SHA-256 fingerprint (also useful)
    fingerprint_256 = cert.fingerprint(hashes.SHA256())
    sha256 = ':'.join('{:02X}'.format(b) for b in fingerprint_256)
    
    print("="*70)
    print("🎯 ANDROID DEBUG KEYSTORE FINGERPRINTS")
    print("="*70)
    print(f"\nSHA-1:   {sha1}")
    print(f"\nSHA-256: {sha256}")
    print("\n" + "="*70)
    print("\n📋 NEXT STEPS:")
    print("="*70)
    print("\n1. Copy the SHA-1 fingerprint above")
    print("\n2. Go to Firebase Console:")
    print("   https://console.firebase.google.com/")
    print("\n3. Select your project → Settings ⚙️ → Project Settings")
    print("\n4. Scroll to 'Your apps' → Find your Android app")
    print("\n5. Click 'Add fingerprint'")
    print("\n6. Paste the SHA-1 and click Save")
    print("\n7. Download the updated google-services.json")
    print("\n8. Replace: Lovable Frontend\\export\\mobile\\android\\app\\google-services.json")
    print("\n9. Rebuild: flutter build apk --release")
    print("\n✅ Google Sign-In will work for ALL users!")
    print("\n" + "="*70)
    
except Exception as e:
    print(f"❌ Error reading keystore: {e}")
    print("\nTrying alternative method...")
    print("\nYou can also get SHA-1 by:")
    print("1. Install the APK on your phone")
    print("2. Try Google Sign-In (will fail)")
    print("3. Firebase Console will show the SHA-1 in the error")
    print("4. Click 'Add fingerprint' button")
