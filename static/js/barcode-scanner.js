/**
 * Barcode Scanner Module for Kitchentory
 * Handles camera permissions, barcode scanning, and manual entry fallback
 */

// Wait for Html5Qrcode library to load
function waitForHtml5Qrcode() {
    return new Promise((resolve, reject) => {
        if (typeof Html5Qrcode !== 'undefined' && typeof Html5QrcodeScanner !== 'undefined') {
            console.log('Html5Qrcode library already loaded');
            resolve();
            return;
        }
        
        console.log('Waiting for Html5Qrcode library to load...');
        let attempts = 0;
        const maxAttempts = 50; // 5 seconds max
        
        const checkLibrary = () => {
            attempts++;
            if (typeof Html5Qrcode !== 'undefined' && typeof Html5QrcodeScanner !== 'undefined') {
                console.log('Html5Qrcode library loaded successfully');
                resolve();
            } else if (attempts >= maxAttempts) {
                console.error('Html5Qrcode library failed to load after 5 seconds');
                reject(new Error('Html5Qrcode library not available'));
            } else {
                setTimeout(checkLibrary, 100);
            }
        };
        
        checkLibrary();
    });
}

class BarcodeScanner {
    constructor() {
        this.scanner = null;
        this.isScanning = false;
        this.onSuccessCallback = null;
        this.onErrorCallback = null;
        this.config = {
            fps: 10,
            qrbox: { width: 250, height: 250 },
            aspectRatio: 1.0,
            supportedScanTypes: [
                Html5QrcodeScanType.SCAN_TYPE_CAMERA
            ]
        };
    }

    /**
     * Check if camera access is supported
     */
    async checkCameraSupport() {
        try {
            // Check if getUserMedia is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                return {
                    supported: false,
                    reason: 'Camera access not supported by this browser'
                };
            }

            // Check if we're on iOS and provide browser guidance
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
            const isOldIOS = isIOS && parseFloat(navigator.userAgent.match(/OS (\d+)_/)?.[1] || '0') < 14.3;
            
            if (isOldIOS && !navigator.userAgent.includes('Safari')) {
                return {
                    supported: false,
                    reason: 'Camera scanning requires Safari on iOS versions below 14.3'
                };
            }

