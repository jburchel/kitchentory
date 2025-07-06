# Kitchentory Browser Extension

Automatically capture grocery items from online shopping sites and sync them to your Kitchentory inventory.

## Features

🛒 **Auto-Capture**: Automatically detect and capture items as you shop online
📱 **Multi-Site Support**: Works with Instacart, Amazon Fresh, and Walmart Grocery
🔄 **Real-time Sync**: Items sync automatically to your Kitchentory account
📊 **Progress Tracking**: View capture and sync statistics
🎯 **Smart Detection**: Extracts product names, prices, quantities, and categories
🔒 **Secure**: Uses token-based authentication with your Kitchentory account

## Supported Sites

- **Instacart** - All product pages and cart interactions
- **Amazon Fresh** - Fresh grocery items and Whole Foods
- **Walmart Grocery** - Online grocery shopping and pickup orders

## Installation

### From Source

1. Clone or download this repository
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" in the top right
4. Click "Load unpacked" and select the `browser-extension` folder
5. The Kitchentory icon should appear in your extensions toolbar

### Extension Icons

Before installing, you'll need to generate the required icon files:

1. Use the provided `images/icon.svg` file
2. Convert to PNG at these sizes:
   - `icon-16.png` - 16x16 pixels
   - `icon-32.png` - 32x32 pixels  
   - `icon-48.png` - 48x48 pixels
   - `icon-128.png` - 128x128 pixels
3. Place the PNG files in the `images/` directory

## Setup

1. **Install the extension** following the steps above
2. **Click the Kitchentory icon** in your browser toolbar
3. **Enter your Kitchentory server URL** (e.g., `https://your-kitchentory.com` or `http://localhost:8000` for development)
4. **Log in** with your Kitchentory email and password
5. **Enable auto-capture** using the toggle switch

## Usage

### Automatic Capture

When auto-capture is enabled, the extension will automatically:

- Detect when you add items to your cart
- Extract product information (name, brand, price, quantity)
- Show a notification when items are captured
- Sync items to your Kitchentory inventory in the background

### Manual Control

You can also:

- **Toggle auto-capture** on/off using the floating button on shopping sites
- **Manually sync** captured items using the popup
- **View statistics** for captured and synced items
- **Manage settings** through the extension popup

### Visual Indicators

- **Green shopping cart icon**: Auto-capture is active
- **Red shopping cart icon**: Auto-capture is disabled
- **Badge number**: Shows unsynced items count
- **Notifications**: Appear when items are captured

## Technical Details

### Architecture

The extension consists of:

- **Background Service Worker** (`background.js`): Handles authentication, sync, and storage
- **Content Scripts** (`content.js`): Site-specific product capture logic
- **Popup Interface** (`popup.html/js`): User controls and status display
- **API Service** (`api-service.js`): Communication with Kitchentory backend

### Data Flow

1. **Capture**: Content script detects shopping actions
2. **Extract**: Product data is extracted and normalized
3. **Store**: Items are temporarily stored in extension storage
4. **Sync**: Background worker syncs items to Kitchentory API
5. **Confirm**: Success/failure status is displayed to user

### Data Normalization

The extension automatically:

- **Cleans product names** (removes brand prefixes, size suffixes)
- **Standardizes units** (oz, lb, gal, count, etc.)
- **Infers categories** (Produce, Dairy, Meat, etc.)
- **Validates quantities** and prices
- **Sanitizes data** for security

### Site-Specific Handlers

Each supported site has custom logic for:

- **Product detection** using CSS selectors
- **Data extraction** from various page layouts
- **Cart monitoring** for real-time updates
- **Quantity changes** and product variations

## API Compatibility

The extension works with Kitchentory's REST API:

- `POST /api/auth/login/` - Authentication
- `POST /api/inventory/items/bulk_add/` - Bulk item creation
- `GET /api/auth/user/` - User information
- `POST /api/auth/logout/` - Logout

### Data Format

Items are sent to the API in this format:

```json
{
  "items": [
    {
      "name": "Organic Bananas",
      "brand": "Fresh Market",
      "quantity": 1.5,
      "unit": "lb",
      "price": 2.99,
      "category": "Produce",
      "image_url": "https://...",
      "notes": "Captured from instacart.com"
    }
  ]
}
```

## Configuration

### Server URL

The extension supports both production and development Kitchentory instances:

- **Production**: `https://your-kitchentory-domain.com`
- **Development**: `http://localhost:8000`
- **Railway**: `https://your-app-name.up.railway.app`

### Auto-Capture Settings

- **Enabled**: Items are captured automatically as you shop
- **Disabled**: Only manual capture through the popup
- **Debounced Sync**: Prevents excessive API calls during shopping

### Storage

The extension stores:

- **Authentication tokens** (encrypted in Chrome storage)
- **Captured items** (temporarily until synced)
- **User preferences** (auto-capture, server URL)
- **Statistics** (capture/sync counts)

## Privacy & Security

### Data Collection

The extension only captures:

- Product information from supported grocery sites
- Your shopping cart interactions
- Sync statistics for the popup display

### Data Storage

- **Local only**: All data is stored locally in your browser
- **No tracking**: No analytics or user behavior tracking
- **Secure transmission**: All API calls use HTTPS
- **Token-based auth**: No passwords stored locally

### Permissions

The extension requests minimal permissions:

- **activeTab**: Access current shopping site
- **storage**: Store settings and captured items
- **scripting**: Inject capture logic on shopping sites
- **host_permissions**: Only for supported grocery sites

## Troubleshooting

### Extension Not Working

1. **Check site support** - Only works on Instacart, Amazon Fresh, and Walmart
2. **Reload the page** - Content scripts need a fresh page load
3. **Check auto-capture** - Toggle must be enabled
4. **Verify login** - Token may have expired

### Items Not Syncing

1. **Check internet connection**
2. **Verify server URL** in popup settings
3. **Re-authenticate** if token expired
4. **Check API logs** in browser console (F12)

### Missing Product Information

1. **Site layout changes** - Retailers update their HTML frequently
2. **JavaScript disabled** - Extension requires JS to function
3. **Ad blockers** - May interfere with product detection

### Performance Issues

1. **Too many items** - Bulk sync is limited to 100 items
2. **Slow network** - Sync will retry automatically
3. **High CPU usage** - Disable auto-capture temporarily

## Development

### Local Development

1. **Clone the repository**
2. **Load extension** in Chrome developer mode
3. **Set server URL** to `http://localhost:8000`
4. **Start Kitchentory backend** locally
5. **Test on supported sites**

### Adding New Sites

To add support for additional grocery sites:

1. **Add hostname** to `manifest.json` permissions
2. **Create site handler** in `content.js`
3. **Define CSS selectors** for product detection
4. **Test product extraction** logic
5. **Update documentation**

### Building for Production

1. **Generate extension icons** from SVG
2. **Update manifest** with production permissions
3. **Test on all supported sites**
4. **Package for Chrome Web Store**

## Support

### Getting Help

- **Documentation**: Check the main Kitchentory docs
- **Issues**: Report bugs on GitHub
- **Features**: Request enhancements via GitHub issues

### Common Issues

- **Authentication errors**: Check server URL and credentials
- **Missing items**: Verify site compatibility and page reload
- **Sync failures**: Check network connection and API status

## Changelog

### Version 1.0.0

- ✅ **Initial release** with Instacart, Amazon Fresh, and Walmart support
- ✅ **Auto-capture functionality** with real-time detection
- ✅ **Secure authentication** with token management
- ✅ **Bulk sync** with error handling and retry logic
- ✅ **Product normalization** for consistent data quality
- ✅ **Popup interface** with statistics and controls

### Planned Features

- 📋 **Manual item editing** before sync
- 🏪 **More grocery sites** (Target, Kroger, Safeway)
- 📄 **Receipt scanning** via OCR
- 📊 **Usage analytics** and insights
- 🔄 **Background sync** improvements
- 📱 **Mobile browser** support

## License

This browser extension is part of the Kitchentory project. See the main repository for license information.