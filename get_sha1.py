import subprocess
import re

# Try to get SHA-1 from debug keystore
keystore_path = r"C:\Users\bonni\.android\debug.keystore"

try:
    # Use flutter to print the SHA
    result = subprocess.run(
        ["flutter", "build", "apk", "--debug", "-v"],
        capture_output=True,
        text=True,
        cwd=r"Lovable Frontend\export\mobile"
    )
    
    output = result.stdout + result.stderr
    
    # Look for SHA patterns
    sha1_pattern = r"SHA1:\s*([A-F0-9:]+)"
    sha256_pattern = r"SHA256:\s*([A-F0-9:]+)"
    
    sha1_matches = re.findall(sha1_pattern, output, re.IGNORECASE)
    sha256_matches = re.findall(sha256_pattern, output, re.IGNORECASE)
    
    if sha1_matches:
        print("SHA-1 Fingerprint:")
        for match in sha1_matches:
            print(f"  {match}")
    
    if sha256_matches:
        print("\nSHA-256 Fingerprint:")
        for match in sha256_matches:
            print(f"  {match}")
    
    if not sha1_matches and not sha256_matches:
        print("Could not find SHA fingerprints in build output")
        print("\nPlease use one of these methods:")
        print("1. Install the APK on your phone and check Play Console")
        print("2. Use Firebase Console to auto-detect (see below)")
        
except Exception as e:
    print(f"Error: {e}")
    
print("\n" + "="*60)
print("EASIEST METHOD - Let Firebase auto-detect:")
print("="*60)
print("1. Go to Firebase Console → Authentication → Sign-in method")
print("2. Enable Google sign-in if not already enabled")
print("3. Install your APK on a real Android device")
print("4. Try to sign in with Google on the device")
print("5. The error will show up in Firebase Console with the SHA-1")
print("6. Firebase will show: 'Add this SHA-1 to allow this app'")
print("7. Click the button to add it automatically")
