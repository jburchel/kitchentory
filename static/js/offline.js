// Offline functionality for Kitchentory
class OfflineManager {
  constructor() {
    this.isOnline = navigator.onLine;
    this.dbName = 'KitchentoryOffline';
    this.dbVersion = 1;
    this.db = null;
    
    this.initializeDB();
    this.setupEventListeners();
  }

  async initializeDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        
        // Create object stores
        if (!db.objectStoreNames.contains('pendingInventoryUpdates')) {
          db.createObjectStore('pendingInventoryUpdates', { keyPath: 'id', autoIncrement: true });
        }
        
        if (!db.objectStoreNames.contains('pendingShoppingUpdates')) {
          db.createObjectStore('pendingShoppingUpdates', { keyPath: 'id', autoIncrement: true });
        }
        
        if (!db.objectStoreNames.contains('cachedInventory')) {
          db.createObjectStore('cachedInventory', { keyPath: 'id' });
        }
        
        if (!db.objectStoreNames.contains('cachedRecipes')) {
          db.createObjectStore('cachedRecipes', { keyPath: 'id' });
        }
        
        if (!db.objectStoreNames.contains('cachedShoppingLists')) {
          db.createObjectStore('cachedShoppingLists', { keyPath: 'id' });
        }
      };
    });
  }

  setupEventListeners() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.showConnectionStatus('online');
      this.syncPendingUpdates();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.showConnectionStatus('offline');
    });
  }

  showConnectionStatus(status) {
    const statusEl = document.getElementById('connection-status');
    if (statusEl) {
      statusEl.className = status === 'online' ? 
        'connection-status online' : 'connection-status offline';
      statusEl.textContent = status === 'online' ? 
        'Back online - syncing data...' : 'You\'re offline - changes will sync when connected';
      
      if (status === 'online') {
        setTimeout(() => {
          statusEl.style.display = 'none';
        }, 3000);
      } else {
        statusEl.style.display = 'block';
      }
    }
  }

  // Store data for offline access
  async storeOfflineData(storeName, data) {
    if (!this.db) await this.initializeDB();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      
      if (Array.isArray(data)) {
        data.forEach(item => store.put(item));
      } else {
        store.put(data);
      }
      
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }

  // Get offline data
  async getOfflineData(storeName, id = null) {
    if (!this.db) await this.initializeDB();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      
      const request = id ? store.get(id) : store.getAll();
      
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // Queue updates for when online
  async queueUpdate(type, data) {
    const storeName = `pending${type}Updates`;
    const update = {
      data: data,
      timestamp: new Date().toISOString(),
      csrfToken: this.getCSRFToken()
    };
    
    await this.storeOfflineData(storeName, update);
    
    // Register background sync if supported
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      navigator.serviceWorker.ready.then(registration => {
        return registration.sync.register(`sync-${type.toLowerCase()}`);
      });
    }
  }

  // Sync all pending updates
  async syncPendingUpdates() {
    if (!this.isOnline) return;

    try {
      await this.syncInventoryUpdates();
      await this.syncShoppingUpdates();
    } catch (error) {
      console.error('Failed to sync pending updates:', error);
    }
  }

  async syncInventoryUpdates() {
    const pendingUpdates = await this.getOfflineData('pendingInventoryUpdates');
    
    for (const update of pendingUpdates) {
      try {
        const response = await fetch('/api/inventory/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': update.csrfToken
          },
          body: JSON.stringify(update.data)
        });

        if (response.ok) {
          await this.removeOfflineData('pendingInventoryUpdates', update.id);
        }
      } catch (error) {
        console.error('Failed to sync inventory update:', error);
      }
    }
  }

  async syncShoppingUpdates() {
    const pendingUpdates = await this.getOfflineData('pendingShoppingUpdates');
    
    for (const update of pendingUpdates) {
      try {
        const response = await fetch('/api/shopping/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': update.csrfToken
          },
          body: JSON.stringify(update.data)
        });

        if (response.ok) {
          await this.removeOfflineData('pendingShoppingUpdates', update.id);
        }
      } catch (error) {
        console.error('Failed to sync shopping update:', error);
      }
    }
  }

  async removeOfflineData(storeName, id) {
    if (!this.db) await this.initializeDB();
    
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.delete(id);
      
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  getCSRFToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
  }

  // Enhanced fetch with offline support
  async enhancedFetch(url, options = {}) {
    try {
      if (this.isOnline) {
        const response = await fetch(url, options);
        
        // Cache GET responses for offline access
        if (options.method === 'GET' || !options.method) {
          const data = await response.clone().json();
          await this.cacheResponse(url, data);
        }
        
        return response;
      } else {
        // Try to get cached data
        const cachedData = await this.getCachedResponse(url);
        if (cachedData) {
          return new Response(JSON.stringify(cachedData), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        
        throw new Error('No cached data available');
      }
    } catch (error) {
      // If it's a mutation, queue it for later
      if (options.method && options.method !== 'GET') {
        await this.queueMutation(url, options);
        return new Response(JSON.stringify({ queued: true }), {
          status: 202,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      
      throw error;
    }
  }

  async cacheResponse(url, data) {
    let storeName;
    if (url.includes('/inventory/')) storeName = 'cachedInventory';
    else if (url.includes('/recipes/')) storeName = 'cachedRecipes';
    else if (url.includes('/shopping/')) storeName = 'cachedShoppingLists';
    else return;

    await this.storeOfflineData(storeName, {
      id: url,
      data: data,
      timestamp: new Date().toISOString()
    });
  }

  async getCachedResponse(url) {
    let storeName;
    if (url.includes('/inventory/')) storeName = 'cachedInventory';
    else if (url.includes('/recipes/')) storeName = 'cachedRecipes';
    else if (url.includes('/shopping/')) storeName = 'cachedShoppingLists';
    else return null;

    const cached = await this.getOfflineData(storeName, url);
    return cached ? cached.data : null;
  }

  async queueMutation(url, options) {
    let type;
    if (url.includes('/inventory/')) type = 'Inventory';
    else if (url.includes('/shopping/')) type = 'Shopping';
    else return;

    await this.queueUpdate(type, {
      url: url,
      method: options.method,
      body: options.body,
      headers: options.headers
    });
  }
}

// Initialize offline manager
const offlineManager = new OfflineManager();

// Export for global use
window.offlineManager = offlineManager;