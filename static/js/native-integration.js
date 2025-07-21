/**
 * Native App Integration
 * Handles mobile-specific features when running in Capacitor
 */

import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { PushNotifications } from '@capacitor/push-notifications';
import { StatusBar, Style } from '@capacitor/status-bar';
import { Keyboard } from '@capacitor/keyboard';
import { App } from '@capacitor/app';
import { Haptics, ImpactStyle } from '@capacitor/haptics';
import { SplashScreen } from '@capacitor/splash-screen';

class NativeIntegration {
    constructor() {
        this.isNativeApp = this.detectNativeEnvironment();
        this.init();
    }

    detectNativeEnvironment() {
        return (
            window.Capacitor !== undefined && 
            window.Capacitor.isNativePlatform()
        );
    }

    async init() {
        if (!this.isNativeApp) {
            console.log('Running in web browser, native features disabled');
            return;
        }

        console.log('Initializing native app features...');
        
        try {
            await this.setupStatusBar();
            await this.setupPushNotifications();
            await this.setupKeyboardListeners();
            await this.setupAppStateListeners();
            await this.hideSplashScreen();
            
            // Initialize barcode scanner integration
            this.setupBarcodeScanner();
            
            console.log('Native app initialization complete');
        } catch (error) {
            console.error('Error initializing native features:', error);
        }
    }

    async setupStatusBar() {
        try {
            // Set status bar style based on theme
            await StatusBar.setStyle({ style: Style.Dark });
            await StatusBar.setBackgroundColor({ color: '#2563eb' });
        } catch (error) {
            console.error('Error setting up status bar:', error);
        }
    }

