/**
 * PWA Install Prompt Manager
 * Handles app installation prompts and subscription-aware features
 */

class PWAInstaller {
    constructor() {
        this.deferredPrompt = null;
        this.installButton = null;
        this.dismissedStorageKey = 'pwa_install_dismissed';
        this.installPromptShown = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkInstallPromptEligibility();
        this.setupSubscriptionAwareFeatures();
    }

    setupEventListeners() {
        // Listen for beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('PWA: beforeinstallprompt fired');
            
            // Prevent the mini-infobar from appearing on mobile
            e.preventDefault();
            
            // Store the event for later use
            this.deferredPrompt = e;
            
            // Show install promotion
            this.showInstallPromotion();
        });

        // Listen for app installed event
        window.addEventListener('appinstalled', (e) => {
            console.log('PWA: App was installed');
            this.onAppInstalled();
        });

        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.onOnlineStatusChange(true);
        });

        window.addEventListener('offline', () => {
            this.onOnlineStatusChange(false);
        });

        // Setup install button handlers
        document.addEventListener('DOMContentLoaded', () => {
            this.setupInstallButtons();
        });
    }

    setupInstallButtons() {
        // Find all install buttons
        const installButtons = document.querySelectorAll('[data-install-app]');
        
        installButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.showInstallPrompt();
            });
        });

        // Setup dismiss buttons
        const dismissButtons = document.querySelectorAll('[data-dismiss-install]');
        
        dismissButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.dismissInstallPromotion();
            });
        });
    }

    checkInstallPromptEligibility() {
        // Check if already installed
        if (this.isAppInstalled()) {
            console.log('PWA: App is already installed');
            this.hideInstallPromotions();
            return false;
        }

        // Check if user dismissed the prompt recently
        const dismissedTime = localStorage.getItem(this.dismissedStorageKey);
        if (dismissedTime) {
            const dismissedDate = new Date(dismissedTime);
            const daysSinceDismissed = (Date.now() - dismissedDate.getTime()) / (1000 * 60 * 60 * 24);
            
            if (daysSinceDismissed < 7) { // Don't show for 7 days after dismissal
                console.log('PWA: Install prompt dismissed recently');
                return false;
            }
        }

        return true;
    }

    isAppInstalled() {
        // Check if running in standalone mode
        return window.matchMedia('(display-mode: standalone)').matches || 
               window.navigator.standalone === true ||
               document.referrer.includes('android-app://');
    }

    showInstallPromotion() {
        if (!this.checkInstallPromptEligibility()) {
            return;
        }

        // Show install banner/modal
        const installBanner = document.getElementById('install-banner');
        if (installBanner) {
            installBanner.style.display = 'block';
            installBanner.classList.add('animate-slide-in');
        }

        // Create dynamic install prompt for subscription users
        if (window.userSubscriptionTier && window.userSubscriptionTier !== 'free') {
            this.createPremiumInstallPrompt();
        } else {
            this.createStandardInstallPrompt();
        }
    }

    createStandardInstallPrompt() {
        if (document.getElementById('dynamic-install-prompt')) {
            return; // Already exists
        }

        const prompt = document.createElement('div');
        prompt.id = 'dynamic-install-prompt';
        prompt.className = 'fixed bottom-4 left-4 right-4 bg-white border border-gray-300 rounded-lg shadow-lg p-4 z-50 md:max-w-sm md:left-auto';
        prompt.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <img src="/static/images/icon-72.png" alt="Kitchentory" class="w-10 h-10">
                    <div>
                        <h3 class="font-semibold text-gray-900">Install Kitchentory</h3>
                        <p class="text-sm text-gray-600">Quick access from your home screen</p>
                    </div>
                </div>
                <div class="flex space-x-2">
                    <button data-dismiss-install class="text-gray-500 hover:text-gray-700">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                    <button data-install-app class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                        Install
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(prompt);
        this.setupInstallButtons(); // Re-setup event listeners
    }

    createPremiumInstallPrompt() {
        if (document.getElementById('dynamic-install-prompt')) {
            return;
        }

        const prompt = document.createElement('div');
        prompt.id = 'dynamic-install-prompt';
        prompt.className = 'fixed bottom-4 left-4 right-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg shadow-lg p-4 z-50 md:max-w-sm md:left-auto';
        prompt.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <img src="/static/images/icon-72.png" alt="Kitchentory" class="w-10 h-10">
                    <div>
                        <h3 class="font-semibold">Install Premium App</h3>
                        <p class="text-sm opacity-90">Get offline access & push notifications</p>
                    </div>
                </div>
                <div class="flex space-x-2">
                    <button data-dismiss-install class="text-white/70 hover:text-white">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                    <button data-install-app class="bg-white text-blue-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-100">
                        Install
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(prompt);
        this.setupInstallButtons();
    }

    async showInstallPrompt() {
        if (!this.deferredPrompt) {
            console.log('PWA: No deferred prompt available');
            // Show manual instructions for iOS or other browsers
            this.showManualInstallInstructions();
            return;
        }

        try {
            // Show the install prompt
            this.deferredPrompt.prompt();

            // Wait for the user to respond to the prompt
            const { outcome } = await this.deferredPrompt.userChoice;
            
            console.log(`PWA: User ${outcome} the install prompt`);

            if (outcome === 'accepted') {
                this.onInstallAccepted();
            } else {
                this.onInstallDeclined();
            }

            // Clear the deferred prompt
            this.deferredPrompt = null;

        } catch (error) {
            console.error('PWA: Error showing install prompt:', error);
            this.showManualInstallInstructions();
        }
    }

    showManualInstallInstructions() {
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        const isAndroid = /Android/.test(navigator.userAgent);
        
        let instructions = '';
        
        if (isIOS) {
            instructions = `
                <div class="text-center p-6">
                    <h3 class="text-lg font-semibold mb-4">Install Kitchentory</h3>
                    <div class="space-y-3 text-sm text-gray-600">
                        <p>1. Tap the Share button <span class="inline-block">📤</span></p>
                        <p>2. Scroll down and tap "Add to Home Screen"</p>
                        <p>3. Tap "Add" to install the app</p>
                    </div>
                </div>
            `;
        } else if (isAndroid) {
            instructions = `
                <div class="text-center p-6">
                    <h3 class="text-lg font-semibold mb-4">Install Kitchentory</h3>
                    <div class="space-y-3 text-sm text-gray-600">
                        <p>1. Tap the menu (⋮) in your browser</p>
                        <p>2. Look for "Add to Home screen" or "Install app"</p>
                        <p>3. Tap "Add" or "Install"</p>
                    </div>
                </div>
            `;
        } else {
            instructions = `
                <div class="text-center p-6">
                    <h3 class="text-lg font-semibold mb-4">Install Kitchentory</h3>
                    <div class="space-y-3 text-sm text-gray-600">
                        <p>Look for an install icon in your browser's address bar</p>
                        <p>Or check your browser's menu for "Install" options</p>
                    </div>
                </div>
            `;
        }

        // Show modal with instructions
        this.showModal(instructions);
    }

    showModal(content) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4';
        modal.innerHTML = `
            <div class="bg-white rounded-lg max-w-sm w-full">
                ${content}
                <div class="border-t p-4">
                    <button onclick="this.closest('.fixed').remove()" class="w-full bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200">
                        Close
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    dismissInstallPromotion() {
        // Store dismissal timestamp
        localStorage.setItem(this.dismissedStorageKey, new Date().toISOString());
        
        // Hide install promotions
        this.hideInstallPromotions();
        
        console.log('PWA: Install promotion dismissed');
    }

    hideInstallPromotions() {
        const installBanner = document.getElementById('install-banner');
        if (installBanner) {
            installBanner.style.display = 'none';
        }

        const dynamicPrompt = document.getElementById('dynamic-install-prompt');
        if (dynamicPrompt) {
            dynamicPrompt.remove();
        }
    }

    onInstallAccepted() {
        // Hide install promotions
        this.hideInstallPromotions();
        
        // Track install event
        if (typeof gtag !== 'undefined') {
            gtag('event', 'pwa_install_accepted');
        }
    }

    onInstallDeclined() {
        // Store temporary dismissal
        this.dismissInstallPromotion();
        
        // Track decline event
        if (typeof gtag !== 'undefined') {
            gtag('event', 'pwa_install_declined');
        }
    }

    onAppInstalled() {
        // Hide all install promotions
        this.hideInstallPromotions();
        
        // Show success message
        this.showInstallSuccessMessage();
        
        // Enable additional PWA features
        this.enablePWAFeatures();
        
        // Track install success
        if (typeof gtag !== 'undefined') {
            gtag('event', 'pwa_installed');
        }
    }

    showInstallSuccessMessage() {
        const message = document.createElement('div');
        message.className = 'fixed top-4 left-4 right-4 bg-green-600 text-white p-4 rounded-lg shadow-lg z-50 md:max-w-sm md:left-auto';
        message.innerHTML = `
            <div class="flex items-center space-x-3">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                <div>
                    <h3 class="font-semibold">App Installed!</h3>
                    <p class="text-sm opacity-90">Kitchentory is now on your home screen</p>
                </div>
            </div>
        `;

        document.body.appendChild(message);

        // Remove after 5 seconds
        setTimeout(() => {
            message.remove();
        }, 5000);
    }

    enablePWAFeatures() {
        // Request notification permission for installed apps
        if ('Notification' in window && Notification.permission === 'default') {
            this.requestNotificationPermission();
        }

        // Enable background sync
        if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
            navigator.serviceWorker.ready.then(registration => {
                console.log('PWA: Background sync enabled');
            });
        }
    }

    async requestNotificationPermission() {
        try {
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                console.log('PWA: Notification permission granted');
                
                // Subscribe to push notifications if user has subscription
                if (window.userSubscriptionTier !== 'free') {
                    this.subscribeToPushNotifications();
                }
            }
        } catch (error) {
            console.error('PWA: Error requesting notification permission:', error);
        }
    }

    async subscribeToPushNotifications() {
        try {
            const registration = await navigator.serviceWorker.ready;
            
            // Check if push messaging is supported
            if (!('pushManager' in registration)) {
                console.warn('PWA: Push messaging is not supported');
                return;
            }

            // Subscribe to push notifications
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlB64ToUint8Array(window.vapidPublicKey || '')
            });

            // Send subscription to server
            await this.sendSubscriptionToServer(subscription);
            
            console.log('PWA: Subscribed to push notifications');

        } catch (error) {
            console.error('PWA: Error subscribing to push notifications:', error);
        }
    }

    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/push-subscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                },
                body: JSON.stringify({
                    subscription: subscription
                })
            });

            if (!response.ok) {
                throw new Error('Failed to send subscription to server');
            }
        } catch (error) {
            console.error('PWA: Error sending subscription to server:', error);
        }
    }

    urlB64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    onOnlineStatusChange(isOnline) {
        // Update UI based on online status
        const statusIndicator = document.getElementById('online-status');
        if (statusIndicator) {
            statusIndicator.textContent = isOnline ? 'Online' : 'Offline';
            statusIndicator.className = isOnline ? 
                'text-green-600' : 'text-orange-600';
        }

        // Show notification
        if (!isOnline) {
            this.showOfflineNotification();
        }
    }

    showOfflineNotification() {
        const notification = document.createElement('div');
        notification.className = 'fixed bottom-4 left-4 right-4 bg-orange-600 text-white p-3 rounded-lg shadow-lg z-40';
        notification.innerHTML = `
            <div class="flex items-center space-x-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z"></path>
                </svg>
                <span>You're offline. Some features may be limited.</span>
            </div>
        `;

        document.body.appendChild(notification);

        // Remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    setupSubscriptionAwareFeatures() {
        // Enable premium PWA features for subscribers
        if (window.userSubscriptionTier === 'premium' || window.userSubscriptionTier === 'pro') {
            this.enablePremiumPWAFeatures();
        }
    }

    enablePremiumPWAFeatures() {
        // Enable advanced caching for premium users
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then(registration => {
                registration.active?.postMessage({
                    type: 'ENABLE_PREMIUM_CACHING',
                    userTier: window.userSubscriptionTier
                });
            });
        }

        // Enable premium shortcuts
        this.enablePremiumShortcuts();
    }

    enablePremiumShortcuts() {
        // Add premium app shortcuts for installed PWA
        if (this.isAppInstalled() && 'setAppBadge' in navigator) {
            // Set app badge for premium features
            navigator.setAppBadge?.();
        }
    }
}

// Initialize PWA installer when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pwaInstaller = new PWAInstaller();
    });
} else {
    window.pwaInstaller = new PWAInstaller();
}

// Export for external use
window.PWAInstaller = PWAInstaller;