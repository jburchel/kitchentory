// Content script for capturing grocery items from websites

class KitchentoryCapture {
  constructor() {
    this.autoCapture = false;
    this.capturedItems = new Set();
    this.siteHandler = null;
    
    this.init();
  }
  
  async init() {
    // Load settings
    const settings = await chrome.storage.local.get(['autoCapture']);
    this.autoCapture = settings.autoCapture || false;
    
    // Listen for messages from background
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.type === 'AUTO_CAPTURE_CHANGED') {
        this.autoCapture = request.enabled;
        if (this.autoCapture) {
          this.startObserving();
        }
      }
    });
    
    // Detect which site we're on and initialize appropriate handler
    const hostname = window.location.hostname;
    
    if (hostname.includes('instacart.com')) {
      this.siteHandler = new InstacartHandler(this);
    } else if (hostname.includes('amazon.com')) {
      this.siteHandler = new AmazonHandler(this);
    } else if (hostname.includes('walmart.com')) {
      this.siteHandler = new WalmartHandler(this);
    }
    
    if (this.siteHandler && this.autoCapture) {
      this.startObserving();
    }
    
    // Add capture button to page
    this.injectCaptureUI();
  }
  
  startObserving() {
    if (this.siteHandler) {
      this.siteHandler.startObserving();
    }
  }
  
  captureItem(item) {
    // Avoid duplicate captures
    const itemKey = `${item.name}-${item.quantity || '1'}`;
    if (this.capturedItems.has(itemKey)) {
      return;
    }
    
    this.capturedItems.add(itemKey);
    
    // Send to background
    chrome.runtime.sendMessage({
      type: 'CAPTURE_ITEM',
      item: {
        name: item.name,
        brand: item.brand || '',
        quantity: item.quantity || 1,
        unit: item.unit || 'item',
        price: item.price || null,
        imageUrl: item.imageUrl || '',
        category: item.category || '',
        barcode: item.barcode || ''
      }
    });
    
    // Show visual feedback
    this.showCaptureNotification(item.name);
  }
  
  showCaptureNotification(itemName) {
    const notification = document.createElement('div');
    notification.className = 'kitchentory-notification';
    notification.textContent = `Captured: ${itemName}`;
    notification.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #10b981;
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      z-index: 9999;
      animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease-out';
      setTimeout(() => notification.remove(), 300);
    }, 2000);
  }
  
  injectCaptureUI() {
    // Add styles
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      
      @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
      
      .kitchentory-capture-btn {
        position: fixed;
        bottom: 80px;
        right: 20px;
        background: #10b981;
        color: white;
        border: none;
        border-radius: 50%;
        width: 56px;
        height: 56px;
        font-size: 24px;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 9998;
        transition: transform 0.2s;
      }
      
      .kitchentory-capture-btn:hover {
        transform: scale(1.1);
      }
      
      .kitchentory-capture-btn.active {
        background: #dc2626;
      }
    `;
    document.head.appendChild(style);
    
    // Add floating button
    const button = document.createElement('button');
    button.className = 'kitchentory-capture-btn';
    button.innerHTML = '🛒';
    button.title = 'Kitchentory: Click to toggle auto-capture';
    
    button.addEventListener('click', () => {
      this.autoCapture = !this.autoCapture;
      button.classList.toggle('active', this.autoCapture);
      chrome.storage.local.set({ autoCapture: this.autoCapture });
      
      if (this.autoCapture) {
        this.startObserving();
        this.showCaptureNotification('Auto-capture enabled');
      } else {
        this.showCaptureNotification('Auto-capture disabled');
      }
    });
    
    if (this.autoCapture) {
      button.classList.add('active');
    }
    
    document.body.appendChild(button);
  }
}

// Site-specific handlers
class InstacartHandler {
  constructor(capture) {
    this.capture = capture;
    this.selectors = {
      // Updated selectors for current Instacart layout
      productCard: '[data-testid="product-tile"], [data-testid="product-card"], .product-tile',
      productName: '[data-testid="product-name"], h2, .product-title',
      productBrand: '[data-testid="brand"], .brand-name, .product-brand',
      productPrice: '[data-testid="price"], .price, .current-price',
      productSize: '[data-testid="size"], [data-testid="product-size"], .size',
      addButton: '[data-testid="add-button"], button[aria-label*="Add"], .add-to-cart',
      cartItem: '[data-testid="cart-item"], .cart-item',
      productImage: 'img[src*="product"], img[alt*="product"], .product-image img'
    };
  }
  
  startObserving() {
    // Watch for add to cart actions with improved selectors
    document.addEventListener('click', (e) => {
      const addButton = e.target.closest(this.selectors.addButton);
      if (addButton) {
        setTimeout(() => this.captureFromButton(addButton), 100);
      }
    });
    
    // Also observe cart updates
    this.observeCart();
    
    // Watch for quantity changes
    this.observeQuantityChanges();
  }
  
  captureFromButton(button) {
    // Try multiple strategies to find product container
    let productCard = button.closest(this.selectors.productCard);
    
    if (!productCard) {
      // Fallback: look for parent containers
      productCard = button.closest('[role="listitem"]') || 
                   button.closest('.product') ||
                   button.closest('[data-product-id]');
    }
    
    if (!productCard) return;
    
    const item = this.extractProductData(productCard);
    
    if (item.name) {
      this.capture.captureItem(item);
    }
  }
  
  extractProductData(container) {
    const name = this.findText(container, this.selectors.productName);
    const brand = this.findText(container, this.selectors.productBrand);
    const sizeText = this.findText(container, this.selectors.productSize);
    
    return {
      name: this.cleanProductName(name),
      brand: this.cleanBrand(brand),
      price: this.extractPrice(container),
      quantity: this.extractQuantity(sizeText),
      unit: this.extractUnit(sizeText),
      imageUrl: this.extractImage(container),
      category: this.inferCategory(name)
    };
  }
  
  findText(container, selector) {
    const element = container.querySelector(selector);
    return element?.textContent?.trim() || '';
  }
  
  cleanProductName(name) {
    // Remove common prefixes/suffixes and clean up
    return name
      .replace(/^(Organic\s+|Fresh\s+|Store Brand\s+)/i, '')
      .replace(/\s+\(\d+.*?\)$/, '') // Remove size in parentheses
      .trim();
  }
  
  cleanBrand(brand) {
    // Clean up brand names
    return brand
      .replace(/^Brand:\s*/i, '')
      .replace(/^by\s+/i, '')
      .trim();
  }
  
  extractImage(container) {
    const img = container.querySelector(this.selectors.productImage);
    if (img?.src && !img.src.includes('data:')) {
      return img.src;
    }
    return '';
  }
  
  inferCategory(name) {
    const lowerName = name.toLowerCase();
    
    if (lowerName.includes('milk') || lowerName.includes('cheese') || lowerName.includes('yogurt')) {
      return 'Dairy';
    } else if (lowerName.includes('chicken') || lowerName.includes('beef') || lowerName.includes('pork')) {
      return 'Meat & Seafood';
    } else if (lowerName.includes('apple') || lowerName.includes('banana') || lowerName.includes('fruit')) {
      return 'Produce';
    } else if (lowerName.includes('bread') || lowerName.includes('pasta') || lowerName.includes('rice')) {
      return 'Pantry';
    } else if (lowerName.includes('frozen')) {
      return 'Frozen';
    }
    
    return 'Other';
  }
  
  observeQuantityChanges() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList' || mutation.type === 'attributes') {
          // Check for quantity selector updates
          const qtyInputs = document.querySelectorAll('input[type="number"], .quantity-input');
          qtyInputs.forEach(input => {
            if (input.dataset.observed !== 'true') {
              input.addEventListener('change', () => this.handleQuantityChange(input));
              input.dataset.observed = 'true';
            }
          });
        }
      });
    });
    
    observer.observe(document.body, { childList: true, subtree: true, attributes: true });
  }
  
  handleQuantityChange(input) {
    // When quantity changes, capture the updated item
    const productCard = input.closest(this.selectors.productCard);
    if (productCard) {
      const item = this.extractProductData(productCard);
      if (item.name && input.value > 0) {
        item.quantity = parseFloat(input.value) || 1;
        this.capture.captureItem(item);
      }
    }
  }
  
  observeCart() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.addedNodes.length > 0) {
          // Check if items were added to cart
          const cartItems = document.querySelectorAll('[data-testid*="cart-item"]');
          cartItems.forEach(item => this.captureCartItem(item));
        }
      });
    });
    
    // Start observing cart container
    const cartContainer = document.querySelector('[data-testid*="cart"]');
    if (cartContainer) {
      observer.observe(cartContainer, { childList: true, subtree: true });
    }
  }
  
  captureCartItem(element) {
    // Extract item details from cart
    const item = {
      name: element.querySelector('[data-testid*="item-name"]')?.textContent || '',
      quantity: element.querySelector('[data-testid*="quantity"]')?.textContent || '1',
      price: this.extractPrice(element)
    };
    
    if (item.name) {
      this.capture.captureItem(item);
    }
  }
  
  extractPrice(container) {
    const priceElement = container.querySelector(this.selectors.productPrice);
    if (!priceElement) return null;
    
    const priceText = priceElement.textContent || '';
    const match = priceText.match(/\$?([\d,]+\.?\d*)/);
    return match ? parseFloat(match[1].replace(',', '')) : null;
  }
  
  extractQuantity(sizeText) {
    if (!sizeText) return 1;
    
    // Look for quantity patterns like "2 x 16 oz", "12 count", "1.5 lb"
    const patterns = [
      /(\d+\.?\d*)\s*x\s*[\d.]+/i,  // "2 x 16 oz" -> 2
      /(\d+\.?\d*)\s*(count|pack|ct)/i,  // "12 count" -> 12
      /(\d+\.?\d*)\s*(lb|oz|gal|qt|pt)/i,  // "1.5 lb" -> 1.5
      /(\d+\.?\d*)/  // fallback to first number
    ];
    
    for (const pattern of patterns) {
      const match = sizeText.match(pattern);
      if (match) {
        return parseFloat(match[1]) || 1;
      }
    }
    
    return 1;
  }
  
  extractUnit(sizeText) {
    if (!sizeText) return 'item';
    
    const unitMap = {
      'oz': 'oz',
      'ounce': 'oz',
      'ounces': 'oz',
      'fl oz': 'fl oz',
      'fluid ounce': 'fl oz',
      'lb': 'lb',
      'pound': 'lb',
      'pounds': 'lb',
      'gal': 'gal',
      'gallon': 'gal',
      'gallons': 'gal',
      'qt': 'qt',
      'quart': 'qt',
      'quarts': 'qt',
      'pt': 'pt',
      'pint': 'pt',
      'pints': 'pt',
      'count': 'count',
      'ct': 'count',
      'pack': 'pack',
      'pkg': 'pack',
      'package': 'pack',
      'each': 'each',
      'ea': 'each'
    };
    
    const lowerSize = sizeText.toLowerCase();
    
    for (const [pattern, unit] of Object.entries(unitMap)) {
      if (lowerSize.includes(pattern)) {
        return unit;
      }
    }
    
    return 'item';
  }
}

class AmazonHandler {
  constructor(capture) {
    this.capture = capture;
    this.selectors = {
      // Amazon Fresh selectors
      freshProductCard: '[data-asin], [data-csa-c-item-id], .product-card',
      freshAddButton: '[data-action*="add"], button[aria-label*="Add"], .add-button',
      freshProductName: '[data-cy="product-title"], .product-title, .product-name',
      freshProductPrice: '[data-cy="price"], .price, .product-price',
      freshProductSize: '[data-cy="product-size"], .size, .product-details',
      freshProductImage: '.product-image img, img[alt*="product"]',
      
      // Regular Amazon selectors
      productTitle: '#productTitle, .product-title',
      productPrice: '.a-price-whole, #priceblock_dealprice, #priceblock_ourprice, .a-price',
      productImage: '#landingImage, #imgTagWrapperId img, .main-image img',
      addToCartButton: '#add-to-cart-button, [data-action="add-to-cart"]',
      brandInfo: '#bylineInfo, .brand-info'
    };
  }
  
  startObserving() {
    // Detect which Amazon service we're on
    const hostname = window.location.hostname;
    const isFresh = window.location.pathname.includes('/fresh/') || 
                   document.querySelector('[data-cy="fresh"]') ||
                   hostname.includes('fresh');
    
    if (isFresh) {
      this.observeFresh();
    } else {
      this.observeRegularAmazon();
    }
  }
  
  observeFresh() {
    // Watch for Fresh/Whole Foods add buttons
    document.addEventListener('click', (e) => {
      const addButton = e.target.closest(this.selectors.freshAddButton);
      if (addButton) {
        setTimeout(() => this.captureFreshItem(addButton), 150);
      }
    });
    
    // Watch for cart updates in Fresh
    this.observeFreshCart();
  }
  
  observeRegularAmazon() {
    // Watch for regular Amazon add to cart
    document.addEventListener('click', (e) => {
      const addButton = e.target.closest(this.selectors.addToCartButton);
      if (addButton) {
        setTimeout(() => this.captureCurrentProduct(), 150);
      }
    });
  }
  
  observeFreshCart() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.addedNodes.length > 0) {
          // Look for cart item additions
          const cartItems = document.querySelectorAll('[data-cy="cart-item"], .cart-item');
          cartItems.forEach(item => {
            if (!item.dataset.captured) {
              this.captureFreshCartItem(item);
              item.dataset.captured = 'true';
            }
          });
        }
      });
    });
    
    const cartContainer = document.querySelector('[data-cy="cart"], .cart-container');
    if (cartContainer) {
      observer.observe(cartContainer, { childList: true, subtree: true });
    }
  }
  
  captureCurrentProduct() {
    const title = this.findText(document, this.selectors.productTitle);
    const brand = this.findText(document, this.selectors.brandInfo);
    
    const item = {
      name: this.cleanProductName(title),
      brand: this.cleanBrand(brand),
      price: this.extractAmazonPrice(),
      imageUrl: this.extractImage(document, this.selectors.productImage),
      category: this.inferCategory(title)
    };
    
    if (item.name) {
      this.capture.captureItem(item);
    }
  }
  
  captureFreshItem(button) {
    let productCard = button.closest(this.selectors.freshProductCard);
    
    if (!productCard) {
      // Fallback: traverse up to find product container
      productCard = button.closest('[role="listitem"]') || 
                   button.closest('.product') ||
                   button.closest('[data-product-id]');
    }
    
    if (!productCard) return;
    
    const item = this.extractFreshProductData(productCard);
    
    if (item.name) {
      this.capture.captureItem(item);
    }
  }
  
  captureFreshCartItem(cartItem) {
    const item = this.extractFreshProductData(cartItem);
    
    if (item.name) {
      this.capture.captureItem(item);
    }
  }
  
  extractFreshProductData(container) {
    const name = this.findText(container, this.selectors.freshProductName);
    const sizeText = this.findText(container, this.selectors.freshProductSize);
    
    return {
      name: this.cleanProductName(name),
      brand: this.extractFreshBrand(container),
      price: this.extractFreshPrice(container),
      quantity: this.extractQuantity(sizeText),
      unit: this.extractUnit(sizeText),
      imageUrl: this.extractImage(container, this.selectors.freshProductImage),
      category: this.inferCategory(name)
    };
  }
  
  findText(container, selector) {
    const element = container.querySelector(selector);
    return element?.textContent?.trim() || '';
  }
  
  cleanProductName(name) {
    return name
      .replace(/^(Amazon Brand\s+|365 by Whole Foods Market\s+|Fresh Brand\s+)/i, '')
      .replace(/\s+\(\d+.*?\)$/, '') // Remove size in parentheses
      .trim();
  }
  
  cleanBrand(brand) {
    return brand
      .replace(/^(Brand:\s*|Visit the\s*|by\s+)/i, '')
      .replace(/\s+Store$/, '')
      .trim();
  }
  
  extractImage(container, selector) {
    const img = container.querySelector(selector);
    if (img?.src && !img.src.includes('data:') && !img.src.includes('blank')) {
      return img.src;
    }
    return '';
  }
  
  extractFreshBrand(container) {
    // Look for brand in various places
    const brandSelectors = [
      '[data-cy="brand"]',
      '.brand',
      '.product-brand',
      '.product-details .brand'
    ];
    
    for (const selector of brandSelectors) {
      const element = container.querySelector(selector);
      if (element) {
        return this.cleanBrand(element.textContent);
      }
    }
    
    return '';
  }
  
  inferCategory(name) {
    const lowerName = name.toLowerCase();
    
    const categoryMap = {
      'Produce': ['apple', 'banana', 'orange', 'lettuce', 'tomato', 'carrot', 'onion', 'potato', 'fruit', 'vegetable'],
      'Dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'dairy'],
      'Meat & Seafood': ['chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'shrimp', 'meat'],
      'Pantry': ['bread', 'pasta', 'rice', 'cereal', 'beans', 'sauce', 'oil', 'vinegar'],
      'Frozen': ['frozen', 'ice cream', 'frozen fruit', 'frozen vegetable'],
      'Beverages': ['water', 'juice', 'soda', 'coffee', 'tea', 'drink'],
      'Snacks': ['chips', 'crackers', 'nuts', 'candy', 'chocolate', 'cookies']
    };
    
    for (const [category, keywords] of Object.entries(categoryMap)) {
      if (keywords.some(keyword => lowerName.includes(keyword))) {
        return category;
      }
    }
    
    return 'Other';
  }
  
  extractQuantity(sizeText) {
    if (!sizeText) return 1;
    
    const patterns = [
      /(\d+\.?\d*)\s*pack/i,
      /(\d+\.?\d*)\s*count/i,
      /(\d+\.?\d*)\s*ct/i,
      /(\d+\.?\d*)\s*(lb|oz|gal|qt|pt)/i,
      /(\d+\.?\d*)/
    ];
    
    for (const pattern of patterns) {
      const match = sizeText.match(pattern);
      if (match) {
        return parseFloat(match[1]) || 1;
      }
    }
    
    return 1;
  }
  
  extractUnit(sizeText) {
    if (!sizeText) return 'item';
    
    const lowerSize = sizeText.toLowerCase();
    
    if (lowerSize.includes('fl oz') || lowerSize.includes('fluid ounce')) return 'fl oz';
    if (lowerSize.includes('oz') || lowerSize.includes('ounce')) return 'oz';
    if (lowerSize.includes('lb') || lowerSize.includes('pound')) return 'lb';
    if (lowerSize.includes('gal') || lowerSize.includes('gallon')) return 'gal';
    if (lowerSize.includes('qt') || lowerSize.includes('quart')) return 'qt';
    if (lowerSize.includes('pt') || lowerSize.includes('pint')) return 'pt';
    if (lowerSize.includes('count') || lowerSize.includes('ct')) return 'count';
    if (lowerSize.includes('pack') || lowerSize.includes('pkg')) return 'pack';
    if (lowerSize.includes('each') || lowerSize.includes('ea')) return 'each';
    
    return 'item';
  }
  
  extractAmazonPrice() {
    const priceSelectors = [
      '.a-price-whole',
      '#priceblock_dealprice',
      '#priceblock_ourprice',
      '.a-price .a-offscreen',
      '.a-price-range',
      '[data-automation-id="price"]'
    ];
    
    for (const selector of priceSelectors) {
      const element = document.querySelector(selector);
      if (element) {
        const priceText = element.textContent || '';
        const match = priceText.match(/\$?([\d,]+\.?\d*)/);
        if (match) {
          return parseFloat(match[1].replace(',', ''));
        }
      }
    }
    
    return null;
  }
  
  extractFreshPrice(container) {
    const priceSelectors = [
      '[data-cy="price"]',
      '.price',
      '.product-price',
      '[data-testid="price"]',
      '.current-price'
    ];
    
    for (const selector of priceSelectors) {
      const element = container.querySelector(selector);
      if (element) {
        const priceText = element.textContent || '';
        const match = priceText.match(/\$?([\d,]+\.?\d*)/);
        if (match) {
          return parseFloat(match[1].replace(',', ''));
        }
      }
    }
    
    return null;
  }
}

class WalmartHandler {
  constructor(capture) {
    this.capture = capture;
    this.selectors = {
      // Product cards and containers
      productCard: '[data-item-id], [data-tl-id*="ProductTile"], .product-tile, [data-testid="item-stack"]',
      productName: '[data-automation-id="product-title"], h3, .product-title, [data-testid="product-title"]',
      productBrand: '[data-automation-id="brand"], .brand, .product-brand',
      productPrice: '[data-automation-id="price"], .price, [data-testid="price"], .current-price',
      productSize: '[data-automation-id="size"], .size, .product-size',
      addButton: '[data-automation-id*="add"], button[aria-label*="Add"], .add-to-cart',
      productImage: 'img[data-testid*="product"], img[alt*="product"], .product-image img',
      
      // Product detail page
      detailTitle: 'h1[data-automation-id="product-title"], h1[itemprop="name"], .product-title h1',
      detailBrand: '[itemprop="brand"], [data-automation-id="brand"], .brand-name',
      detailPrice: '[data-automation-id="price"], [itemprop="price"], .price-now',
      detailImage: '[data-testid="hero-image"] img, .hero-image img, .main-image img',
      detailSize: '[data-automation-id="size"], .size-info, .product-size'
    };
  }
  
  startObserving() {
    // Watch for add to cart buttons
    document.addEventListener('click', (e) => {
      const addButton = e.target.closest(this.selectors.addButton);
      if (addButton) {
        setTimeout(() => this.captureFromButton(addButton), 100);
      }
    });
    
    // Watch for quantity changes in product tiles
    this.observeQuantityChanges();
  }
  
  captureFromButton(button) {
    // Try to find product container
    let productCard = button.closest(this.selectors.productCard);
    
    if (!productCard) {
      // Fallback: look for parent containers
      productCard = button.closest('[role="listitem"]') || 
                   button.closest('.product') ||
                   button.closest('[data-product-id]');
    }
    
    if (productCard) {
      const item = this.extractProductData(productCard);
      if (item.name) {
        this.capture.captureItem(item);
      }
    } else {
      // Likely a product detail page
      this.captureProductPage();
    }
  }
  
  extractProductData(container) {
    const name = this.findText(container, this.selectors.productName);
    const brand = this.findText(container, this.selectors.productBrand);
    const sizeText = this.findText(container, this.selectors.productSize);
    
    return {
      name: this.cleanProductName(name),
      brand: this.cleanBrand(brand),
      price: this.extractPrice(container, this.selectors.productPrice),
      quantity: this.extractQuantity(sizeText),
      unit: this.extractUnit(sizeText),
      imageUrl: this.extractImage(container, this.selectors.productImage),
      category: this.inferCategory(name)
    };
  }
  
  captureProductPage() {
    const name = this.findText(document, this.selectors.detailTitle);
    const brand = this.findText(document, this.selectors.detailBrand);
    const sizeText = this.findText(document, this.selectors.detailSize);
    
    const item = {
      name: this.cleanProductName(name),
      brand: this.cleanBrand(brand),
      price: this.extractPrice(document, this.selectors.detailPrice),
      quantity: this.extractQuantity(sizeText),
      unit: this.extractUnit(sizeText),
      imageUrl: this.extractImage(document, this.selectors.detailImage),
      category: this.inferCategory(name)
    };
    
    if (item.name) {
      this.capture.captureItem(item);
    }
  }
  
  findText(container, selector) {
    const element = container.querySelector(selector);
    return element?.textContent?.trim() || '';
  }
  
  cleanProductName(name) {
    return name
      .replace(/^(Great Value\s+|Equate\s+|Parent's Choice\s+|Marketside\s+)/i, '')
      .replace(/\s+\(\d+.*?\)$/, '') // Remove size in parentheses
      .trim();
  }
  
  cleanBrand(brand) {
    return brand
      .replace(/^Brand:\s*/i, '')
      .replace(/^by\s+/i, '')
      .trim();
  }
  
  extractImage(container, selector) {
    const img = container.querySelector(selector);
    if (img?.src && !img.src.includes('data:') && !img.src.includes('placeholder')) {
      return img.src;
    }
    return '';
  }
  
  observeQuantityChanges() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList' || mutation.type === 'attributes') {
          // Check for quantity input changes
          const qtyInputs = document.querySelectorAll('input[type="number"], [data-automation-id*="quantity"]');
          qtyInputs.forEach(input => {
            if (input.dataset.observed !== 'true') {
              input.addEventListener('change', () => this.handleQuantityChange(input));
              input.dataset.observed = 'true';
            }
          });
        }
      });
    });
    
    observer.observe(document.body, { childList: true, subtree: true, attributes: true });
  }
  
  handleQuantityChange(input) {
    const productCard = input.closest(this.selectors.productCard);
    if (productCard) {
      const item = this.extractProductData(productCard);
      if (item.name && input.value > 0) {
        item.quantity = parseFloat(input.value) || 1;
        this.capture.captureItem(item);
      }
    }
  }
  
  inferCategory(name) {
    const lowerName = name.toLowerCase();
    
    const categoryMap = {
      'Produce': ['apple', 'banana', 'orange', 'lettuce', 'tomato', 'carrot', 'onion', 'potato', 'fruit', 'vegetable', 'organic'],
      'Dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'dairy', 'eggs'],
      'Meat & Seafood': ['chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'shrimp', 'meat', 'ground beef'],
      'Pantry': ['bread', 'pasta', 'rice', 'cereal', 'beans', 'sauce', 'oil', 'vinegar', 'flour', 'sugar'],
      'Frozen': ['frozen', 'ice cream', 'frozen fruit', 'frozen vegetable', 'frozen meal'],
      'Beverages': ['water', 'juice', 'soda', 'coffee', 'tea', 'drink', 'beverage'],
      'Snacks': ['chips', 'crackers', 'nuts', 'candy', 'chocolate', 'cookies', 'snack']
    };
    
    for (const [category, keywords] of Object.entries(categoryMap)) {
      if (keywords.some(keyword => lowerName.includes(keyword))) {
        return category;
      }
    }
    
    return 'Other';
  }
  
  extractQuantity(sizeText) {
    if (!sizeText) return 1;
    
    const patterns = [
      /(\d+\.?\d*)\s*pack/i,
      /(\d+\.?\d*)\s*count/i,
      /(\d+\.?\d*)\s*ct/i,
      /(\d+\.?\d*)\s*(lb|oz|gal|qt|pt)/i,
      /(\d+\.?\d*)/
    ];
    
    for (const pattern of patterns) {
      const match = sizeText.match(pattern);
      if (match) {
        return parseFloat(match[1]) || 1;
      }
    }
    
    return 1;
  }
  
  extractUnit(sizeText) {
    if (!sizeText) return 'item';
    
    const lowerSize = sizeText.toLowerCase();
    
    if (lowerSize.includes('fl oz') || lowerSize.includes('fluid ounce')) return 'fl oz';
    if (lowerSize.includes('oz') || lowerSize.includes('ounce')) return 'oz';
    if (lowerSize.includes('lb') || lowerSize.includes('pound')) return 'lb';
    if (lowerSize.includes('gal') || lowerSize.includes('gallon')) return 'gal';
    if (lowerSize.includes('qt') || lowerSize.includes('quart')) return 'qt';
    if (lowerSize.includes('pt') || lowerSize.includes('pint')) return 'pt';
    if (lowerSize.includes('count') || lowerSize.includes('ct')) return 'count';
    if (lowerSize.includes('pack') || lowerSize.includes('pkg')) return 'pack';
    if (lowerSize.includes('each') || lowerSize.includes('ea')) return 'each';
    
    return 'item';
  }
  
  extractPrice(container, selector) {
    const priceSelectors = [
      selector,
      '[data-automation-id="price"]',
      '.price-characteristic',
      '.current-price',
      '[data-testid="price"]',
      '.price'
    ];
    
    for (const priceSelector of priceSelectors) {
      const element = container.querySelector(priceSelector);
      if (element) {
        const priceText = element.textContent || '';
        const match = priceText.match(/\$?([\d,]+\.?\d*)/);
        if (match) {
          return parseFloat(match[1].replace(',', ''));
        }
      }
    }
    
    return null;
  }
}

// Initialize capture when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new KitchentoryCapture());
} else {
  new KitchentoryCapture();
}console.log('Kitchentory extension debug check');
