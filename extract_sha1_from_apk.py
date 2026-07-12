"""
Extract SHA-1 fingerprint directly from APK file
No Java/keytool needed!
"""
import zipfile
import os
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("Installing cryptography...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'cryptography'])
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend

# Path to your APK
apk_path = Path("Lovable Frontend/export/mobile/build/app/outputs/flutter-apk/app-release.apk")

if not apk_path.exists():
    print(f"❌ APK not found at: {apk_path}")
    print("\nBuild it first:")
    print("cd 'Lovable Frontend\\export\\mobile' && flutter build apk --release")
    exit(1)

print(f"✅ Found APK: {apk_path}")
print("\nExtracting certificate from APK...\n")

try:
    # Open APK as ZIP
    with zipfile.ZipFile(apk_path, 'r') as apk_zip:
        # List certificate files in META-INF
        cert_files = [f for f in apk_zip.namelist() if f.startswith('META-INF/') and (f.endswith('.RSA') or f.endswith('.DSA') or f.endswith('.EC'))]
        
        if not cert_files:
            print("❌ No certificate found in APK")
            exit(1)
        
        # Read the first certificate
        cert_file = cert_files[0]
        print(f"📜 Found certificate: {cert_file}")
        
        with apk_zip.open(cert_file) as cert_data:
            cert_bytes = cert_data.read()
        
        # Parse PKCS7 signature block to extract certificate
        # The certificate is in DER format inside the PKCS7 structure
        # We need to extract it properly
        
        from cryptography.hazmat.primitives.serialization import pkcs7
        from cryptography.hazmat.primitives.serialization.pkcs7 import PKCS7SignatureBuilder
        
        # Load PKCS7 data
        try:
            # Try to load as PKCS7 PEM
            pkcs7_data = pkcs7.load_der_pkcs7_certificates(cert_bytes)
            cert = pkcs7_data[0]
        except:
            # Try parsing as raw DER certificate
            try:
                cert = x509.load_der_x509_certificate(cert_bytes, default_backend())
            except:
                # Try extracting from PKCS7 manually
                # PKCS7 structure contains certificate after specific bytes
                # Look for certificate start marker (0x30 0x82)
                for i in range(len(cert_bytes) - 4):
                    if cert_bytes[i:i+2] == b'\x30\x82':
                        try:
                            cert = x509.load_der_x509_certificate(cert_bytes[i:], default_backend())
                            break
                        except:
                            continue
        
        # Calculate fingerprints
        sha1_fingerprint = cert.fingerprint(hashes.SHA1())
        sha1 = ':'.join('{:02X}'.format(b) for b in sha1_fingerprint)
        
        sha256_fingerprint = cert.fingerprint(hashes.SHA256())
        sha256 = ':'.join('{:02X}'.format(b) for b in sha256_fingerprint)
        
        print("\n" + "="*70)
        print("🎯 APK CERTIFICATE FINGERPRINTS")
        print("="*70)
        print(f"\nSHA-1:   {sha1}")
        print(f"\nSHA-256: {sha256}")
        print("\n" + "="*70)
        print("\n📋 ADD THIS SHA-1 TO FIREBASE:")
        print("="*70)
        print("\n1. Copy the SHA-1 above")
        print("\n2. Go to: https://console.firebase.google.com/")
        print("\n3. Select project → ⚙️ Settings → Project Settings")
        print("\n4. Scroll to 'Your apps' → Android app")
        print("\n5. Click 'Add fingerprint' button")
        print(f"\n6. Paste: {sha1}")
        print("\n7. Click Save")
        print("\n8. Download updated google-services.json")
        print("\n9. Replace: Lovable Frontend\\export\\mobile\\android\\app\\google-services.json")
        print("\n10. Rebuild if needed")
        print("\n✅ ALL USERS can now use Google Sign-In!")
        print("\n" + "="*70)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
