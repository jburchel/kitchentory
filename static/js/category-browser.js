/**
 * Category Browser Component
 * Provides category-based product browsing with infinite scroll
 */

class CategoryBrowser {
    constructor(options = {}) {
        this.container = options.container;
        this.loadMoreButton = options.loadMoreButton;
        this.currentCategory = options.categoryId;
        this.currentPage = 1;
        this.hasNextPage = true;
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        if (!this.container) {
            console.error('CategoryBrowser: Container element not found');
            return;
        }
        
        this.bindEvents();
        this.setupInfiniteScroll();
    }
    
    bindEvents() {
        // Load more button
        if (this.loadMoreButton) {
            this.loadMoreButton.addEventListener('click', () => {
                this.loadMore();
            });
        }
        
        // Category filter clicks
        document.addEventListener('click', (e) => {
            if (e.target.matches('.category-filter')) {
                e.preventDefault();
                const categoryId = e.target.dataset.categoryId;
                this.switchCategory(categoryId);
            }
        });
    }
    
    setupInfiniteScroll() {
        const observer = new IntersectionObserver((entries) => {
            const [entry] = entries;
            if (entry.isIntersecting && this.hasNextPage && !this.isLoading) {
                this.loadMore();
            }
        }, {
            root: null,
            rootMargin: '100px',
            threshold: 0.1
        });
        
        // Observe the last product card
        this.updateObserver(observer);
    }
    
    updateObserver(observer) {
        // Remove previous observations
        observer.disconnect();
        
        // Observe the last product card
        const productCards = this.container.querySelectorAll('.product-card');
        if (productCards.length > 0) {
            const lastCard = productCards[productCards.length - 1];
            observer.observe(lastCard);
        }
    }
    