            return { supported: true };
        } catch (error) {
            return {
                supported: false,
                reason: `Camera check failed: ${error.message}`
            };
        }
    }

    /**
     * Request camera permission with user-friendly messaging
     */
    async requestCameraPermission() {
        console.log('🎥 Requesting camera permission...');
        try {
            const support = await this.checkCameraSupport();
            if (!support.supported) {
                console.log('❌ Camera not supported:', support.reason);
                throw new Error(support.reason);
            }

            console.log('✅ Camera is supported, requesting access...');
            
            // Try to access camera to trigger permission prompt
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'environment' // Prefer back camera
                } 
            });
            
            console.log('✅ Camera permission granted, got stream:', stream);
            
            // Stop the stream immediately - we just needed to check permission
            stream.getTracks().forEach(track => track.stop());
            
            return { granted: true };
        } catch (error) {
            console.log('❌ Camera permission error:', error.name, error.message);
            
            if (error.name === 'NotAllowedError') {
                return {
                    granted: false,
                    reason: 'Camera permission denied. Please enable camera access in your browser settings.'
                };
            } else if (error.name === 'NotFoundError') {
                return {
                    granted: false,
                    reason: 'No camera found on this device.'
                };
            } else {
                return {
                    granted: false,
                    reason: `Camera access failed: ${error.message}`
                };
            }
        }
    }

    /**
     * Start scanning with camera
     */
    async startScanning(elementId, onSuccess, onError) {
        try {
            // Stop any existing scanner first
            if (this.isScanning) {
                console.log('Stopping existing scanner...');
                await this.stopScanning();
            }

            // Wait for library to load first
            await waitForHtml5Qrcode();

            this.onSuccessCallback = onSuccess;
            this.onErrorCallback = onError;

            // Check permissions first
            const permission = await this.requestCameraPermission();
            if (!permission.granted) {
                throw new Error(permission.reason);
            }

            console.log('Initializing Html5QrcodeScanner...');
            // Initialize scanner
            this.scanner = new Html5QrcodeScanner(elementId, this.config, false);
            
            // Start scanning
            this.scanner.render(
                (decodedText, decodedResult) => this.handleScanSuccess(decodedText, decodedResult),
                (error) => this.handleScanError(error)
            );

            this.isScanning = true;
            return { success: true };

        } catch (error) {
            console.error('Failed to start scanning:', error);
            if (onError) onError(error.message);
            return { success: false, error: error.message };
        }
    }

    /**
     * Stop scanning and cleanup
     */
    async stopScanning() {
        try {
            if (this.scanner) {
                console.log('Cleaning up scanner...');
                try {
                    await this.scanner.clear();
                } catch (clearError) {
                    console.warn('Error clearing scanner:', clearError);
                }
                this.scanner = null;
            }
            this.isScanning = false;
            this.onSuccessCallback = null;
            this.onErrorCallback = null;
            return { success: true };
        } catch (error) {
            console.error('Error stopping scanner:', error);
            // Force cleanup even if there's an error
            this.scanner = null;
            this.isScanning = false;
            this.onSuccessCallback = null;
            this.onErrorCallback = null;
            return { success: false, error: error.message };
        }
    }

    /**
     * Handle successful scan
     */
    handleScanSuccess(decodedText, decodedResult) {
        console.log('Barcode scanned:', decodedText);
        
        // Stop scanning after successful scan
        this.stopScanning();

        // Call success callback
        if (this.onSuccessCallback) {
            this.onSuccessCallback({
                text: decodedText,
                format: decodedResult.result?.format || 'unknown',
                timestamp: new Date().toISOString()
            });
        }
    }

    /**
     * Handle scan errors (most are not critical)
     */
    handleScanError(error) {
        // Only log actual errors, not "no QR code found" messages
        if (!error.includes('NotFoundException') && !error.includes('No MultiFormat Readers')) {
            console.warn('Scan error:', error);
        }
    }

    /**
     * Get list of available cameras
     */
    async getCameras() {
        try {
            const devices = await Html5Qrcode.getCameras();
            return {
                success: true,
                cameras: devices.map(device => ({
                    id: device.id,
                    label: device.label || `Camera ${device.id}`
                }))
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                cameras: []
            };
        }
    }

    /**
     * Switch between front and back camera
     */
    async switchCamera(cameraId) {
        if (!this.isScanning) {
            return { success: false, error: 'Scanner not running' };
        }

        try {
            // Stop current scanning
            await this.stopScanning();
            
            // Update config with specific camera
            const newConfig = {
                ...this.config,
                cameraIdOrConfig: cameraId
            };

            // Restart with new camera
            this.scanner = new Html5QrcodeScanner('scanner-container', newConfig, false);
            this.scanner.render(
                (decodedText, decodedResult) => this.handleScanSuccess(decodedText, decodedResult),
                (error) => this.handleScanError(error)
            );

            this.isScanning = true;
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Validate barcode format for grocery products
     */
    validateBarcodeFormat(barcode) {
        // Remove any whitespace
        const cleanBarcode = barcode.trim();
        
        // Check for common grocery barcode formats
        const formats = {
            UPC_A: /^\d{12}$/,           // 12 digits
            UPC_E: /^\d{8}$/,            // 8 digits  
            EAN_13: /^\d{13}$/,          // 13 digits
            EAN_8: /^\d{8}$/,            // 8 digits
            Code_128: /^[\x00-\x7F]+$/   // ASCII characters
        };

        for (const [format, regex] of Object.entries(formats)) {
            if (regex.test(cleanBarcode)) {
                return { valid: true, format, barcode: cleanBarcode };
            }
        }

        return { 
            valid: false, 
            format: 'unknown',
            barcode: cleanBarcode,
            error: 'Barcode format not recognized. Please ensure it\'s a valid grocery product barcode.'
        };
    }

    /**
     * Process scanned barcode for product lookup
     */
    async processBarcode(barcodeData) {
        const validation = this.validateBarcodeFormat(barcodeData.text);
        
        if (!validation.valid) {
            console.warn('Invalid barcode format:', validation.error);
            if (this.onErrorCallback) {
                this.onErrorCallback(validation.error);
            }
            return { success: false, error: validation.error };
        }

        // Return validated barcode data
        return {
            success: true,
            barcode: validation.barcode,
            format: validation.format,
            timestamp: barcodeData.timestamp
        };
    }
}

// Global scanner instance - wait for library to load first
window.addEventListener('load', async () => {
    try {
        await waitForHtml5Qrcode();
        window.barcodeScanner = new BarcodeScanner();
        console.log('✅ BarcodeScanner instance created successfully');
    } catch (error) {
        console.error('❌ Failed to create BarcodeScanner instance:', error);
        // Create a fallback object
        window.barcodeScanner = {
            startScanning: () => Promise.resolve({ success: false, error: 'Scanner not available' }),
            stopScanning: () => Promise.resolve({ success: true }),
            validateBarcodeFormat: (barcode) => ({ valid: true, format: 'unknown', barcode })
        };
    }
});

// Immediate fallback for early access
if (!window.barcodeScanner) {
    window.barcodeScanner = {
        startScanning: () => Promise.resolve({ success: false, error: 'Scanner initializing...' }),
        stopScanning: () => Promise.resolve({ success: true }),
        validateBarcodeFormat: (barcode) => ({ valid: true, format: 'unknown', barcode })
    };
}

// Helper functions for HTMX integration
window.startBarcodeScanning = async function(containerId = 'scanner-container') {
    const onSuccess = (data) => {
        // Dispatch custom event with barcode data
        window.dispatchEvent(new CustomEvent('barcodeScanned', { 
            detail: data 
        }));
    };

    const onError = (error) => {
        // Dispatch error event
        window.dispatchEvent(new CustomEvent('barcodeScanError', { 
            detail: { error } 
        }));
    };

    return await window.barcodeScanner.startScanning(containerId, onSuccess, onError);
};

window.stopBarcodeScanning = async function() {
    return await window.barcodeScanner.stopScanning();
};

// Camera permission check function
window.checkCameraPermission = async function() {
    const support = await window.barcodeScanner.checkCameraSupport();
    if (!support.supported) {
        return { granted: false, reason: support.reason };
    }
    
    return await window.barcodeScanner.requestCameraPermission();
};