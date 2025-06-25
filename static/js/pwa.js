// PWA Installation and Management
class PWAManager {
  constructor() {
    this.installPrompt = null;
    this.isInstalled = false;
    this.isStandalone = window.matchMedia('(display-mode: standalone)').matches || 
                       window.navigator.standalone || 
                       document.referrer.includes('android-app://');
    
    this.init();
  }

  init() {
    // Register service worker
    this.registerServiceWorker();
    
    // Setup install prompt
    this.setupInstallPrompt();
    
    // Check if already installed
    this.checkInstallStatus();
    
    // Setup push notifications
    this.setupPushNotifications();
  }

  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/static/js/sw.js');
        console.log('Service Worker registered:', registration);
        
        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.showUpdateNotification();
            }
          });
        });
        
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  }

  setupInstallPrompt() {
    // Listen for beforeinstallprompt event
    window.addEventListener('beforeinstallprompt', (event) => {
      event.preventDefault();
      this.installPrompt = event;
      this.showInstallButton();
    });

    // Listen for appinstalled event
    window.addEventListener('appinstalled', () => {
      this.isInstalled = true;
      this.hideInstallButton();
      this.showInstalledMessage();
    });
  }

  showInstallButton() {
    if (this.isStandalone || this.isInstalled) return;

    const installBtn = document.getElementById('install-button');
    if (installBtn) {
      installBtn.style.display = 'block';
      installBtn.addEventListener('click', () => this.promptInstall());
    } else {
      // Create install banner
      this.createInstallBanner();
    }
  }

  hideInstallButton() {
    const installBtn = document.getElementById('install-button');
    const installBanner = document.getElementById('install-banner');
    
    if (installBtn) installBtn.style.display = 'none';
    if (installBanner) installBanner.remove();
  }

  createInstallBanner() {
    if (document.getElementById('install-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'install-banner';
    banner.className = 'install-banner fixed bottom-4 left-4 right-4 bg-blue-600 text-white p-4 rounded-lg shadow-lg z-50 transform translate-y-full transition-transform duration-300';
    banner.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
            <svg class="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
              <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
            </svg>
          </div>
          <div>
            <p class="font-medium">Install Kitchentory</p>
            <p class="text-sm text-blue-100">Get the full app experience</p>
          </div>
        </div>
        <div class="flex items-center space-x-2">
          <button onclick="pwaManager.promptInstall()" 
                  class="bg-white text-blue-600 px-4 py-2 rounded-lg font-medium text-sm hover:bg-blue-50 transition-colors">
            Install
          </button>
          <button onclick="pwaManager.dismissInstallBanner()" 
                  class="text-blue-100 hover:text-white">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(banner);
    
    // Show banner with animation
    setTimeout(() => {
      banner.classList.remove('translate-y-full');
    }, 100);
  }

  dismissInstallBanner() {
    const banner = document.getElementById('install-banner');
    if (banner) {
      banner.classList.add('translate-y-full');
      setTimeout(() => banner.remove(), 300);
    }
    
    // Remember dismissal
    localStorage.setItem('installBannerDismissed', Date.now().toString());
  }

  async promptInstall() {
    if (!this.installPrompt) return;

    try {
      const result = await this.installPrompt.prompt();
      console.log('Install prompt result:', result.outcome);
      
      if (result.outcome === 'accepted') {
        this.isInstalled = true;
      }
      
      this.installPrompt = null;
    } catch (error) {
      console.error('Install prompt failed:', error);
    }
  }

  checkInstallStatus() {
    // Check if running in standalone mode
    if (this.isStandalone) {
      this.isInstalled = true;
      this.addStandaloneStyles();
    }

    // Check if install banner was recently dismissed
    const dismissed = localStorage.getItem('installBannerDismissed');
    if (dismissed && Date.now() - parseInt(dismissed) < 7 * 24 * 60 * 60 * 1000) {
      // Don't show banner for 7 days after dismissal
      return;
    }
  }

  addStandaloneStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .standalone-only { display: block !important; }
      .browser-only { display: none !important; }
      
      /* Add safe area padding for standalone apps */
      .standalone-safe-top { padding-top: env(safe-area-inset-top); }
      .standalone-safe-bottom { padding-bottom: env(safe-area-inset-bottom); }
      
      /* Hide browser UI elements in standalone mode */
      .pwa-hide { display: none !important; }
    `;
    document.head.appendChild(style);
    
    document.body.classList.add('standalone-app');
  }

  showInstalledMessage() {
    const message = document.createElement('div');
    message.className = 'fixed top-4 left-4 right-4 bg-green-600 text-white p-4 rounded-lg shadow-lg z-50 transform -translate-y-full transition-transform duration-300';
    message.innerHTML = `
      <div class="flex items-center space-x-3">
        <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
        </svg>
        <div>
          <p class="font-medium">Kitchentory Installed!</p>
          <p class="text-sm text-green-100">You can now access the app from your home screen</p>
        </div>
      </div>
    `;

    document.body.appendChild(message);
    
    setTimeout(() => {
      message.classList.remove('-translate-y-full');
    }, 100);
    
    setTimeout(() => {
      message.classList.add('-translate-y-full');
      setTimeout(() => message.remove(), 300);
    }, 5000);
  }

  showUpdateNotification() {
    const notification = document.createElement('div');
    notification.className = 'fixed top-4 left-4 right-4 bg-blue-600 text-white p-4 rounded-lg shadow-lg z-50';
    notification.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
          </svg>
          <div>
            <p class="font-medium">Update Available</p>
            <p class="text-sm text-blue-100">A new version of Kitchentory is ready</p>
          </div>
        </div>
        <button onclick="pwaManager.updateApp()" 
                class="bg-white text-blue-600 px-4 py-2 rounded-lg font-medium text-sm hover:bg-blue-50 transition-colors">
          Update
        </button>
      </div>
    `;

    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.remove();
    }, 10000);
  }

  async updateApp() {
    if ('serviceWorker' in navigator) {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration && registration.waiting) {
        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        window.location.reload();
      }
    }
  }

  async setupPushNotifications() {
    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
      return;
    }

    // Check current permission
    if (Notification.permission === 'default') {
      this.showNotificationPrompt();
    } else if (Notification.permission === 'granted') {
      this.subscribeToNotifications();
    }
  }

  showNotificationPrompt() {
    const prompt = document.createElement('div');
    prompt.className = 'fixed bottom-20 left-4 right-4 bg-white border border-gray-200 rounded-lg shadow-lg z-40 p-4';
    prompt.innerHTML = `
      <div class="flex items-start space-x-3">
        <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
          <svg class="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z"/>
          </svg>
        </div>
        <div class="flex-1">
          <p class="font-medium text-gray-900">Stay Updated</p>
          <p class="text-sm text-gray-600 mt-1">Get notified about expiring items and recipe suggestions</p>
          <div class="flex space-x-2 mt-3">
            <button onclick="pwaManager.enableNotifications()" 
                    class="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 transition-colors">
              Enable
            </button>
            <button onclick="pwaManager.dismissNotificationPrompt()" 
                    class="text-gray-600 px-3 py-1 rounded text-sm hover:text-gray-800">
              Not Now
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(prompt);
    
    setTimeout(() => {
      prompt.remove();
    }, 15000);
  }

  async enableNotifications() {
    try {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        await this.subscribeToNotifications();
        this.dismissNotificationPrompt();
      }
    } catch (error) {
      console.error('Failed to enable notifications:', error);
    }
  }

  dismissNotificationPrompt() {
    const prompts = document.querySelectorAll('.fixed.bottom-20');
    prompts.forEach(prompt => prompt.remove());
  }

  async subscribeToNotifications() {
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(window.vapidPublicKey || '')
      });

      // Send subscription to server
      await fetch('/api/notifications/subscribe/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify(subscription)
      });

    } catch (error) {
      console.error('Failed to subscribe to notifications:', error);
    }
  }

  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  getCSRFToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
  }
}

// Initialize PWA manager
const pwaManager = new PWAManager();

// Export for global access
window.pwaManager = pwaManager;