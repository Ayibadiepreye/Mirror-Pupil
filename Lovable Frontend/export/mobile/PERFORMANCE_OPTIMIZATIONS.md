# Performance Optimizations for Lower-End Devices

This document outlines the optimizations made to ensure Mirror Pupil runs smoothly on lower-spec Android devices.

## Target Devices
- **Minimum Android Version**: Android 5.0 (Lollipop, API 21)
- **RAM**: 1GB+ recommended, optimized for 512MB-1GB devices
- **Processor**: Any ARMv7 or ARM64 processor

## Optimizations Applied

### 1. Android Build Configuration (`android/app/build.gradle.kts`)

#### Min SDK Lowered
```kotlin
minSdk = 21  // Android 5.0 - supports 95%+ of devices
```

#### Multidex Enabled
Prevents app crashes on devices with limited method count:
```kotlin
multiDexEnabled = true
```

#### APK Splitting by ABI
Reduces download size by ~60% (users only download their device's architecture):
```kotlin
splits {
    abi {
        isEnable = true
        include("armeabi-v7a", "arm64-v8a", "x86_64")
        isUniversalApk = true
    }
}
```

#### Code Shrinking & Obfuscation
Reduces APK size by removing unused code:
```kotlin
release {
    isMinifyEnabled = true
    isShrinkResources = true
    proguardFiles(...)
}
```

### 2. Flutter App Optimizations (`lib/main.dart`)

#### Image Cache Limits
Prevents OutOfMemory errors on low-RAM devices:
```dart
PaintingBinding.instance.imageCache.maximumSize = 50;       // Max 50 images
PaintingBinding.instance.imageCache.maximumSizeBytes = 50 << 20;  // Max 50 MB
```

### 3. Memory Management Best Practices

All screens implement:
- **Lazy loading**: Data loads as needed
- **Pagination**: Large lists split into pages
- **Dispose pattern**: Resources cleaned up when screens close
- **Cached network images**: Reduces repeated downloads

### 4. UI Performance

- **Material Design 3**: Hardware-accelerated animations
- **ListView.builder**: Only renders visible items
- **const constructors**: Reduces widget rebuilds
- **Key widgets**: Preserves state during rebuilds

## Build Instructions for Optimized APK

### Development Build (Faster, Larger)
```bash
cd "Lovable Frontend/export/mobile"
flutter build apk
```

### Production Build (Smaller, Optimized)
```bash
cd "Lovable Frontend/export/mobile"
flutter build apk --release --split-per-abi
```

This creates 4 APKs:
- `app-armeabi-v7a-release.apk` - 32-bit ARM (older phones) ~15MB
- `app-arm64-v8a-release.apk` - 64-bit ARM (newer phones) ~18MB
- `app-x86_64-release.apk` - Intel/AMD (emulators) ~20MB
- `app-release.apk` - Universal (all devices) ~45MB

**Recommendation**: Share the specific ABI APK for friend's device for smallest size.

### How to Check Friend's Device ABI

Install CPU-Z app or run:
```bash
adb shell getprop ro.product.cpu.abi
```

Common results:
- `armeabi-v7a` → Use `app-armeabi-v7a-release.apk`
- `arm64-v8a` → Use `app-arm64-v8a-release.apk`

## Testing on Lower-End Devices

### Performance Monitoring
```dart
import 'package:flutter/scheduler.dart';

void checkPerformance() {
  SchedulerBinding.instance.addTimingsCallback((timings) {
    for (final timing in timings) {
      if (timing.build > Duration(milliseconds: 16)) {
        print('Frame took ${timing.build.inMilliseconds}ms (target: 16ms)');
      }
    }
  });
}
```

### Memory Monitoring
```dart
import 'dart:developer' as developer;

void checkMemory() {
  developer.inspect(MemoryUsage());
}
```

## Troubleshooting Common Issues

### App Crashes on Startup
**Cause**: OutOfMemory or multidex issue
**Solution**: 
1. Reduce image cache limits further (set to 25 images, 25MB)
2. Ensure multidex is enabled in `build.gradle.kts`
3. Clear app data and reinstall

### Slow Performance
**Cause**: Too many widgets rebuilding
**Solution**:
1. Check for unnecessary `setState()` calls
2. Use `const` constructors where possible
3. Implement `RepaintBoundary` for complex widgets

### Large APK Size
**Cause**: Universal APK includes all architectures
**Solution**: Use `--split-per-abi` flag and share specific APK

## Firebase Performance (Optional Enhancement)

To monitor real-world performance:

1. Add Firebase Performance to `pubspec.yaml`:
```yaml
dependencies:
  firebase_performance: ^0.9.4
```

2. Track custom metrics:
```dart
final trace = FirebasePerformance.instance.newTrace('dashboard_load');
await trace.start();
// ... load dashboard ...
await trace.stop();
```

## Expected Performance Metrics

### Target Frame Rate
- **High-end devices**: 60 FPS (16ms per frame)
- **Mid-range devices**: 60 FPS (16ms per frame)
- **Low-end devices**: 30-45 FPS (22-33ms per frame) ✓ Acceptable

### Memory Usage
- **Idle**: 50-80 MB
- **Active use**: 80-120 MB
- **Peak**: <150 MB (Android kills apps >150MB on low-RAM devices)

### APK Size
- **Split APK**: 15-20 MB ✓ Excellent
- **Universal APK**: 40-50 MB ✓ Good
- **>100 MB**: ❌ Too large for lower-end devices

## Additional Recommendations

### For Friend's Device
1. **Clear storage**: Ensure 500MB+ free space
2. **Close background apps**: Free up RAM
3. **Update Android WebView**: Ensures compatibility
4. **Disable animations**: Settings → Developer Options → Animation scale → 0.5x

### For Future Updates
- Use `flutter pub outdated` to keep dependencies current
- Test on actual low-end device, not just emulator
- Monitor Firebase Crashlytics for device-specific crashes
- Consider adding "Lite Mode" toggle in settings for ultra-low-end devices

## Checklist Before Release

- [ ] Test on Android 5.0 device (or emulator)
- [ ] Test on 1GB RAM device
- [ ] Check APK size (<20MB per ABI)
- [ ] Verify no memory leaks (use DevTools)
- [ ] Test on poor network (throttle to 2G)
- [ ] Verify offline functionality
- [ ] Test Firebase notifications
- [ ] Check ProGuard rules don't break features

---

**Last Updated**: 2026-07-17
**App Version**: 1.0.0+1
**Min Android**: 5.0 (API 21)
**Target Android**: 14.0 (API 34)
