# Kitchentory App Icon Specifications

## Design Guidelines

### Brand Colors
- **Primary Blue**: #2563eb (RGB: 37, 99, 235)
- **Green Accent**: #10B981 (RGB: 16, 185, 129)  
- **White**: #FFFFFF
- **Dark Gray**: #1F2937

### Icon Concept
The Kitchentory icon should represent kitchen management and smart organization. Suggested design elements:
- Kitchen utensil silhouettes (fork, spoon, knife)
- Inventory box or container
- Smart/tech element (subtle grid, dots, or geometric pattern)
- Clean, modern design with rounded corners

### Design Principles
- **Simple**: Clear and recognizable at small sizes
- **Memorable**: Distinctive shape and color combination
- **Scalable**: Works from 16x16 to 1024x1024 pixels
- **Professional**: Clean, modern aesthetic
- **App Store Compliant**: Follows platform guidelines

## Required Icon Sizes

### iOS App Store
| Size | Usage | File Name | Notes |
|------|--------|-----------|-------|
| 1024x1024 | App Store listing | icon-1024.png | Required for App Store Connect |
| 180x180 | iPhone 6 Plus, 6s Plus, 7 Plus, 8 Plus, X, XS, XR, 11, 12, 13, 14 | icon-180.png | @3x |
| 167x167 | iPad Pro | icon-167.png | @2x |
| 152x152 | iPad, iPad Air, iPad mini | icon-152.png | @2x |
| 144x144 | iPad | icon-144.png | @2x |
| 120x120 | iPhone 4s, 5, 5c, 5s, 6, 6s, 7, 8 | icon-120.png | @2x |
| 114x114 | iPhone 4, 4S | icon-114.png | @2x |
| 87x87 | iPhone 6s, 7, 8, X, XS, 11, 12 (Settings) | icon-87.png | @3x |
| 80x80 | iPhone 4, 4S, 5, 5c, 5s, 6, 6s, 7, 8 (Settings) | icon-80.png | @2x |
| 76x76 | iPad | icon-76.png | @1x |
| 72x72 | iPad | icon-72.png | @1x |
| 60x60 | iPhone | icon-60.png | @1x |
| 58x58 | iPhone (Settings) | icon-58.png | @2x |
| 57x57 | iPhone | icon-57.png | @1x |
| 40x40 | iPhone, iPad (Settings) | icon-40.png | @1x |
| 29x29 | iPhone, iPad (Settings, Notifications) | icon-29.png | @1x |

### Android Google Play
| Size | Usage | File Name | DPI | Notes |
|------|--------|-----------|-----|-------|
| 512x512 | Google Play Store | icon-512.png | N/A | Required for Google Play Console |
| 192x192 | High-density devices | icon-192.png | xxxhdpi | @4x |
| 144x144 | Extra-high-density devices | icon-144.png | xxhdpi | @3x |
| 96x96 | High-density devices | icon-96.png | xhdpi | @2x |
| 72x72 | Medium-density devices | icon-72.png | hdpi | @1.5x |
| 48x48 | Medium-density devices | icon-48.png | mdpi | @1x |
| 36x36 | Low-density devices | icon-36.png | ldpi | @0.75x |

### Adaptive Icons (Android 8.0+)
- **Foreground**: 108x108dp (432x432px at xxxhdpi)
- **Background**: 108x108dp (432x432px at xxxhdpi)
- **Safe Zone**: 66x66dp (264x264px at xxxhdpi) - critical elements must be within this area

## PWA Icons (Already Created)
These are referenced in `/static/manifest.json`:
- icon-72.png
- icon-96.png  
- icon-128.png
- icon-144.png
- icon-152.png
- icon-192.png
- icon-384.png
- icon-512.png
- icon-maskable-192.png (with safe zone for masking)
- icon-maskable-512.png (with safe zone for masking)

## Creation Tools & Process

### Recommended Tools
1. **Figma** (Free) - Vector design with export presets
2. **Adobe Illustrator** - Professional vector graphics
3. **Sketch** (Mac only) - UI design with icon templates
4. **GIMP** (Free) - Raster graphics editor
5. **Online Tools**:
   - AppIcon.co - Generates all sizes from one source
   - MakeAppIcon.com - iOS and Android icon generator

