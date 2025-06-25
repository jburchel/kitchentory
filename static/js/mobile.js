// Mobile UX Enhancements for Kitchentory
class MobileUX {
  constructor() {
    this.isTouch = 'ontouchstart' in window;
    this.isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    this.isAndroid = /Android/.test(navigator.userAgent);
    this.swipeThreshold = 50;
    this.longPressDelay = 500;
    
    this.init();
  }

  init() {
    if (this.isTouch) {
      this.setupTouchEnhancements();
      this.setupSwipeGestures();
      this.setupPullToRefresh();
      this.setupHapticFeedback();
      this.setupBottomSheets();
      this.setupMobileNavigation();
    }
    
    this.setupResponsiveImages();
    this.setupKeyboardHandling();
  }

  setupTouchEnhancements() {
    // Add touch-friendly classes
    document.body.classList.add('touch-device');
    
    // Enhance button interactions
    document.addEventListener('touchstart', (e) => {
      if (e.target.closest('.touch-button, .tap-feedback')) {
        e.target.style.transform = 'scale(0.98)';
      }
    });

    document.addEventListener('touchend', (e) => {
      if (e.target.closest('.touch-button, .tap-feedback')) {
        setTimeout(() => {
          e.target.style.transform = '';
        }, 100);
      }
    });

    // Prevent accidental double-tap zoom
    let lastTouchEnd = 0;
    document.addEventListener('touchend', (e) => {
      const now = Date.now();
      if (now - lastTouchEnd <= 300) {
        e.preventDefault();
      }
      lastTouchEnd = now;
    }, false);
  }

  setupSwipeGestures() {
    document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
    document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
    document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
  }

