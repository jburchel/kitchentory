// Background service worker for Kitchentory extension

// Import API service (inline since we can't use modules in Manifest V3)
importScripts('api-service.js');

let capturedItems = [];
let api = null;

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
  console.log('Kitchentory Shopping Assistant installed');
  initializeAPI();
  loadStoredData();
});

// Initialize API service
async function initializeAPI() {
  api = new KitchentoryAPI();
  await api.init();
}

// Load stored data on startup
async function loadStoredData() {
  const stored = await chrome.storage.local.get(['capturedItems']);
  capturedItems = stored.capturedItems || [];
  
  // Initialize API if not already done
  if (!api) {
    await initializeAPI();
  }
}

// Message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.type) {
    case 'AUTH_SUCCESS':
      // Reinitialize API with new auth
      initializeAPI().then(() => {
        sendResponse({ success: true });
      });
      return true;
      
    case 'AUTH_LOGOUT':
      if (api) {
        api.logout().then(() => {
          capturedItems = [];
          chrome.storage.local.set({ capturedItems });
          sendResponse({ success: true });
        });
      } else {
        sendResponse({ success: true });
      }
      return true;
      
    case 'CAPTURE_ITEM':
      handleItemCapture(request.item, sender.tab);
      sendResponse({ success: true });
      break;
      
    case 'SYNC_ITEMS':
      syncItemsToKitchentory().then(result => {
        sendResponse(result);
      });
      return true; // Keep channel open for async response
      
    case 'TOGGLE_AUTO_CAPTURE':
      // Notify all content scripts
      chrome.tabs.query({}, (tabs) => {
        tabs.forEach(tab => {
          chrome.tabs.sendMessage(tab.id, { 
            type: 'AUTO_CAPTURE_CHANGED', 
            enabled: request.enabled 
          }).catch(() => {}); // Ignore errors for tabs without content script
        });
      });
      sendResponse({ success: true });
      break;
      
    case 'GET_AUTH':
      if (api) {
        sendResponse({ auth: api.getStatus() });
      } else {
        sendResponse({ auth: null });
      }
      break;
  }
});

// Handle item capture from content script
async function handleItemCapture(item, tab) {
  // Add metadata
  const captureItem = {
    ...item,
    capturedAt: new Date().toISOString(),
    sourceUrl: tab.url,
    sourceSite: new URL(tab.url).hostname,
    synced: false
  };
  
  capturedItems.push(captureItem);
  
  // Store items
  await chrome.storage.local.set({ capturedItems });
  
  // Update stats
  const stats = await chrome.storage.local.get(['stats']);
  const currentStats = stats.stats || { captured: 0, synced: 0 };
  currentStats.captured += 1;
  await chrome.storage.local.set({ stats: currentStats });
  
  // Update badge
  updateBadge();
  
  // Auto-sync if enabled
  const settings = await chrome.storage.local.get(['autoCapture']);
  if (settings.autoCapture) {
    // Debounce sync to avoid too many API calls
    scheduleSyncDebounced();
  }
}

// Sync items to Kitchentory
async function syncItemsToKitchentory() {
  if (!api || !api.isAuthenticated) {
    return { success: false, error: 'Not authenticated' };
  }
  
  const unsyncedItems = capturedItems.filter(item => !item.synced);
  if (unsyncedItems.length === 0) {
    return { success: true, synced: 0 };
  }
  
  try {
    const result = await api.bulkAddItems(unsyncedItems);
    
    // Mark items as synced
    capturedItems = capturedItems.map(item => {
      if (unsyncedItems.includes(item)) {
        return { ...item, synced: true, syncedAt: new Date().toISOString() };
      }
      return item;
    });
    
    await chrome.storage.local.set({ capturedItems });
    
    // Update stats
    const stats = await chrome.storage.local.get(['stats']);
    const currentStats = stats.stats || { captured: 0, synced: 0 };
    currentStats.synced += result.added || unsyncedItems.length;
    await chrome.storage.local.set({ stats: currentStats });
    
    // Clear badge
    chrome.action.setBadgeText({ text: '' });
    
    return { 
      success: true, 
      synced: result.added || unsyncedItems.length,
      total: result.total || unsyncedItems.length,
      errors: result.errors || []
    };
  } catch (error) {
    console.error('Sync error:', error);
    return { success: false, error: error.message };
  }
}

// Update extension badge with unsynced item count
function updateBadge() {
  const unsyncedCount = capturedItems.filter(item => !item.synced).length;
  
  if (unsyncedCount > 0) {
    chrome.action.setBadgeText({ text: unsyncedCount.toString() });
    chrome.action.setBadgeBackgroundColor({ color: '#10b981' });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

// Debounced sync function
let syncTimeout = null;
function scheduleSyncDebounced() {
  if (syncTimeout) {
    clearTimeout(syncTimeout);
  }
  
  syncTimeout = setTimeout(() => {
    syncItemsToKitchentory();
  }, 5000); // Wait 5 seconds before syncing
}

// Clean up old captured items (older than 7 days)
async function cleanupOldItems() {
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  
  capturedItems = capturedItems.filter(item => {
    const capturedDate = new Date(item.capturedAt);
    return capturedDate > sevenDaysAgo || !item.synced;
  });
  
  await chrome.storage.local.set({ capturedItems });
}

// Run cleanup daily
setInterval(cleanupOldItems, 24 * 60 * 60 * 1000);