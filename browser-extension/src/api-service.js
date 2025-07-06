/**
 * Kitchentory API Service
 * Handles all communication with the Kitchentory backend
 */

class KitchentoryAPI {
  constructor() {
    this.baseUrl = null;
    this.token = null;
    this.isAuthenticated = false;
  }

  /**
   * Initialize API service with authentication data
   */
  async init() {
    const auth = await chrome.storage.local.get(['auth']);
    if (auth.auth && auth.auth.token) {
      this.baseUrl = auth.auth.serverUrl;
      this.token = auth.auth.token;
      this.isAuthenticated = true;
    }
  }

  /**
   * Make authenticated API request
   */
  async request(endpoint, options = {}) {
    if (!this.isAuthenticated) {
      throw new Error('Not authenticated');
    }

    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Token ${this.token}`,
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      
      if (response.status === 401) {
        // Token expired, clear auth
        await this.clearAuth();
        throw new Error('Authentication expired. Please log in again.');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Network error. Check your internet connection.');
      }
      throw error;
    }
  }

  /**
   * Login user and store authentication
   */
  async login(serverUrl, email, password) {
    const response = await fetch(`${serverUrl}/api/auth/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Invalid email or password');
      } else if (response.status === 404) {
        throw new Error('Server not found. Check your Kitchentory URL.');
      } else {
        throw new Error(`Connection failed (${response.status})`);
      }
    }

    const data = await response.json();
    
    // Store authentication data
    const authData = {
      token: data.token,
      email: email,
      serverUrl: serverUrl,
      user: data.user
    };

    await chrome.storage.local.set({ auth: authData });
    
    this.baseUrl = serverUrl;
    this.token = data.token;
    this.isAuthenticated = true;

    return authData;
  }

  /**
   * Logout and clear authentication
   */
  async logout() {
    if (this.isAuthenticated) {
      try {
        await this.request('/api/auth/logout/', { method: 'POST' });
      } catch (error) {
        // Ignore logout errors
        console.warn('Logout request failed:', error);
      }
    }

    await this.clearAuth();
  }

  /**
   * Clear stored authentication
   */
  async clearAuth() {
    await chrome.storage.local.remove(['auth']);
    this.baseUrl = null;
    this.token = null;
    this.isAuthenticated = false;
  }

  /**
   * Get current user information
   */
  async getUserInfo() {
    return await this.request('/api/auth/user/');
  }

  /**
   * Bulk add items to inventory
   */
  async bulkAddItems(items) {
    const normalizedItems = items.map(item => this.normalizeItem(item));
    
    return await this.request('/api/inventory/items/bulk_add_ext/', {
      method: 'POST',
      body: JSON.stringify({ items: normalizedItems })
    });
  }

  /**
   * Add single item to inventory
   */
  async addItem(item) {
    const normalizedItem = this.normalizeItem(item);
    
    return await this.request('/api/inventory/items/quick_add/', {
      method: 'POST',
      body: JSON.stringify(normalizedItem)
    });
  }

  /**
   * Search for products by barcode
   */
  async searchByBarcode(barcode) {
    return await this.request(`/api/inventory/products/by_barcode/?barcode=${encodeURIComponent(barcode)}`);
  }

  /**
   * Search for products by name
   */
  async searchProducts(query) {
    return await this.request(`/api/inventory/products/search/?q=${encodeURIComponent(query)}`);
  }

  /**
   * Normalize captured item data for API
   */
  normalizeItem(item) {
    return {
      name: this.sanitizeString(item.name),
      brand: this.sanitizeString(item.brand) || '',
      quantity: Math.max(parseFloat(item.quantity) || 1, 0.01), // Minimum 0.01
      unit: this.normalizeUnit(item.unit),
      price: item.price ? Math.max(parseFloat(item.price), 0) : null,
      barcode: this.sanitizeString(item.barcode) || '',
      category: this.sanitizeString(item.category) || 'Other',
      image_url: this.sanitizeUrl(item.imageUrl) || '',
      notes: `Captured from ${item.sourceSite || 'browser extension'}`,
      // Set default location to fridge (can be updated by user later)
      location: 'fridge'
    };
  }

  /**
   * Normalize unit names to match backend expectations
   */
  normalizeUnit(unit) {
    if (!unit) return 'item';
    
    const unitMap = {
      'item': 'item',
      'items': 'item',
      'each': 'each',
      'ea': 'each',
      'count': 'count',
      'ct': 'count',
      'pack': 'pack',
      'package': 'pack',
      'pkg': 'pack',
      'oz': 'oz',
      'ounce': 'oz',
      'ounces': 'oz',
      'fl oz': 'fl_oz',
      'fluid ounce': 'fl_oz',
      'fluid ounces': 'fl_oz',
      'lb': 'lb',
      'pound': 'lb',
      'pounds': 'lb',
      'lbs': 'lb',
      'kg': 'kg',
      'kilogram': 'kg',
      'kilograms': 'kg',
      'g': 'g',
      'gram': 'g',
      'grams': 'g',
      'gal': 'gal',
      'gallon': 'gal',
      'gallons': 'gal',
      'qt': 'qt',
      'quart': 'qt',
      'quarts': 'qt',
      'pt': 'pt',
      'pint': 'pt',
      'pints': 'pt',
      'cup': 'cup',
      'cups': 'cup',
      'tbsp': 'tbsp',
      'tablespoon': 'tbsp',
      'tablespoons': 'tbsp',
      'tsp': 'tsp',
      'teaspoon': 'tsp',
      'teaspoons': 'tsp',
      'ml': 'ml',
      'milliliter': 'ml',
      'milliliters': 'ml',
      'l': 'l',
      'liter': 'l',
      'liters': 'l'
    };

    const normalized = unit.toLowerCase().trim();
    return unitMap[normalized] || 'item';
  }

  /**
   * Sanitize string inputs
   */
  sanitizeString(str) {
    if (!str || typeof str !== 'string') return '';
    
    return str
      .trim()
      .replace(/[\x00-\x1F\x7F]/g, '') // Remove control characters
      .substring(0, 200); // Limit length
  }

  /**
   * Sanitize URL inputs
   */
  sanitizeUrl(url) {
    if (!url || typeof url !== 'string') return '';
    
    try {
      const parsed = new URL(url);
      // Only allow http/https protocols
      if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
        return url.substring(0, 500); // Limit length
      }
    } catch (e) {
      // Invalid URL
    }
    
    return '';
  }

  /**
   * Get API connection status
   */
  getStatus() {
    return {
      isAuthenticated: this.isAuthenticated,
      baseUrl: this.baseUrl,
      hasToken: !!this.token
    };
  }
}

// Create singleton instance
const kitchentoryAPI = new KitchentoryAPI();

// Initialize on script load
kitchentoryAPI.init().catch(console.error);

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = KitchentoryAPI;
} else if (typeof window !== 'undefined') {
  window.KitchentoryAPI = kitchentoryAPI;
}