  handleTouchStart(e) {
    const touch = e.touches[0];
    this.touchStart = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
      target: e.target
    };
  }

  handleTouchMove(e) {
    if (!this.touchStart) return;

    const touch = e.touches[0];
    const deltaX = touch.clientX - this.touchStart.x;
    const deltaY = touch.clientY - this.touchStart.y;
    
    const swipeZone = e.target.closest('.swipe-zone');
    if (swipeZone) {
      const absDeltaX = Math.abs(deltaX);
      const absDeltaY = Math.abs(deltaY);
      
      // Only handle horizontal swipes
      if (absDeltaX > absDeltaY && absDeltaX > 10) {
        e.preventDefault();
        
        if (deltaX > 0) {
          swipeZone.classList.add('swiping-right');
          swipeZone.classList.remove('swiping-left');
        } else {
          swipeZone.classList.add('swiping-left');
          swipeZone.classList.remove('swiping-right');
        }
        
        // Update visual feedback
        swipeZone.style.transform = `translateX(${deltaX * 0.3}px)`;
      }
    }
  }

  handleTouchEnd(e) {
    if (!this.touchStart) return;

    const touch = e.changedTouches[0];
    const deltaX = touch.clientX - this.touchStart.x;
    const deltaY = touch.clientY - this.touchStart.y;
    const deltaTime = Date.now() - this.touchStart.time;
    
    const absDeltaX = Math.abs(deltaX);
    const absDeltaY = Math.abs(deltaY);
    
    const swipeZone = e.target.closest('.swipe-zone');
    if (swipeZone) {
      swipeZone.style.transform = '';
      swipeZone.classList.remove('swiping-left', 'swiping-right');
      
      // Check if it's a swipe
      if (absDeltaX > this.swipeThreshold && absDeltaX > absDeltaY && deltaTime < 300) {
        if (deltaX > 0) {
          this.triggerSwipeAction(swipeZone, 'right');
        } else {
          this.triggerSwipeAction(swipeZone, 'left');
        }
      }
    }
    
    // Check for long press
    if (deltaTime > this.longPressDelay && absDeltaX < 10 && absDeltaY < 10) {
      this.triggerLongPress(this.touchStart.target);
    }

    this.touchStart = null;
  }

  triggerSwipeAction(element, direction) {
    const action = element.dataset[`swipe${direction.charAt(0).toUpperCase() + direction.slice(1)}`];
    if (action) {
      this.vibrate('light');
      
      // Trigger custom event
      element.dispatchEvent(new CustomEvent('swipe', {
        detail: { direction, action }
      }));
      
      // Execute action
      if (typeof window[action] === 'function') {
        window[action](element);
      }
    }
  }

  triggerLongPress(element) {
    this.vibrate('medium');
    
    element.dispatchEvent(new CustomEvent('longpress', {
      detail: { target: element }
    }));
  }

  setupPullToRefresh() {
    let startY = 0;
    let currentY = 0;
    let pullDistance = 0;
    let isRefreshing = false;
    
    const refreshElements = document.querySelectorAll('.pull-to-refresh');
    
    refreshElements.forEach(element => {
      const indicator = element.querySelector('.pull-refresh-indicator') || this.createRefreshIndicator(element);
      
      element.addEventListener('touchstart', (e) => {
        if (element.scrollTop === 0) {
          startY = e.touches[0].clientY;
        }
      }, { passive: true });
      
      element.addEventListener('touchmove', (e) => {
        if (isRefreshing || element.scrollTop > 0) return;
        
        currentY = e.touches[0].clientY;
        pullDistance = Math.max(0, currentY - startY);
        
        if (pullDistance > 0) {
          const progress = Math.min(pullDistance / 100, 1);
          indicator.style.transform = `translateY(${pullDistance * 0.5}px) scale(${progress})`;
          indicator.style.opacity = progress;
          
          if (pullDistance > 80) {
            indicator.classList.add('visible');
          }
        }
      }, { passive: false });
      
      element.addEventListener('touchend', () => {
        if (pullDistance > 80 && !isRefreshing) {
          this.performRefresh(element, indicator);
        } else {
          this.resetRefreshIndicator(indicator);
        }
        pullDistance = 0;
      });
    });
  }

  createRefreshIndicator(container) {
    const indicator = document.createElement('div');
    indicator.className = 'pull-refresh-indicator';
    indicator.innerHTML = `
      <svg class="w-6 h-6 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
      </svg>
    `;
    container.prepend(indicator);
    return indicator;
  }

  async performRefresh(element, indicator) {
    this.vibrate('light');
    indicator.classList.add('visible');
    
    // Trigger custom refresh event
    const refreshEvent = new CustomEvent('pullrefresh');
    element.dispatchEvent(refreshEvent);
    
    // Simulate refresh or wait for actual refresh
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    this.resetRefreshIndicator(indicator);
  }

  resetRefreshIndicator(indicator) {
    indicator.style.transform = '';
    indicator.style.opacity = '';
    indicator.classList.remove('visible');
  }

  setupHapticFeedback() {
    // Add haptic feedback to elements with haptic classes
    document.addEventListener('click', (e) => {
      const hapticElement = e.target.closest('.haptic-light, .haptic-medium, .haptic-heavy');
      if (hapticElement) {
        if (hapticElement.classList.contains('haptic-light')) {
          this.vibrate('light');
        } else if (hapticElement.classList.contains('haptic-medium')) {
          this.vibrate('medium');
        } else if (hapticElement.classList.contains('haptic-heavy')) {
          this.vibrate('heavy');
        }
      }
    });
  }

  vibrate(type) {
    if (!navigator.vibrate) return;
    
    const patterns = {
      light: 10,
      medium: 50,
      heavy: 100,
      success: [100, 50, 100],
      error: [200, 100, 200]
    };
    
    navigator.vibrate(patterns[type] || patterns.light);
  }

  setupBottomSheets() {
    document.addEventListener('click', (e) => {
      const trigger = e.target.closest('[data-bottom-sheet]');
      if (trigger) {
        const sheetId = trigger.dataset.bottomSheet;
        this.openBottomSheet(sheetId);
      }
      
      if (e.target.closest('.bottom-sheet-backdrop')) {
        this.closeBottomSheet();
      }
    });
    
    // Handle bottom sheet swiping
    document.addEventListener('touchstart', (e) => {
      const sheet = e.target.closest('.bottom-sheet');
      if (sheet && sheet.classList.contains('open')) {
        this.bottomSheetStartY = e.touches[0].clientY;
      }
    });
    
    document.addEventListener('touchmove', (e) => {
      const sheet = e.target.closest('.bottom-sheet');
      if (sheet && sheet.classList.contains('open') && this.bottomSheetStartY) {
        const deltaY = e.touches[0].clientY - this.bottomSheetStartY;
        if (deltaY > 0) {
          sheet.style.transform = `translateY(${deltaY}px)`;
        }
      }
    });
    
    document.addEventListener('touchend', (e) => {
      const sheet = e.target.closest('.bottom-sheet');
      if (sheet && sheet.classList.contains('open') && this.bottomSheetStartY) {
        const deltaY = e.touches[0].clientY - this.bottomSheetStartY;
        if (deltaY > 100) {
          this.closeBottomSheet();
        } else {
          sheet.style.transform = '';
        }
        this.bottomSheetStartY = null;
      }
    });
  }

  openBottomSheet(sheetId) {
    const sheet = document.getElementById(sheetId);
    const backdrop = document.querySelector('.bottom-sheet-backdrop');
    
    if (sheet) {
      sheet.classList.add('open');
      if (backdrop) {
        backdrop.classList.add('open');
      }
      
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
      
      this.vibrate('light');
    }
  }

  closeBottomSheet() {
    const sheets = document.querySelectorAll('.bottom-sheet.open');
    const backdrop = document.querySelector('.bottom-sheet-backdrop.open');
    
    sheets.forEach(sheet => {
      sheet.classList.remove('open');
      sheet.style.transform = '';
    });
    
    if (backdrop) {
      backdrop.classList.remove('open');
    }
    
    // Restore body scroll
    document.body.style.overflow = '';
  }

  setupMobileNavigation() {
    // Add active state management for mobile navigation
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.mobile-nav-item');
    
    navItems.forEach(item => {
      const href = item.getAttribute('href');
      if (href && currentPath.startsWith(href)) {
        item.classList.add('active');
      }
      
      item.addEventListener('click', () => {
        this.vibrate('light');
      });
    });
  }

  setupResponsiveImages() {
    // Implement lazy loading for images
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            observer.unobserve(img);
          }
        });
      });

      document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
      });
    }
  }

  setupKeyboardHandling() {
    // Handle virtual keyboard on mobile
    if (this.isIOS) {
      let initialViewportHeight = window.innerHeight;
      
      window.addEventListener('resize', () => {
        const currentHeight = window.innerHeight;
        const heightDifference = initialViewportHeight - currentHeight;
        
        if (heightDifference > 150) {
          // Keyboard is likely open
          document.body.classList.add('keyboard-open');
          document.body.style.setProperty('--keyboard-height', `${heightDifference}px`);
        } else {
          // Keyboard is likely closed
          document.body.classList.remove('keyboard-open');
          document.body.style.removeProperty('--keyboard-height');
        }
      });
    }
    
    // Auto-scroll to focused inputs
    document.addEventListener('focusin', (e) => {
      if (e.target.matches('input, textarea, select')) {
        setTimeout(() => {
          e.target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 300);
      }
    });
  }

  // Utility methods
  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 left-4 right-4 p-4 rounded-lg text-white z-50 ${
      type === 'success' ? 'bg-green-600' : 
      type === 'error' ? 'bg-red-600' : 
      type === 'warning' ? 'bg-yellow-600' : 'bg-blue-600'
    }`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    this.vibrate(type === 'error' ? 'error' : 'light');
    
    setTimeout(() => {
      toast.remove();
    }, 3000);
  }

  createFAB(icon, action, position = 'bottom-right') {
    const fab = document.createElement('button');
    fab.className = `fab fixed ${position === 'bottom-right' ? 'bottom-20 right-4' : position} z-50`;
    fab.innerHTML = icon;
    fab.addEventListener('click', action);
    
    document.body.appendChild(fab);
    return fab;
  }

  // Smooth scroll utility
  smoothScrollTo(element, offset = 0) {
    const targetPosition = element.offsetTop - offset;
    window.scrollTo({
      top: targetPosition,
      behavior: 'smooth'
    });
  }
}

// Initialize mobile UX enhancements
const mobileUX = new MobileUX();

// Export for global access
window.mobileUX = mobileUX;