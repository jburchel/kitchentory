/*
 * Load test for Kitchentory API endpoints using k6
 * 
 * This test simulates realistic user behavior patterns:
 * - User authentication
 * - Inventory management operations
 * - Recipe browsing and searching
 * - Shopping list management
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');
const apiCalls = new Counter('api_calls');

// Test configuration
export const options = {
    stages: [
        { duration: '2m', target: 10 },  // Ramp up to 10 users
        { duration: '5m', target: 10 },  // Stay at 10 users
        { duration: '2m', target: 20 },  // Ramp up to 20 users
        { duration: '5m', target: 20 },  // Stay at 20 users
        { duration: '2m', target: 0 },   // Ramp down to 0 users
    ],
    thresholds: {
        http_req_duration: ['p(95)<2000'], // 95% of requests must be below 2s
        http_req_failed: ['rate<0.1'],     // Error rate must be below 10%
        errors: ['rate<0.1'],              // Custom error rate below 10%
    },
};

// Configuration
const BASE_URL = __ENV.BASE_URL || 'https://staging.kitchentory.com';
const API_BASE = `${BASE_URL}/api`;

// Test data
const TEST_USERS = [
    { username: 'test_user_1', password: 'test_password_123' },
    { username: 'test_user_2', password: 'test_password_123' },
    { username: 'test_user_3', password: 'test_password_123' },
];

const SAMPLE_PRODUCTS = [
    { name: 'Organic Tomatoes', category: 1, quantity: '5.0', unit: 'pieces' },
    { name: 'Whole Milk', category: 2, quantity: '2.0', unit: 'liters' },
    { name: 'Bread', category: 3, quantity: '1.0', unit: 'loaf' },
    { name: 'Chicken Breast', category: 4, quantity: '1.5', unit: 'kg' },
];

const RECIPE_SEARCHES = [
    'pasta', 'chicken', 'soup', 'salad', 'bread', 'dessert'
];

// Helper functions
function getRandomUser() {
    return TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
}

function getRandomProduct() {
    return SAMPLE_PRODUCTS[Math.floor(Math.random() * SAMPLE_PRODUCTS.length)];
}

function getRandomSearch() {
    return RECIPE_SEARCHES[Math.floor(Math.random() * RECIPE_SEARCHES.length)];
}

function makeRequest(method, url, payload = null, headers = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json',
        ...headers
    };
    
    const params = {
        headers: defaultHeaders,
        timeout: '30s',
    };
    
    let response;
    const startTime = new Date().getTime();
    
    if (method === 'GET') {
        response = http.get(url, params);
    } else if (method === 'POST') {
        response = http.post(url, JSON.stringify(payload), params);
    } else if (method === 'PATCH') {
        response = http.patch(url, JSON.stringify(payload), params);
    } else if (method === 'DELETE') {
        response = http.del(url, null, params);
    }
    
    const endTime = new Date().getTime();
    const duration = endTime - startTime;
    
    // Record metrics
    responseTime.add(duration);
    apiCalls.add(1);
    
    // Check for errors
    const isError = response.status >= 400;
    errorRate.add(isError);
    
    return response;
}

export function setup() {
    // Create test users if they don't exist
    console.log('Setting up test data...');
    
    // Health check
    const healthResponse = makeRequest('GET', `${BASE_URL}/health/`);
    check(healthResponse, {
        'Health check passes': (r) => r.status === 200,
    });
    
    return { baseUrl: BASE_URL };
}

export default function(data) {
    const user = getRandomUser();
    let authToken = null;
    
    // 1. Authentication
    const authResponse = makeRequest('POST', `${API_BASE}/auth/login/`, {
        username: user.username,
        password: user.password
    });
    
    const authSuccess = check(authResponse, {
        'Authentication successful': (r) => r.status === 200,
        'Token received': (r) => r.json('token') !== undefined,
    });
    
    if (authSuccess) {
        authToken = authResponse.json('token');
    } else {
        console.error(`Authentication failed for user ${user.username}`);
        return;
    }
    
    const authHeaders = {
        'Authorization': `Token ${authToken}`
    };
    
    sleep(Math.random() * 2); // Random delay between 0-2 seconds
    
    // 2. Get inventory list
    const inventoryResponse = makeRequest('GET', `${API_BASE}/inventory/`, null, authHeaders);
    check(inventoryResponse, {
        'Inventory list retrieved': (r) => r.status === 200,
        'Inventory data structure valid': (r) => {
            const data = r.json();
            return data.hasOwnProperty('results') && Array.isArray(data.results);
        },
    });
    
    sleep(Math.random() * 1);
    
    // 3. Add inventory item (30% of users)
    if (Math.random() < 0.3) {
        const product = getRandomProduct();
        const addItemResponse = makeRequest('POST', `${API_BASE}/inventory/`, {
            ...product,
            purchase_date: new Date().toISOString().split('T')[0],
            expiration_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        }, authHeaders);
        
        check(addItemResponse, {
            'Inventory item added': (r) => r.status === 201,
        });
        
        sleep(Math.random() * 1);
    }
    
    // 4. Search recipes
    const searchTerm = getRandomSearch();
    const recipeSearchResponse = makeRequest('GET', 
        `${API_BASE}/recipes/search/?q=${searchTerm}`, null, authHeaders);
    
    check(recipeSearchResponse, {
        'Recipe search successful': (r) => r.status === 200,
        'Recipe search results valid': (r) => {
            const data = r.json();
            return data.hasOwnProperty('results') && Array.isArray(data.results);
        },
    });
    
    sleep(Math.random() * 2);
    
    // 5. Get recipe recommendations (50% of users)
    if (Math.random() < 0.5) {
        const recommendationsResponse = makeRequest('GET', 
            `${API_BASE}/recipes/matching/?threshold=70`, null, authHeaders);
        
        check(recommendationsResponse, {
            'Recipe recommendations retrieved': (r) => r.status === 200,
        });
        
        sleep(Math.random() * 1);
    }
    
    // 6. Shopping list operations (40% of users)
    if (Math.random() < 0.4) {
        // Get shopping lists
        const shoppingListsResponse = makeRequest('GET', `${API_BASE}/shopping/lists/`, null, authHeaders);
        check(shoppingListsResponse, {
            'Shopping lists retrieved': (r) => r.status === 200,
        });
        
        const shoppingLists = shoppingListsResponse.json('results') || [];
        
        // Create new shopping list if none exist or randomly
        if (shoppingLists.length === 0 || Math.random() < 0.3) {
            const createListResponse = makeRequest('POST', `${API_BASE}/shopping/lists/`, {
                name: `Test List ${Math.floor(Math.random() * 1000)}`,
                budget_limit: '50.00'
            }, authHeaders);
            
            check(createListResponse, {
                'Shopping list created': (r) => r.status === 201,
            });
            
            sleep(Math.random() * 1);
        }
        
        sleep(Math.random() * 1);
    }
    
    // 7. Get inventory statistics (20% of users)
    if (Math.random() < 0.2) {
        const statsResponse = makeRequest('GET', `${API_BASE}/inventory/statistics/`, null, authHeaders);
        check(statsResponse, {
            'Inventory statistics retrieved': (r) => r.status === 200,
            'Statistics data valid': (r) => {
                const data = r.json();
                return data.hasOwnProperty('total_items') && 
                       data.hasOwnProperty('total_value');
            },
        });
        
        sleep(Math.random() * 1);
    }
    
    // 8. Barcode lookup simulation (10% of users)
    if (Math.random() < 0.1) {
        const barcode = '1234567890123'; // Sample barcode
        const barcodeResponse = makeRequest('GET', 
            `${API_BASE}/inventory/barcode-lookup/?barcode=${barcode}`, null, authHeaders);
        
        check(barcodeResponse, {
            'Barcode lookup completed': (r) => r.status === 200 || r.status === 404,
        });
        
        sleep(Math.random() * 1);
    }
    
    // Random think time between user sessions
    sleep(Math.random() * 3);
}

export function teardown(data) {
    console.log('Load test completed');
    console.log(`Total API calls made: ${apiCalls.count}`);
}

// Helper function to handle errors gracefully
export function handleSummary(data) {
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'load-test-results.json': JSON.stringify(data),
    };
}

function textSummary(data, options = {}) {
    const indent = options.indent || '';
    const enableColors = options.enableColors || false;
    
    let summary = `${indent}Load Test Summary:\n`;
    summary += `${indent}================\n\n`;
    
    // HTTP metrics
    if (data.metrics.http_req_duration) {
        summary += `${indent}HTTP Request Duration:\n`;
        summary += `${indent}  Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
        summary += `${indent}  95th percentile: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
        summary += `${indent}  99th percentile: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n\n`;
    }
    
    // Error rate
    if (data.metrics.http_req_failed) {
        const errorRate = (data.metrics.http_req_failed.values.rate * 100).toFixed(2);
        summary += `${indent}Error Rate: ${errorRate}%\n\n`;
    }
    
    // Custom metrics
    if (data.metrics.api_calls) {
        summary += `${indent}Total API Calls: ${data.metrics.api_calls.values.count}\n`;
    }
    
    if (data.metrics.response_time) {
        summary += `${indent}Custom Response Time Average: ${data.metrics.response_time.values.avg.toFixed(2)}ms\n`;
    }
    
    return summary;
}