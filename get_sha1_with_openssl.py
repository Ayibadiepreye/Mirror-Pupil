"""
Extract SHA-1 from Android debug keystore using OpenSSL
"""
import subprocess
import os
from pathlib import Path

keystore_path = Path.home() / ".android" / "debug.keystore"

if not keystore_path.exists():
    print(f"❌ Keystore not found: {keystore_path}")
    exit(1)

print(f"✅ Found keystore: {keystore_path}\n")

# Convert keystore to PKCS12 format, then extract certificate
temp_p12 = "temp_debug.p12"
temp_cert = "temp_cert.pem"

try:
    # We'll use a pure Python approach with direct keystore reading
    # First, let's try to read it as a raw file and look for certificate patterns
    
    with open(keystore_path, 'rb') as f:
        data = f.read()
    
    # Check keystore type by magic bytes
    if data[:4] == b'\xfe\xed\xfe\xed':
        print("✅ Detected: JKS keystore")
    elif data[:4] == b'\xce\xce\xce\xce':
        print("✅ Detected: JCEKS keystore")
    else:
        print(f"⚠️  Unknown keystore format (magic: {data[:4].hex()})")
    
    # Try using keytool from Android SDK if available
    android_home = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
    
    if android_home:
        keytool_path = Path(android_home) / "cmdline-tools" / "latest" / "bin" / "keytool.bat"
        if not keytool_path.exists():
            # Try older structure
            keytool_path = Path(android_home) / "tools" / "bin" / "keytool.bat"
        
        if keytool_path.exists():
            print(f"\n✅ Found keytool: {keytool_path}\n")
            result = subprocess.run(
                [str(keytool_path), "-list", "-v", "-keystore", str(keystore_path), 
                 "-storepass", "android", "-alias", "androiddebugkey"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                output = result.stdout
                # Extract SHA-1
                for line in output.split('\n'):
                    if 'SHA1:' in line:
                        sha1 = line.split('SHA1:')[1].strip()
                        print("="*70)
                        print("🎯 SHA-1 FINGERPRINT")
                        print("="*70)
                        print(f"\n{sha1}\n")
                        print("="*70)
                        print("\n📋 ADD TO FIREBASE:")
                        print(f"\n{sha1}")
                        print("\n1. Go to https://console.firebase.google.com/")
                        print("2. Project Settings → Your Android app")
                        print("3. Add fingerprint → Paste SHA-1 → Save")
                        print("4. Download google-services.json")
                        print("5. Replace in: Lovable Frontend\\export\\mobile\\android\\app\\")
                        exit(0)
    
    # If we reach here, we need another method
    print("\n⚠️  Could not find keytool")
    print("\n" + "="*70)
    print("SOLUTION: Use gradlew to get SHA-1")
    print("="*70)
    print("\n1. Open PowerShell/CMD")
    print("\n2. Run:")
    print("   cd 'Lovable Frontend\\export\\mobile\\android'")
    print("   .\\gradlew signingReport")
    print("\n3. Look for 'SHA1:' in the output")
    print("\n4. Copy that SHA-1 and add it to Firebase")
    print("\n" + "="*70)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
