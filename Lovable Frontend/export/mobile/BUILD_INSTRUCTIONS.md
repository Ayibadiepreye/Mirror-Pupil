# Mirror Pupil Mobile - Build Instructions

## Flutter App (Android/iOS)

### Prerequisites
- Flutter SDK 3.3.0 or higher
- Android Studio with Android SDK
- Xcode (for iOS builds, macOS only)
- Java 17 or higher

### Backend Configuration
The app is pre-configured to connect to your VPS backend:
- **API URL**: `https://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil`
- **WebSocket URL**: `wss://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil`

### Build Commands

#### Android Release Build (Optimized for All Devices)
```bash
cd "Lovable Frontend/export/mobile"

# Build APK (Universal - works on all devices)
flutter build apk --release

# Build App Bundle (for Google Play Store)
flutter build appbundle --release

# Build split APKs (smaller downloads per device)
flutter build apk --release --split-per-abi
```

**Output locations:**
- Universal APK: `build/app/outputs/flutter-apk/app-release.apk`
- App Bundle: `build/app/outputs/bundle/release/app-release.aab`
- Split APKs: `build/app/outputs/flutter-apk/app-armeabi-v7a-release.apk`, etc.

#### iOS Release Build
```bash
cd "Lovable Frontend/export/mobile"

# Build iOS app
flutter build ios --release

# Build iOS IPA (for distribution)
flutter build ipa --release
```

**Output location:** `build/ios/ipa/mirror_pupil_mobile.ipa`

### Build Optimizations

The release builds are optimized for:
- ✅ **Low-spec devices** - Supports Android 5.0+ (API 21)
- ✅ **Small app size** - Code minification, resource shrinking, ProGuard enabled
- ✅ **Fast loading** - Tree shaking, lazy loading, optimized assets
- ✅ **Battery efficiency** - Optimized rendering, background task management
- ✅ **Network efficiency** - HTTP caching, request deduplication

### Testing Release Build
```bash
# Install APK on connected device
flutter install

# Or manually:
adb install build/app/outputs/flutter-apk/app-release.apk
```

### Distribution Options

#### 1. Direct APK Distribution
- Share `app-release.apk` directly to users
- Users enable "Install from Unknown Sources"
- Best for internal testing

#### 2. Google Play Store
- Upload `app-release.aab` to Google Play Console
- Follow Play Store review process
- Best for public distribution

#### 3. Firebase App Distribution
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Deploy
firebase appdistribution:distribute build/app/outputs/flutter-apk/app-release.apk \
  --app YOUR_FIREBASE_APP_ID \
  --groups testers
```

---

## Web App (Vercel Deployment)

### Prerequisites
- Node.js 18+ and npm
- Vercel account (free tier works)
- Vercel CLI (optional)

### Method 1: Deploy via Vercel Dashboard (Easiest)

1. **Push to GitHub** (if not already)
   ```bash
   cd "Lovable Frontend"
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Connect to Vercel**
   - Go to https://vercel.com/new
   - Click "Import Git Repository"
   - Select your GitHub repo
   - Click "Import"

3. **Configure Build Settings**
   - **Framework Preset**: Vite
   - **Root Directory**: `Lovable Frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

4. **Add Environment Variables**
   - Click "Environment Variables"
   - Add these variables:
     ```
     VITE_API_URL=https://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil
     VITE_WS_URL=wss://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil
     VITE_USE_MOCK=false
     VITE_FIREBASE_API_KEY=AIzaSyAjxKQJFeRdFwHMYybKcNer5QQHp2nVUz8
     VITE_FIREBASE_AUTH_DOMAIN=mirror-pupil.firebaseapp.com
     VITE_FIREBASE_PROJECT_ID=mirror-pupil
     VITE_FIREBASE_STORAGE_BUCKET=mirror-pupil.firebasestorage.app
     VITE_FIREBASE_MESSAGING_SENDER_ID=2009963821
     VITE_FIREBASE_APP_ID=1:2009963821:web:d1dc6133ae10a1fc8747a4
     VITE_FIREBASE_MEASUREMENT_ID=G-GNS6TYCQCX
     ```

5. **Deploy**
   - Click "Deploy"
   - Wait for build to complete (~2-3 minutes)
   - Your app will be live at `https://your-project.vercel.app`

### Method 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Update .env for Production**
   ```bash
   cd "Lovable Frontend"
   
   # Update .env file
   echo "VITE_API_URL=https://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil" > .env.production
   echo "VITE_WS_URL=wss://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil" >> .env.production
   echo "VITE_USE_MOCK=false" >> .env.production
   echo "VITE_FIREBASE_API_KEY=AIzaSyAjxKQJFeRdFwHMYybKcNer5QQHp2nVUz8" >> .env.production
   echo "VITE_FIREBASE_AUTH_DOMAIN=mirror-pupil.firebaseapp.com" >> .env.production
   echo "VITE_FIREBASE_PROJECT_ID=mirror-pupil" >> .env.production
   echo "VITE_FIREBASE_STORAGE_BUCKET=mirror-pupil.firebasestorage.app" >> .env.production
   echo "VITE_FIREBASE_MESSAGING_SENDER_ID=2009963821" >> .env.production
   echo "VITE_FIREBASE_APP_ID=1:2009963821:web:d1dc6133ae10a1fc8747a4" >> .env.production
   echo "VITE_FIREBASE_MEASUREMENT_ID=G-GNS6TYCQCX" >> .env.production
   ```

4. **Deploy**
   ```bash
   # First deployment (creates project)
   vercel
   
   # Production deployment
   vercel --prod
   ```

5. **Follow prompts:**
   - Set up and deploy? `Y`
   - Which scope? Select your account
   - Link to existing project? `N`
   - Project name? `mirror-pupil` (or your choice)
   - Directory? `.` (current directory)
   - Override settings? `N`

### Method 3: Build Locally and Deploy

```bash
cd "Lovable Frontend"

# Install dependencies
npm install

# Build for production
npm run build

# Deploy dist folder
vercel --prod dist
```

### Post-Deployment

1. **Test the deployment:**
   - Visit your Vercel URL
   - Try logging in with Firebase
   - Check API connectivity

2. **Set up custom domain (optional):**
   - Go to Vercel project settings
   - Add custom domain
   - Update DNS records

3. **Enable HTTPS:**
   - Vercel automatically provisions SSL certificates
   - Your backend already supports HTTPS via Tailscale

### Vercel Build Configuration File (Optional)

Create `vercel.json` in `Lovable Frontend` directory:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        }
      ]
    }
  ]
}
```

### Troubleshooting

**Build fails:**
- Check Node.js version (`node --version` should be 18+)
- Clear cache: `rm -rf node_modules package-lock.json && npm install`
- Check environment variables are set correctly

**API connection fails:**
- Verify backend is running: `curl https://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil/health`
- Check browser console for CORS errors
- Verify Firebase authentication is working

**WebSocket connection fails:**
- Ensure backend supports WebSocket on same endpoint
- Check for proxy/firewall blocking WSS connections

---

## Summary

### Flutter APK for Android:
```bash
cd "Lovable Frontend/export/mobile"
flutter build apk --release --split-per-abi
# Share: build/app/outputs/flutter-apk/app-arm64-v8a-release.apk
```

### Web App on Vercel:
```bash
cd "Lovable Frontend"
vercel --prod
# Live at: https://your-project.vercel.app
```

Both are now connected to your VPS backend at:
**https://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil**