    async setupPushNotifications() {
        try {
            // Request permission for push notifications
            let permStatus = await PushNotifications.checkPermissions();

            if (permStatus.receive === 'prompt') {
                permStatus = await PushNotifications.requestPermissions();
            }

            if (permStatus.receive !== 'granted') {
                console.log('Push notification permissions not granted');
                return;
            }

            // Register for push notifications
            await PushNotifications.register();

            // Listen for registration success
            PushNotifications.addListener('registration', (token) => {
                console.log('Push registration success:', token.value);
                this.sendTokenToServer(token.value);
            });

            // Listen for registration errors
            PushNotifications.addListener('registrationError', (error) => {
                console.error('Push registration error:', error);
            });

            // Handle push notifications
            PushNotifications.addListener('pushNotificationReceived', (notification) => {
                console.log('Push notification received:', notification);
                this.handlePushNotification(notification);
            });

            // Handle notification actions
            PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
                console.log('Push action performed:', action);
                this.handleNotificationAction(action);
            });

        } catch (error) {
            console.error('Error setting up push notifications:', error);
        }
    }

    async setupKeyboardListeners() {
        try {
            // Handle keyboard show/hide for better UX
            Keyboard.addListener('keyboardWillShow', (info) => {
                document.body.style.paddingBottom = `${info.keyboardHeight}px`;
            });

            Keyboard.addListener('keyboardWillHide', () => {
                document.body.style.paddingBottom = '0px';
            });
        } catch (error) {
            console.error('Error setting up keyboard listeners:', error);
        }
    }

    async setupAppStateListeners() {
        try {
            // Handle app state changes
            App.addListener('appStateChange', ({ isActive }) => {
                console.log('App state changed. Is active:', isActive);
                
                if (isActive) {
                    // App became active - refresh data if needed
                    this.onAppActive();
                } else {
                    // App went to background - save state if needed
                    this.onAppInactive();
                }
            });

            // Handle deep links
            App.addListener('appUrlOpen', (event) => {
                console.log('Deep link opened:', event.url);
                this.handleDeepLink(event.url);
            });

        } catch (error) {
            console.error('Error setting up app state listeners:', error);
        }
    }

    async hideSplashScreen() {
        try {
            await SplashScreen.hide();
        } catch (error) {
            console.error('Error hiding splash screen:', error);
        }
    }

    setupBarcodeScanner() {
        // Override the web barcode scanner with native camera
        if (window.BarcodeScanner) {
            window.BarcodeScanner.scanWithCamera = this.scanBarcodeWithNativeCamera.bind(this);
        }
    }

    async scanBarcodeWithNativeCamera() {
        try {
            await this.triggerHapticFeedback();

            const image = await Camera.getPhoto({
                quality: 90,
                allowEditing: false,
                resultType: CameraResultType.DataUrl,
                source: CameraSource.Camera,
                width: 800,
                height: 600
            });

            // Send image to barcode detection service
            return await this.processBarcodeImage(image.dataUrl);

        } catch (error) {
            console.error('Error scanning barcode with camera:', error);
            throw error;
        }
    }

    async processBarcodeImage(imageDataUrl) {
        try {
            // Send image to Django backend for barcode processing
            const response = await fetch('/api/barcode/scan/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    image: imageDataUrl
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.barcode) {
                await this.triggerHapticFeedback('success');
                return result.barcode;
            } else {
                throw new Error('No barcode detected in image');
            }

        } catch (error) {
            await this.triggerHapticFeedback('error');
            throw error;
        }
    }

    async triggerHapticFeedback(type = 'light') {
        if (!this.isNativeApp) return;

        try {
            switch (type) {
                case 'light':
                    await Haptics.impact({ style: ImpactStyle.Light });
                    break;
                case 'medium':
                    await Haptics.impact({ style: ImpactStyle.Medium });
                    break;
                case 'heavy':
                    await Haptics.impact({ style: ImpactStyle.Heavy });
                    break;
                case 'success':
                    await Haptics.vibrate();
                    break;
                case 'error':
                    await Haptics.vibrate();
                    await new Promise(resolve => setTimeout(resolve, 100));
                    await Haptics.vibrate();
                    break;
            }
        } catch (error) {
            console.error('Error triggering haptic feedback:', error);
        }
    }

    async sendTokenToServer(token) {
        try {
            await fetch('/api/push-notifications/register/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    token: token,
                    platform: window.Capacitor.getPlatform()
                })
            });
        } catch (error) {
            console.error('Error sending push token to server:', error);
        }
    }

    handlePushNotification(notification) {
        // Display in-app notification or handle silently
        console.log('Handling push notification:', notification);
        
        // Trigger haptic feedback
        this.triggerHapticFeedback('light');

        // If app is in foreground, show custom notification
        if (document.visibilityState === 'visible') {
            this.showInAppNotification(notification);
        }
    }

    handleNotificationAction(action) {
        const { notification, actionId } = action;
        
        switch (actionId) {
            case 'view_inventory':
                window.location.href = '/inventory/';
                break;
            case 'view_recipes':
                window.location.href = '/recipes/';
                break;
            case 'upgrade':
                window.location.href = '/subscriptions/upgrade/';
                break;
            default:
                // Default action - open app
                window.location.href = '/';
        }
    }

    showInAppNotification(notification) {
        // Create and show in-app notification UI
        const notificationEl = document.createElement('div');
        notificationEl.className = 'fixed top-4 left-4 right-4 bg-blue-600 text-white p-4 rounded-lg shadow-lg z-50 animate-slide-down';
        notificationEl.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <h3 class="font-semibold">${notification.title}</h3>
                    <p class="text-sm opacity-90">${notification.body}</p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-2 text-white/70 hover:text-white">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(notificationEl);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notificationEl.parentElement) {
                notificationEl.remove();
            }
        }, 5000);
    }

    handleDeepLink(url) {
        try {
            const urlObj = new URL(url);
            const path = urlObj.pathname;
            
            // Navigate to the appropriate page
            window.location.href = path;
        } catch (error) {
            console.error('Error handling deep link:', error);
        }
    }

    onAppActive() {
        // App became active - refresh data if needed
        console.log('App became active');
        
        // Check for expired inventory items
        if (window.location.pathname.includes('/inventory/')) {
            // Trigger inventory refresh if on inventory page
            this.refreshInventoryData();
        }
    }

    onAppInactive() {
        // App went to background - save any pending changes
        console.log('App went inactive');
        
        // Save any form data or pending changes
        this.savePendingChanges();
    }

    async refreshInventoryData() {
        try {
            // Check for updated inventory data
            const response = await fetch('/api/inventory/check-updates/', {
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.hasUpdates) {
                    // Refresh the page or specific components
                    window.location.reload();
                }
            }
        } catch (error) {
            console.error('Error refreshing inventory data:', error);
        }
    }

    savePendingChanges() {
        // Save any form data that might be lost
        const forms = document.querySelectorAll('form[data-auto-save]');
        forms.forEach(form => {
            const formData = new FormData(form);
            const data = Object.fromEntries(formData);
            localStorage.setItem(`form_data_${form.id}`, JSON.stringify(data));
        });
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // Public methods for external use
    async shareContent(title, text, url) {
        if (this.isNativeApp && window.Capacitor.Plugins.Share) {
            try {
                await window.Capacitor.Plugins.Share.share({
                    title,
                    text,
                    url
                });
            } catch (error) {
                console.error('Error sharing content:', error);
            }
        }
    }

    async openExternalUrl(url) {
        if (this.isNativeApp && window.Capacitor.Plugins.Browser) {
            try {
                await window.Capacitor.Plugins.Browser.open({ url });
            } catch (error) {
                console.error('Error opening external URL:', error);
                window.open(url, '_blank');
            }
        } else {
            window.open(url, '_blank');
        }
    }
}

// Initialize native integration when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.nativeIntegration = new NativeIntegration();
    });
} else {
    window.nativeIntegration = new NativeIntegration();
}

// Export for external use
window.NativeIntegration = NativeIntegration;