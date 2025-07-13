/**
 * Theme Manager for Kitchentory
 * Handles light/dark mode switching with system preference detection
 */

class ThemeManager {
    constructor() {
        this.currentTheme = this.getStoredTheme() || this.getSystemTheme();
        this.init();
    }

    init() {
        // Apply initial theme
        this.applyTheme(this.currentTheme);
        
        // Setup system theme change listener
        this.setupSystemThemeListener();
        
        // Setup theme toggle buttons
        this.setupThemeToggles();
        
        // Expose global methods
        window.ThemeManager = this;
    }

    getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    getStoredTheme() {
        return localStorage.getItem('kitchentory-theme');
    }

    setStoredTheme(theme) {
        localStorage.setItem('kitchentory-theme', theme);
    }

    applyTheme(theme) {
        const root = document.documentElement;
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        
        // Set data attribute for CSS targeting
        root.setAttribute('data-theme', theme);
        
        // Update theme color meta tag for browser UI
        if (metaThemeColor) {
            metaThemeColor.content = theme === 'dark' ? '#1F2937' : '#10B981';
        }
        
        // Update current theme
        this.currentTheme = theme;
        
        // Store preference
        this.setStoredTheme(theme);
        
        // Trigger custom event for other components
        window.dispatchEvent(new CustomEvent('themeChanged', { 
            detail: { theme } 
        }));
        
        // Update toggle button states
        this.updateToggleStates();
        
        // Update status bar style for PWA
        this.updateStatusBarStyle(theme);
    }

    updateStatusBarStyle(theme) {
        const statusBarMeta = document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]');
        if (statusBarMeta) {
            statusBarMeta.content = theme === 'dark' ? 'black' : 'default';
        }
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
        
        // Add haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
        
        return newTheme;
    }

    setupSystemThemeListener() {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addListener((e) => {
            // Only auto-switch if user hasn't manually set a preference
            if (!this.getStoredTheme()) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    }

    setupThemeToggles() {
        // Setup any elements with data-theme-toggle attribute
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-theme-toggle]') || 
                e.target.closest('[data-theme-toggle]')) {
                e.preventDefault();
                this.toggleTheme();
            }
        });
    }

    updateToggleStates() {
        const toggles = document.querySelectorAll('[data-theme-toggle]');
        toggles.forEach(toggle => {
            const icon = toggle.querySelector('.theme-icon');
            const text = toggle.querySelector('.theme-text');
            
            if (icon) {
                // Update icon
                if (this.currentTheme === 'dark') {
                    icon.innerHTML = this.getSunIcon();
                } else {
                    icon.innerHTML = this.getMoonIcon();
                }
            }
            
            if (text) {
                text.textContent = this.currentTheme === 'dark' ? 'Light mode' : 'Dark mode';
            }
            
            // Update ARIA label
            toggle.setAttribute('aria-label', 
                `Switch to ${this.currentTheme === 'dark' ? 'light' : 'dark'} mode`);
        });
    }

    getSunIcon() {
        return `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z">
                </path>
            </svg>
        `;
    }

    getMoonIcon() {
        return `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z">
                </path>
            </svg>
        `;
    }

    // Method to create theme toggle button
    createThemeToggle() {
        const button = document.createElement('button');
        button.setAttribute('data-theme-toggle', '');
        button.className = 'theme-toggle-btn';
        button.innerHTML = `
            <span class="theme-icon">${this.currentTheme === 'dark' ? this.getSunIcon() : this.getMoonIcon()}</span>
            <span class="theme-text sr-only">${this.currentTheme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
        `;
        button.setAttribute('aria-label', `Switch to ${this.currentTheme === 'dark' ? 'light' : 'dark'} mode`);
        
        return button;
    }

    // Alpine.js integration
    alpineData() {
        return {
            theme: this.currentTheme,
            toggle: () => {
                this.theme = this.toggleTheme();
            },
            isDark: () => this.theme === 'dark',
            isLight: () => this.theme === 'light'
        };
    }
}

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});

// Alpine.js global data - Initialize before anything else
document.addEventListener('alpine:init', () => {
    // Get initial theme
    const initialTheme = localStorage.getItem('kitchentory-theme') || 
                        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    
    Alpine.store('theme', {
        current: initialTheme,
        toggle() {
            // Toggle the theme
            this.current = this.current === 'light' ? 'dark' : 'light';
            
            // Store the preference
            localStorage.setItem('kitchentory-theme', this.current);
            
            // Apply the theme to the document
            document.documentElement.setAttribute('data-theme', this.current);
            
            // Update meta theme color
            const metaThemeColor = document.querySelector('meta[name="theme-color"]');
            if (metaThemeColor) {
                metaThemeColor.content = this.current === 'dark' ? '#1F2937' : '#10B981';
            }
            
            // If the full theme manager exists, sync it
            if (window.themeManager && window.themeManager.applyTheme) {
                window.themeManager.currentTheme = this.current;
                window.themeManager.applyTheme(this.current);
            }
            
            // Trigger custom event
            window.dispatchEvent(new CustomEvent('themeChanged', { 
                detail: { theme: this.current } 
            }));
            
            return this.current;
        },
        isDark() {
            return this.current === 'dark';
        },
        isLight() {
            return this.current === 'light';
        }
    });
    
    // Apply initial theme
    document.documentElement.setAttribute('data-theme', initialTheme);
    
    // Update Alpine store when theme changes from other sources
    window.addEventListener('themeChanged', (e) => {
        Alpine.store('theme').current = e.detail.theme;
    });
});

// CSS for theme toggle button
const themeToggleCSS = `
.theme-toggle-btn {
    padding: 8px;
    border-radius: 8px;
    border: none;
    background: var(--color-bg-tertiary);
    color: var(--color-text-secondary);
    transition: all var(--transition-base);
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 44px;
    min-height: 44px;
    cursor: pointer;
}

.theme-toggle-btn:hover {
    background: var(--color-bg-secondary);
    color: var(--color-text-primary);
    transform: scale(1.05);
}

.theme-toggle-btn:active {
    transform: scale(0.95);
}

/* Theme transition animations */
* {
    transition: background-color var(--transition-base), 
                color var(--transition-base), 
                border-color var(--transition-base);
}

/* Smooth theme transition */
.theme-transition {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Auto-hide scrollbars in dark mode for cleaner look */
:root[data-theme="dark"] ::-webkit-scrollbar {
    width: 8px;
}

:root[data-theme="dark"] ::-webkit-scrollbar-track {
    background: var(--color-gray-800);
}

:root[data-theme="dark"] ::-webkit-scrollbar-thumb {
    background: var(--color-gray-600);
    border-radius: 4px;
}

:root[data-theme="dark"] ::-webkit-scrollbar-thumb:hover {
    background: var(--color-gray-500);
}
`;

// Inject CSS
const style = document.createElement('style');
style.textContent = themeToggleCSS;
document.head.appendChild(style);