    async loadMore() {
        if (this.isLoading || !this.hasNextPage) return;
        
        this.isLoading = true;
        this.showLoadingState();
        
        try {
            const nextPage = this.currentPage + 1;
            const response = await fetch(
                `/inventory/search/category/${this.currentCategory}/?page=${nextPage}&format=json`
            );
            
            if (!response.ok) {
                throw new Error('Failed to load products');
            }
            
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                this.appendProducts(data.results);
                this.currentPage = nextPage;
                this.hasNextPage = data.has_next;
            } else {
                this.hasNextPage = false;
            }
            
        } catch (error) {
            console.error('Error loading more products:', error);
            this.showError('Failed to load more products. Please try again.');
        } finally {\n            this.isLoading = false;\n            this.hideLoadingState();\n            \n            // Update infinite scroll observer\n            setTimeout(() => {\n                this.updateObserver(new IntersectionObserver((entries) => {\n                    const [entry] = entries;\n                    if (entry.isIntersecting && this.hasNextPage && !this.isLoading) {\n                        this.loadMore();\n                    }\n                }, {\n                    root: null,\n                    rootMargin: '100px',\n                    threshold: 0.1\n                }));\n            }, 100);\n        }\n    }\n    \n    appendProducts(products) {\n        const productsGrid = this.container.querySelector('.grid');\n        if (!productsGrid) return;\n        \n        products.forEach(product => {\n            const productCard = this.createProductCard(product);\n            productsGrid.appendChild(productCard);\n        });\n    }\n    \n    createProductCard(product) {\n        const card = document.createElement('div');\n        card.className = 'product-card bg-white rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all duration-200 cursor-pointer';\n        card.dataset.productId = product.id;\n        card.dataset.productName = product.name;\n        card.dataset.productBrand = product.brand || '';\n        \n        const imageUrl = product.local_image || product.image_url;\n        const imageHtml = imageUrl ? \n            `<img src=\"${imageUrl}\" alt=\"${product.name}\" class=\"w-full h-32 object-cover\">` :\n            `<div class=\"w-full h-32 flex items-center justify-center\">\n                <svg class=\"w-12 h-12 text-gray-400\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">\n                    <path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4\"></path>\n                </svg>\n            </div>`;\n        \n        card.innerHTML = `\n            <div class=\"aspect-w-16 aspect-h-12 bg-gray-100 rounded-t-lg overflow-hidden\">\n                ${imageHtml}\n            </div>\n            \n            <div class=\"p-4\">\n                <h3 class=\"font-medium text-gray-900 truncate\">\n                    ${product.name}\n                </h3>\n                \n                ${product.brand ? `\n                <p class=\"text-sm text-gray-600 truncate mt-1\">\n                    ${product.brand}\n                </p>\n                ` : ''}\n                \n                <div class=\"mt-3 flex items-center justify-between\">\n                    <div class=\"flex items-center space-x-2\">\n                        ${product.barcode ? `\n                        <span class=\"inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800\">\n                            <svg class=\"w-3 h-3 mr-1\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">\n                                <path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h2M4 4h5m3 0h6m4 0h2M4 20h5M12 4V3M4 4v5m0 11v1m0-1h5m11 4h-1M20 20v-1\"></path>\n                            </svg>\n                            Scannable\n                        </span>\n                        ` : ''}\n                    </div>\n                    \n                    <svg class=\"w-5 h-5 text-gray-400\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">\n                        <path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 4v16m8-8H4\"></path>\n                    </svg>\n                </div>\n            </div>\n        `;\n        \n        // Add click handler\n        card.addEventListener('click', () => {\n            if (window.selectProduct) {\n                window.selectProduct(product.id, product.name, product.brand, product.category);\n            }\n        });\n        \n        return card;\n    }\n    \n    switchCategory(categoryId) {\n        this.currentCategory = categoryId;\n        this.currentPage = 1;\n        this.hasNextPage = true;\n        this.isLoading = false;\n        \n        // Clear current products\n        const productsGrid = this.container.querySelector('.grid');\n        if (productsGrid) {\n            productsGrid.innerHTML = '';\n        }\n        \n        // Load first page of new category\n        this.loadMore();\n    }\n    \n    showLoadingState() {\n        const loadingIndicator = document.createElement('div');\n        loadingIndicator.id = 'category-loading';\n        loadingIndicator.className = 'text-center py-8';\n        loadingIndicator.innerHTML = `\n            <div class=\"inline-flex items-center space-x-2\">\n                <div class=\"animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600\"></div>\n                <span class=\"text-gray-600\">Loading more products...</span>\n            </div>\n        `;\n        \n        this.container.appendChild(loadingIndicator);\n    }\n    \n    hideLoadingState() {\n        const loadingIndicator = document.getElementById('category-loading');\n        if (loadingIndicator) {\n            loadingIndicator.remove();\n        }\n    }\n    \n    showError(message) {\n        const errorElement = document.createElement('div');\n        errorElement.className = 'text-center py-8 text-red-600';\n        errorElement.innerHTML = `\n            <svg class=\"w-8 h-8 mx-auto mb-2\" fill=\"none\" stroke=\"currentColor\" viewBox=\"0 0 24 24\">\n                <path stroke-linecap=\"round\" stroke-linejoin=\"round\" stroke-width=\"2\" d=\"M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z\"></path>\n            </svg>\n            <p class=\"text-sm\">${message}</p>\n        `;\n        \n        this.container.appendChild(errorElement);\n        \n        // Remove error after 5 seconds\n        setTimeout(() => {\n            errorElement.remove();\n        }, 5000);\n    }\n}\n\n// Initialize category browser on page load\ndocument.addEventListener('DOMContentLoaded', function() {\n    const container = document.getElementById('products-container');\n    const categoryId = document.querySelector('[data-category-id]')?.dataset.categoryId;\n    \n    if (container && categoryId) {\n        window.categoryBrowser = new CategoryBrowser({\n            container: container,\n            categoryId: categoryId\n        });\n    }\n});"