### Creation Process
1. **Create Master Icon** at 1024x1024px in vector format
2. **Design Elements**:
   - Use 16px grid system for alignment
   - Maintain 64px padding from edges for iOS
   - Keep important elements within 80% safe area for Android adaptive icons
3. **Export Process**:
   - Export as PNG with transparent background
   - Use bicubic resampling for downsizing
   - Optimize file sizes (aim for <100KB each)
4. **Testing**:
   - Test visibility on light and dark backgrounds
   - Check legibility at smallest sizes (29x29)
   - Verify on actual devices

## File Organization

```
/static/images/icons/
├── ios/
│   ├── icon-1024.png
│   ├── icon-180.png
│   ├── icon-167.png
│   ├── icon-152.png
│   ├── icon-144.png
│   ├── icon-120.png
│   ├── icon-114.png
│   ├── icon-87.png
│   ├── icon-80.png
│   ├── icon-76.png
│   ├── icon-72.png
│   ├── icon-60.png
│   ├── icon-58.png
│   ├── icon-57.png
│   ├── icon-40.png
│   └── icon-29.png
├── android/
│   ├── icon-512.png
│   ├── icon-192.png
│   ├── icon-144.png
│   ├── icon-96.png
│   ├── icon-72.png
│   ├── icon-48.png
│   └── icon-36.png
└── source/
    ├── kitchentory-icon.svg
    ├── kitchentory-icon.fig
    └── export-guide.md
```

## App Store Screenshots

### iOS Requirements
| Device | Size | Orientation | Quantity |
|--------|------|-------------|----------|
| iPhone 6.7" (14 Pro Max, 13 Pro Max, 12 Pro Max) | 1290x2796 | Portrait | 3-10 |
| iPhone 6.5" (11 Pro Max, XS Max) | 1242x2688 | Portrait | 3-10 |
| iPhone 5.5" (8 Plus, 7 Plus, 6s Plus, 6 Plus) | 1242x2208 | Portrait | 3-10 |
| iPad Pro 12.9" | 2048x2732 | Portrait | 3-10 |
| iPad Pro 11" | 1668x2388 | Portrait | 3-10 |

### Android Requirements  
| Device Type | Size | Orientation | Quantity |
|-------------|------|-------------|----------|
| Phone | 1080x1920 | Portrait | 2-8 |
| 7" Tablet | 1024x1600 | Portrait | Optional |
| 10" Tablet | 1280x1920 | Portrait | Optional |

### Screenshot Content Strategy
1. **Hero Shot**: Dashboard with sample data showing key features
2. **Barcode Scanning**: Show camera interface with successful scan
3. **Recipe Discovery**: Display "recipes you can make now" screen
4. **Shopping Lists**: Smart shopping list with organized items
5. **Inventory Management**: Clean inventory list with categories
6. **Premium Features**: Highlight subscription benefits

## Implementation Commands

```bash
# Create directory structure
mkdir -p /Users/macbookair/dev/kitchentory/static/images/icons/{ios,android,source}

# After creating icons, copy to Capacitor projects
npx cap copy ios
npx cap copy android

# Update iOS icons in Xcode (manual process)
# Update Android icons in Android Studio (manual process)
```

## Quality Checklist

- [ ] All required sizes created and optimized
- [ ] Icons display correctly on light and dark backgrounds  
- [ ] Text remains legible at smallest sizes
- [ ] Design is consistent across all sizes
- [ ] File sizes optimized (<100KB each)
- [ ] Files named according to platform conventions
- [ ] Icons tested on actual devices
- [ ] App Store guidelines compliance verified
- [ ] Adaptive icons work correctly on Android 8.0+
- [ ] PWA manifest updated with correct paths

## Next Steps

1. **Design Creation**: Use the specifications above to create the master 1024x1024 icon
2. **Size Generation**: Use tools like AppIcon.co to generate all required sizes
3. **Integration**: Copy icons to appropriate Capacitor directories
4. **Testing**: Test icons on simulators and physical devices
5. **App Store Preparation**: Upload icons during app submission process

## Branding Considerations

The Kitchentory icon should:
- Be instantly recognizable as a kitchen/food app
- Convey organization and smart management
- Use the brand color palette consistently  
- Work well alongside other apps on home screens
- Represent the premium nature of the Pro tier features
- Be culturally neutral and internationally appropriate