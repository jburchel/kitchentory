// Popup script for Kitchentory browser extension

class KitchentoryPopup {
  constructor() {
    this.elements = {
      loginSection: document.getElementById('login-section'),
      connectedSection: document.getElementById('connected-section'),
      loading: document.getElementById('loading'),
      loginBtn: document.getElementById('login-btn'),
      logoutBtn: document.getElementById('logout-btn'),
      syncBtn: document.getElementById('sync-now-btn'),
      autoCapture: document.getElementById('auto-capture'),
      serverUrl: document.getElementById('server-url'),
      email: document.getElementById('email'),
      password: document.getElementById('password'),
      userEmail: document.getElementById('user-email'),
      itemsCaptured: document.getElementById('items-captured'),
      itemsSynced: document.getElementById('items-synced'),
      loginError: document.getElementById('login-error')
    };

    this.api = new KitchentoryAPI();
    this.init();
  }

  async init() {
    // Initialize API service
    await this.api.init();
    
    // Check if user is logged in
    if (this.api.isAuthenticated) {
      try {
        const userInfo = await this.api.getUserInfo();
        this.showConnectedView(userInfo.user.email);
        this.loadStats();
      } catch (error) {
        // Auth might be expired, show login
        this.showLoginView();
      }
    } else {
      this.showLoginView();
    }

    // Event listeners
    this.elements.loginBtn.addEventListener('click', () => this.handleLogin());
    this.elements.logoutBtn.addEventListener('click', () => this.handleLogout());
    this.elements.syncBtn.addEventListener('click', () => this.handleSync());
    this.elements.autoCapture.addEventListener('change', (e) => this.toggleAutoCapture(e.target.checked));

    // Load auto-capture setting
    const settings = await chrome.storage.local.get(['autoCapture']);
    this.elements.autoCapture.checked = settings.autoCapture || false;
  }

  showLoginView() {
    this.elements.loginSection.classList.remove('hidden');
    this.elements.connectedSection.classList.add('hidden');
    this.elements.loading.classList.add('hidden');
  }

  showConnectedView(email) {
    this.elements.loginSection.classList.add('hidden');
    this.elements.connectedSection.classList.remove('hidden');
    this.elements.loading.classList.add('hidden');
    this.elements.userEmail.textContent = email;
  }

  showLoading() {
    this.elements.loading.classList.remove('hidden');
  }

  hideLoading() {
    this.elements.loading.classList.add('hidden');
  }

  async handleLogin() {
    const serverUrl = this.elements.serverUrl.value.trim();
    const email = this.elements.email.value.trim();
    const password = this.elements.password.value.trim();

    if (!serverUrl || !email || !password) {
      this.showError('Please fill in all fields');
      return;
    }

    // Validate server URL format
    try {
      new URL(serverUrl);
    } catch (e) {
      this.showError('Please enter a valid server URL');
      return;
    }

    this.showLoading();
    this.hideError();

    try {
      // Login using API service
      const authData = await this.api.login(serverUrl, email, password);

      // Send message to background script
      chrome.runtime.sendMessage({ 
        type: 'AUTH_SUCCESS', 
        auth: authData
      });

      this.showConnectedView(authData.email);
      this.loadStats();
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        this.showError('Cannot connect to server. Check your internet connection and server URL.');
      } else {
        this.showError(error.message || 'Login failed');
      }
    } finally {
      this.hideLoading();
    }
  }

  async handleLogout() {
    try {
      await this.api.logout();
    } catch (error) {
      console.warn('Logout error:', error);
    }
    
    chrome.runtime.sendMessage({ type: 'AUTH_LOGOUT' });
    this.showLoginView();
  }

  async handleSync() {
    this.showLoading();
    
    try {
      // Send sync request to background script
      const response = await chrome.runtime.sendMessage({ type: 'SYNC_ITEMS' });
      
      if (response && response.success) {
        this.loadStats();
        // Show success message
        this.elements.syncBtn.textContent = `Synced ${response.synced} items!`;
        setTimeout(() => {
          this.elements.syncBtn.textContent = 'Sync Now';
        }, 2000);
      } else {
        const errorMsg = response?.error || 'Sync failed';
        this.showError(errorMsg);
        
        // If auth expired, show login form
        if (errorMsg.includes('Authentication expired')) {
          await chrome.storage.local.remove(['auth']);
          this.showLoginView();
        }
      }
    } catch (error) {
      console.error('Sync failed:', error);
      this.showError('Sync failed. Please try again.');
    } finally {
      this.hideLoading();
    }
  }

  async toggleAutoCapture(enabled) {
    await chrome.storage.local.set({ autoCapture: enabled });
    chrome.runtime.sendMessage({ type: 'TOGGLE_AUTO_CAPTURE', enabled });
  }

  async loadStats() {
    const stats = await chrome.storage.local.get(['stats']);
    if (stats.stats) {
      this.elements.itemsCaptured.textContent = stats.stats.captured || 0;
      this.elements.itemsSynced.textContent = stats.stats.synced || 0;
    }
  }

  async getStoredAuth() {
    const result = await chrome.storage.local.get(['auth']);
    return result.auth;
  }

  showError(message) {
    this.elements.loginError.textContent = message;
    this.elements.loginError.classList.remove('hidden');
  }

  hideError() {
    this.elements.loginError.classList.add('hidden');
  }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new KitchentoryPopup();
});