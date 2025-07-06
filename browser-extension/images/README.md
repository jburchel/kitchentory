# Extension Icons

This directory should contain the following icons:

- `icon-16.png` - 16x16 pixels
- `icon-32.png` - 32x32 pixels  
- `icon-48.png` - 48x48 pixels
- `icon-128.png` - 128x128 pixels

## Converting SVG to PNG

Use the provided `icon.svg` file to generate the required PNG icons:

```bash
# Using ImageMagick (if available)
convert icon.svg -resize 16x16 icon-16.png
convert icon.svg -resize 32x32 icon-32.png
convert icon.svg -resize 48x48 icon-48.png
convert icon.svg -resize 128x128 icon-128.png

# Or use online converters like:
# - https://convertio.co/svg-png/
# - https://cloudconvert.com/svg-to-png
```

The icons represent a shopping cart/inventory list with the Kitchentory brand colors (#10B981).