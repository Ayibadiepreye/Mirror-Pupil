# Mirror Pupil App Icon & Splash Screen Setup

## Current Status
✅ Splash screen XML configured with theme gradient
❌ Need to generate PNG icons from logo.svg

## Required Icon Sizes (Android)

The logo is at: `assets/logo.svg`

### Generate these PNG files:

1. **mipmap-mdpi/ic_launcher.png** - 48x48 px
2. **mipmap-hdpi/ic_launcher.png** - 72x72 px  
3. **mipmap-xhdpi/ic_launcher.png** - 96x96 px
4. **mipmap-xxhdpi/ic_launcher.png** - 144x144 px
5. **mipmap-xxxhdpi/ic_launcher.png** - 192x192 px

## Option 1: Use flutter_launcher_icons (Recommended)

```bash
# Add to pubspec.yaml
flutter pub add flutter_launcher_icons --dev

# Create flutter_launcher_icons.yaml
```

```yaml
flutter_launcher_icons:
  android: true
  ios: false
  image_path: "assets/logo.svg"
  adaptive_icon_background: "#16161A"
  adaptive_icon_foreground: "assets/logo.svg"
```

```bash
# Generate icons
flutter pub run flutter_launcher_icons
```

## Option 2: Manual Conversion (If SVG tools available)

Use ImageMagick or Inkscape:

```bash
# With Inkscape (if installed)
inkscape assets/logo.svg -w 192 -h 192 -o android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png
inkscape assets/logo.svg -w 144 -h 144 -o android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png
inkscape assets/logo.svg -w 96 -h 96 -o android/app/src/main/res/mipmap-xhdpi/ic_launcher.png
inkscape assets/logo.svg -w 72 -h 72 -o android/app/src/main/res/mipmap-hdpi/ic_launcher.png
inkscape assets/logo.svg -w 48 -h 48 -o android/app/src/main/res/mipmap-mdpi/ic_launcher.png
```

## Option 3: Online Tool (Easiest)

1. Go to https://appicon.co/ or https://icon.kitchen/
2. Upload `assets/logo.svg`
3. Select Android only
4. Download ZIP
5. Extract to `android/app/src/main/res/`

## Splash Screen Status

✅ **Already configured** with theme colors:
- Background gradient: #16161A → #1E1E24
- Crimson glow effect
- Logo centered

File: `android/app/src/main/res/drawable/launch_background.xml`
