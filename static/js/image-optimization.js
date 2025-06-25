// Image Optimization and Lazy Loading for Kitchentory
class ImageOptimizer {
  constructor() {
    this.isWebPSupported = this.checkWebPSupport();
    this.observerOptions = {
      root: null,
      rootMargin: '50px',
      threshold: 0.1
    };
    
    this.init();
  }

  init() {
    this.setupLazyLoading();
    this.setupProgressiveLoading();
    this.setupImageErrorHandling();
    this.optimizeExistingImages();
  }

  checkWebPSupport() {
    return new Promise(resolve => {
      const webP = new Image();
      webP.onload = webP.onerror = () => {
        resolve(webP.height === 2);
      };
      webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
    });
  }

  setupLazyLoading() {
    if (!('IntersectionObserver' in window)) {
      // Fallback for older browsers
      this.loadAllImages();
      return;
    }

    this.imageObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          this.loadImage(entry.target);
          this.imageObserver.unobserve(entry.target);
        }
      });
    }, this.observerOptions);

    // Observe all lazy images
    this.observeLazyImages();
  }

  observeLazyImages() {
    const lazyImages = document.querySelectorAll('img[data-src], img.lazy');
    lazyImages.forEach(img => {
      this.imageObserver.observe(img);
    });
  }

  async loadImage(img) {
    // Show loading placeholder
    this.showImagePlaceholder(img);

    try {
      const src = await this.getOptimizedImageSrc(img);
      
      // Create a new image to preload
      const imageLoader = new Image();
      
      imageLoader.onload = () => {
        img.src = src;
        img.classList.remove('lazy', 'loading');
        img.classList.add('loaded');
        this.hideImagePlaceholder(img);
      };
      
      imageLoader.onerror = () => {
        this.handleImageError(img);
      };
      
      imageLoader.src = src;
      
    } catch (error) {
      this.handleImageError(img);
    }
  }

  async getOptimizedImageSrc(img) {
    const originalSrc = img.dataset.src || img.src;
    const devicePixelRatio = window.devicePixelRatio || 1;
    const imgWidth = img.offsetWidth || img.getAttribute('width') || 300;
    const imgHeight = img.offsetHeight || img.getAttribute('height') || 200;
    
    // Calculate optimal dimensions
    const optimalWidth = Math.round(imgWidth * devicePixelRatio);
    const optimalHeight = Math.round(imgHeight * devicePixelRatio);
    
    // Build optimized URL (assuming we have an image service)
    const params = new URLSearchParams({
      w: optimalWidth,
      h: optimalHeight,
      q: 80, // Quality
      f: this.isWebPSupported ? 'webp' : 'auto'
    });
    
    // If we have a CDN or image service, use it
    if (originalSrc.includes('/static/') || originalSrc.includes('/media/')) {
      return `${originalSrc}?${params.toString()}`;
    }
    
    return originalSrc;
  }

  showImagePlaceholder(img) {
    if (img.classList.contains('has-placeholder')) return;
    
    const placeholder = document.createElement('div');
    placeholder.className = 'image-placeholder';
    placeholder.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      animation: loading-shimmer 1.5s infinite;
    `;
    
    // Position image container relatively
    img.style.position = 'relative';
    img.classList.add('loading', 'has-placeholder');
    
    // Insert placeholder
    img.parentNode.insertBefore(placeholder, img.nextSibling);
  }

  hideImagePlaceholder(img) {
    const placeholder = img.parentNode.querySelector('.image-placeholder');
    if (placeholder) {
      placeholder.remove();
    }
    img.classList.remove('has-placeholder');
  }

  handleImageError(img) {
    img.classList.remove('lazy', 'loading');
    img.classList.add('error');
    
    // Try fallback image
    const fallback = img.dataset.fallback || '/static/images/placeholder.svg';
    if (img.src !== fallback) {
      img.src = fallback;
    }
    
    this.hideImagePlaceholder(img);
  }

  setupProgressiveLoading() {
    // Load critical images immediately
    const criticalImages = document.querySelectorAll('img.critical, img[data-critical]');
    criticalImages.forEach(img => {
      this.loadImage(img);
    });
  }

  setupImageErrorHandling() {
    document.addEventListener('error', (e) => {
      if (e.target.tagName === 'IMG') {
        this.handleImageError(e.target);
      }
    }, true);
  }

  optimizeExistingImages() {
    // Add responsive behavior to existing images
    const images = document.querySelectorAll('img:not(.lazy):not([data-src])');
    images.forEach(img => {
      if (!img.hasAttribute('loading')) {
        img.setAttribute('loading', 'lazy');
      }
      
      // Add srcset for responsive images if not present
      if (!img.hasAttribute('srcset') && img.src) {
        this.addResponsiveSrcset(img);
      }
    });
  }

  addResponsiveSrcset(img) {
    const baseSrc = img.src;
    const sizes = [320, 640, 960, 1280, 1920];
    
    const srcsetEntries = sizes.map(size => {
      const params = new URLSearchParams({
        w: size,
        q: 80,
        f: this.isWebPSupported ? 'webp' : 'auto'
      });
      return `${baseSrc}?${params.toString()} ${size}w`;
    });
    
    img.srcset = srcsetEntries.join(', ');
    img.sizes = '(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw';
  }

  loadAllImages() {
    // Fallback for browsers without IntersectionObserver
    const lazyImages = document.querySelectorAll('img[data-src], img.lazy');
    lazyImages.forEach(img => {
      this.loadImage(img);
    });
  }

  // Utility methods
  preloadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = src;
    });
  }

  async preloadCriticalImages() {
    const criticalSrcs = [
      '/static/images/logo.png',
      '/static/images/icon-192.png'
    ];
    
    try {
      await Promise.all(criticalSrcs.map(src => this.preloadImage(src)));
      console.log('Critical images preloaded');
    } catch (error) {
      console.warn('Failed to preload some critical images:', error);
    }
  }

  // Image compression for user uploads
  compressImage(file, maxWidth = 1200, quality = 0.8) {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();
      
      img.onload = () => {
        // Calculate dimensions
        let { width, height } = img;
        
        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }
        
        canvas.width = width;
        canvas.height = height;
        
        // Draw and compress
        ctx.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob(resolve, 'image/jpeg', quality);
      };
      
      img.src = URL.createObjectURL(file);
    });
  }

  // Progressive JPEG simulation
  loadProgressiveImage(img) {
    const src = img.dataset.src || img.src;
    
    // Load low quality first
    const lowQualityParams = new URLSearchParams({
      w: 100,
      q: 30,
      f: 'jpeg'
    });
    
    const lowQualitySrc = `${src}?${lowQualityParams.toString()}`;
    
    const lowQualityImg = new Image();
    lowQualityImg.onload = () => {
      img.src = lowQualitySrc;
      img.style.filter = 'blur(5px)';
      
      // Then load high quality
      const highQualityImg = new Image();
      highQualityImg.onload = () => {
        img.src = src;
        img.style.filter = '';
        img.classList.add('loaded');
      };
      highQualityImg.src = src;
    };
    
    lowQualityImg.src = lowQualitySrc;
  }

  // Background image lazy loading
  setupBackgroundImages() {
    const bgImages = document.querySelectorAll('[data-bg-src]');
    
    if (!('IntersectionObserver' in window)) {
      bgImages.forEach(el => {
        el.style.backgroundImage = `url(${el.dataset.bgSrc})`;
      });
      return;
    }
    
    const bgObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          el.style.backgroundImage = `url(${el.dataset.bgSrc})`;
          el.classList.add('bg-loaded');
          bgObserver.unobserve(el);
        }
      });
    }, this.observerOptions);
    
    bgImages.forEach(el => bgObserver.observe(el));
  }

  // Performance monitoring
  measureImageLoadTime(img) {
    const startTime = performance.now();
    
    img.addEventListener('load', () => {
      const loadTime = performance.now() - startTime;
      console.log(`Image loaded in ${loadTime.toFixed(2)}ms:`, img.src);
      
      // Send to analytics if needed
      if (window.gtag) {
        gtag('event', 'timing_complete', {
          name: 'image_load',
          value: Math.round(loadTime)
        });
      }
    });
  }
}

// CSS for loading animations
const style = document.createElement('style');
style.textContent = `
  @keyframes loading-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
  
  img.loading {
    opacity: 0.7;
  }
  
  img.loaded {
    opacity: 1;
    transition: opacity 0.3s ease;
  }
  
  img.error {
    opacity: 0.5;
    filter: grayscale(100%);
  }
  
  .image-placeholder {
    border-radius: inherit;
  }
  
  .bg-loaded {
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
  }
`;
document.head.appendChild(style);

// Initialize image optimizer
const imageOptimizer = new ImageOptimizer();

// Export for global access
window.imageOptimizer = imageOptimizer;

// Auto-observe new images added to DOM
const mutationObserver = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    mutation.addedNodes.forEach((node) => {
      if (node.nodeType === 1) { // Element node
        const lazyImages = node.querySelectorAll ? 
          node.querySelectorAll('img[data-src], img.lazy') : 
          node.matches && node.matches('img[data-src], img.lazy') ? [node] : [];
        
        lazyImages.forEach(img => {
          if (imageOptimizer.imageObserver) {
            imageOptimizer.imageObserver.observe(img);
          }
        });
        
        const bgImages = node.querySelectorAll ? 
          node.querySelectorAll('[data-bg-src]') : 
          node.matches && node.matches('[data-bg-src]') ? [node] : [];
        
        if (bgImages.length > 0) {
          imageOptimizer.setupBackgroundImages();
        }
      }
    });
  });
});

mutationObserver.observe(document.body, {
  childList: true,
  subtree: true
});