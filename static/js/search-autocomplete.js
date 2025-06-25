/**
 * Search Autocomplete Component
 * Provides intelligent product search with fuzzy matching and recent searches
 */

class SearchAutocomplete {
    constructor(options = {}) {
        this.inputElement = options.input;
        this.resultsContainer = options.resultsContainer;
        this.onSelect = options.onSelect || (() => {});
        this.minQueryLength = options.minQueryLength || 2;
        this.debounceDelay = options.debounceDelay || 300;
        this.maxResults = options.maxResults || 10;
        
        // Recent searches storage
        this.recentSearches = this.loadRecentSearches();
        this.maxRecentSearches = 5;
        
        // State
        this.currentQuery = '';
        this.isVisible = false;
        this.selectedIndex = -1;
        this.searchTimeout = null;
        
        this.init();
    }
    
    init() {
        if (!this.inputElement || !this.resultsContainer) {
            console.error('SearchAutocomplete: Required elements not found');
            return;
        }
        
        this.bindEvents();
        this.setupStyles();
    }
    
    bindEvents() {
        // Input events
        this.inputElement.addEventListener('input', (e) => {
            this.handleInput(e.target.value);
        });
        
        this.inputElement.addEventListener('focus', () => {
            if (this.currentQuery.length >= this.minQueryLength) {
                this.showResults();
            } else {
                this.showRecentSearches();
            }
        });
        
        this.inputElement.addEventListener('blur', (e) => {
            // Delay hiding to allow click events on results
            setTimeout(() => {
                this.hideResults();
            }, 150);
        });
        
        // Keyboard navigation
        this.inputElement.addEventListener('keydown', (e) => {
            this.handleKeydown(e);
        });
        
        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!this.inputElement.contains(e.target) && 
                !this.resultsContainer.contains(e.target)) {
                this.hideResults();
            }
        });
    }
    
    setupStyles() {
        // Ensure results container is positioned correctly
        this.resultsContainer.style.position = 'absolute';
        this.resultsContainer.style.zIndex = '1000';
        this.resultsContainer.style.width = '100%';
        this.resultsContainer.style.display = 'none';
    }
    
    handleInput(value) {
        this.currentQuery = value.trim();
        
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        // Reset selection
        this.selectedIndex = -1;
        
        if (this.currentQuery.length < this.minQueryLength) {
            if (this.currentQuery.length === 0) {
                this.showRecentSearches();
            } else {
                this.hideResults();
            }
            return;
        }
        
        // Debounce search
        this.searchTimeout = setTimeout(() => {
            this.performSearch(this.currentQuery);
        }, this.debounceDelay);
    }
    
    async performSearch(query) {
        try {
            // Show loading state
            this.showLoading();
            
            const response = await fetch(`/inventory/search/?q=${encodeURIComponent(query)}&format=html`);
            const html = await response.text();
            
            this.displayResults(html);
            this.showResults();
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Search failed. Please try again.');
        }
    }
    
    displayResults(html) {
        this.resultsContainer.innerHTML = html;
        
        // Bind click events to results
        const resultItems = this.resultsContainer.querySelectorAll('[onclick*=\"selectProduct\"]');
        resultItems.forEach((item, index) => {
            item.addEventListener('mouseenter', () => {
                this.selectedIndex = index;
                this.updateSelection();
            });
        });
    }
    
    showRecentSearches() {
        if (this.recentSearches.length === 0) {
            this.hideResults();
            return;
        }
        
        const html = this.generateRecentSearchesHTML();
        this.resultsContainer.innerHTML = html;
        this.showResults();
    }
    
    generateRecentSearchesHTML() {
        let html = '<div class=\"bg-white border border-gray-200 rounded-lg shadow-lg\">';\n        html += '<div class=\"px-4 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b\">Recent Searches</div>';\n        \n        this.recentSearches.forEach((search, index) => {\n            html += `\n                <div class=\"px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0\"\n                     onclick=\"this.selectRecentSearch('${search.query}')\">\n                    <div class=\"flex items-center justify-between\">\n                        <div class=\"flex items-center space-x-3\">\n                            <svg class=\"w-4 h-4 text-gray-400\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">\n                                <path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z\"></path>\n                            </svg>\n                            <span class=\"text-sm text-gray-700\">${search.query}</span>\n                        </div>\n                        <button class=\"text-gray-400 hover:text-gray-600\" onclick=\"event.stopPropagation(); this.removeRecentSearch(${index})\">\n                            <svg class=\"w-4 h-4\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">\n                                <path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M6 18L18 6M6 6l12 12\"></path>\n                            </svg>\n                        </button>\n                    </div>\n                </div>\n            `;\n        });\n        \n        html += '</div>';\n        return html;\n    }\n    \n    selectRecentSearch(query) {\n        this.inputElement.value = query;\n        this.handleInput(query);\n    }\n    \n    removeRecentSearch(index) {\n        this.recentSearches.splice(index, 1);\n        this.saveRecentSearches();\n        this.showRecentSearches();\n    }\n    \n    showLoading() {\n        this.resultsContainer.innerHTML = `\n            <div class=\"bg-white border border-gray-200 rounded-lg shadow-lg p-4\">\n                <div class=\"flex items-center justify-center space-x-2\">\n                    <div class=\"animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600\"></div>\n                    <span class=\"text-sm text-gray-600\">Searching...</span>\n                </div>\n            </div>\n        `;\n        this.showResults();\n    }\n    \n    showError(message) {\n        this.resultsContainer.innerHTML = `\n            <div class=\"bg-white border border-gray-200 rounded-lg shadow-lg p-4\">\n                <div class=\"text-center text-red-600\">\n                    <svg class=\"w-8 h-8 mx-auto mb-2\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">\n                        <path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z\"></path>\n                    </svg>\n                    <p class=\"text-sm\">${message}</p>\n                </div>\n            </div>\n        `;\n        this.showResults();\n    }\n    \n    showResults() {\n        this.resultsContainer.style.display = 'block';\n        this.isVisible = true;\n    }\n    \n    hideResults() {\n        this.resultsContainer.style.display = 'none';\n        this.isVisible = false;\n        this.selectedIndex = -1;\n    }\n    \n    handleKeydown(e) {\n        if (!this.isVisible) return;\n        \n        const items = this.resultsContainer.querySelectorAll('[onclick*=\"selectProduct\"], [onclick*=\"selectRecentSearch\"]');\n        \n        switch (e.key) {\n            case 'ArrowDown':\n                e.preventDefault();\n                this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);\n                this.updateSelection();\n                break;\n                \n            case 'ArrowUp':\n                e.preventDefault();\n                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);\n                this.updateSelection();\n                break;\n                \n            case 'Enter':\n                e.preventDefault();\n                if (this.selectedIndex >= 0 && items[this.selectedIndex]) {\n                    items[this.selectedIndex].click();\n                }\n                break;\n                \n            case 'Escape':\n                this.hideResults();\n                this.inputElement.blur();\n                break;\n        }\n    }\n    \n    updateSelection() {\n        const items = this.resultsContainer.querySelectorAll('[onclick*=\"selectProduct\"], [onclick*=\"selectRecentSearch\"]');\n        \n        items.forEach((item, index) => {\n            if (index === this.selectedIndex) {\n                item.classList.add('bg-blue-50');\n                item.scrollIntoView({ block: 'nearest' });\n            } else {\n                item.classList.remove('bg-blue-50');\n            }\n        });\n    }\n    \n    addToRecentSearches(query) {\n        // Remove if already exists\n        this.recentSearches = this.recentSearches.filter(item => item.query !== query);\n        \n        // Add to beginning\n        this.recentSearches.unshift({\n            query: query,\n            timestamp: Date.now()\n        });\n        \n        // Limit size\n        this.recentSearches = this.recentSearches.slice(0, this.maxRecentSearches);\n        \n        this.saveRecentSearches();\n    }\n    \n    loadRecentSearches() {\n        try {\n            const stored = localStorage.getItem('kitchentory_recent_searches');\n            return stored ? JSON.parse(stored) : [];\n        } catch (error) {\n            console.error('Error loading recent searches:', error);\n            return [];\n        }\n    }\n    \n    saveRecentSearches() {\n        try {\n            localStorage.setItem('kitchentory_recent_searches', JSON.stringify(this.recentSearches));\n        } catch (error) {\n            console.error('Error saving recent searches:', error);\n        }\n    }\n    \n    // Public method to trigger search from external code\n    search(query) {\n        this.inputElement.value = query;\n        this.handleInput(query);\n    }\n    \n    // Public method to clear the search\n    clear() {\n        this.inputElement.value = '';\n        this.currentQuery = '';\n        this.hideResults();\n    }\n}\n\n// Global function for product selection (called from HTML)\nwindow.selectProduct = function(id, name, brand, category) {\n    // Add to recent searches\n    const searchInstance = window.currentSearchInstance;\n    if (searchInstance) {\n        searchInstance.addToRecentSearches(searchInstance.currentQuery);\n        searchInstance.hideResults();\n    }\n    \n    // Fill form fields\n    const nameField = document.getElementById('id_name');\n    const brandField = document.getElementById('id_brand');\n    const categoryField = document.getElementById('id_category');\n    \n    if (nameField) nameField.value = name;\n    if (brandField && brand) brandField.value = brand;\n    \n    // Try to select category if it exists\n    if (categoryField && category) {\n        const options = categoryField.querySelectorAll('option');\n        for (let option of options) {\n            if (option.textContent.trim() === category) {\n                option.selected = true;\n                break;\n            }\n        }\n    }\n    \n    // Trigger change events\n    [nameField, brandField, categoryField].forEach(field => {\n        if (field) field.dispatchEvent(new Event('change', { bubbles: true }));\n    });\n    \n    // Show success notification\n    showNotification(`Selected: ${brand ? brand + ' - ' : ''}${name}`, 'success');\n};\n\n// Utility function for notifications\nfunction showNotification(message, type = 'info') {\n    const toast = document.createElement('div');\n    toast.className = `fixed top-20 right-4 z-50 max-w-sm p-4 rounded-lg shadow-lg transition-all duration-300 transform translate-x-full ${\n        type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :\n        type === 'warning' ? 'bg-yellow-100 text-yellow-800 border border-yellow-200' :\n        type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :\n        'bg-blue-100 text-blue-800 border border-blue-200'\n    }`;\n    \n    toast.innerHTML = `\n        <div class=\"flex items-center\">\n            <svg class=\"w-5 h-5 mr-2\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">\n                ${type === 'success' ? '<path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z\"></path>' :\n                  type === 'warning' ? '<path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z\"></path>' :\n                  '<path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z\"></path>'}\n            </svg>\n            <span class=\"text-sm font-medium\">${message}</span>\n        </div>\n    `;\n    \n    document.body.appendChild(toast);\n    \n    // Animate in\n    setTimeout(() => {\n        toast.classList.remove('translate-x-full');\n    }, 100);\n    \n    // Auto-remove\n    setTimeout(() => {\n        toast.classList.add('translate-x-full');\n        setTimeout(() => {\n            if (document.body.contains(toast)) {\n                document.body.removeChild(toast);\n            }\n        }, 300);\n    }, 3000);\n}"