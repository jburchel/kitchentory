// Service Worker for Kitchentory PWA
const CACHE_NAME = 'kitchentory-v1';
const urlsToCache = [
  '/',
  '/static/css/tailwind.css',
  '/static/js/main.js',
  '/static/js/barcode-scanner.js',
  '/static/images/logo.png',
  '/static/images/icon-192.png',
  '/static/images/icon-512.png',
  '/inventory/',
  '/recipes/',
  '/shopping/',
  '/offline/',
];

// Install event - cache resources
self.addEventListener('install', event => {
  console.log('Service Worker: Install');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching files');
        return cache.addAll(urlsToCache);
      })
      .catch(err => console.log('Service Worker: Cache failed', err))
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activate');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('Service Worker: Clearing old cache', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', event => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and data URLs
  if (event.request.url.startsWith('chrome-extension://') || 
      event.request.url.startsWith('data:')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached version or fetch from network
        if (response) {
          return response;
        }

        return fetch(event.request).then(response => {
          // Check if valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response for caching
          const responseToCache = response.clone();

          // Cache API responses for offline access
          if (event.request.url.includes('/api/') ||
              event.request.url.includes('/inventory/') ||
              event.request.url.includes('/recipes/') ||
              event.request.url.includes('/shopping/')) {
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
          }

          return response;
        });
      })
      .catch(() => {
        // Offline fallback
        if (event.request.destination === 'document') {
          return caches.match('/offline/');
        }
        
        // Return a generic offline response for other requests
        return new Response('Offline', {
          status: 503,
          statusText: 'Service Unavailable',
          headers: new Headers({
            'Content-Type': 'text/plain'
          })
        });
      })
  );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  console.log('Service Worker: Background sync', event.tag);
  
  if (event.tag === 'sync-inventory') {
    event.waitUntil(syncInventoryData());
  } else if (event.tag === 'sync-shopping') {
    event.waitUntil(syncShoppingData());
  }
});

// Push notification handling
self.addEventListener('push', event => {
  console.log('Service Worker: Push notification received');
  
  const options = {
    body: event.data ? event.data.text() : 'New notification from Kitchentory',
    icon: '/static/images/icon-192.png',
    badge: '/static/images/badge-72.png',
    tag: 'kitchentory-notification',
    requireInteraction: true,
    actions: [
      {
        action: 'view',
        title: 'View',
        icon: '/static/images/action-view.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/static/images/action-dismiss.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Kitchentory', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  console.log('Service Worker: Notification click', event.action);
  
  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Sync functions
async function syncInventoryData() {
  try {
    // Get pending inventory updates from IndexedDB
    const pendingUpdates = await getStoredData('pendingInventoryUpdates');
    
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
          // Remove synced update
          await removeStoredData('pendingInventoryUpdates', update.id);
        }
      } catch (error) {
        console.error('Failed to sync inventory update:', error);
      }
    }
  } catch (error) {
    console.error('Failed to sync inventory data:', error);
  }
}

async function syncShoppingData() {
  try {
    // Get pending shopping list updates from IndexedDB
    const pendingUpdates = await getStoredData('pendingShoppingUpdates');
    
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
          // Remove synced update
          await removeStoredData('pendingShoppingUpdates', update.id);
        }
      } catch (error) {
        console.error('Failed to sync shopping update:', error);
      }
    }
  } catch (error) {
    console.error('Failed to sync shopping data:', error);
  }
}

// IndexedDB helpers
function getStoredData(storeName) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('KitchentoryOffline', 1);
    
    request.onerror = () => reject(request.error);
    
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const getAllRequest = store.getAll();
      
      getAllRequest.onsuccess = () => resolve(getAllRequest.result);
      getAllRequest.onerror = () => reject(getAllRequest.error);
    };
    
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(storeName)) {
        db.createObjectStore(storeName, { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

function removeStoredData(storeName, id) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('KitchentoryOffline', 1);
    
    request.onerror = () => reject(request.error);
    
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const deleteRequest = store.delete(id);
      
      deleteRequest.onsuccess = () => resolve();
      deleteRequest.onerror = () => reject(deleteRequest.error);
    };
  });
}