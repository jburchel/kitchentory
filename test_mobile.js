const puppeteer = require('puppeteer');

async function testMobile() {
    console.log('🚀 Starting mobile test...');
    
    const browser = await puppeteer.launch({
        headless: false, // Show browser window
        defaultViewport: null,
        args: ['--start-maximized']
    });
    
    const page = await browser.newPage();
    
    // Set mobile viewport (iPhone 12 Pro)
    await page.setViewport({
        width: 390,
        height: 844,
        deviceScaleFactor: 3,
        isMobile: true,
        hasTouch: true,
        isLandscape: false
    });
    
    // Set user agent for mobile
    await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1');
    
    try {
        // Navigate to your app
        console.log('📱 Loading app in mobile view...');
        await page.goto('http://localhost:8000', { waitUntil: 'networkidle0' });
        
        // Take screenshot
        await page.screenshot({ 
            path: 'mobile-test-home.png', 
            fullPage: true 
        });
        console.log('📸 Screenshot saved: mobile-test-home.png');
        
        // Test navigation if logged in
        const loginButton = await page.$('a[href*="login"]');
        if (loginButton) {
            console.log('🔐 Not logged in, testing login page...');
            await loginButton.click();
            await page.waitForNavigation();
            await page.screenshot({ 
                path: 'mobile-test-login.png', 
                fullPage: true 
            });
            console.log('📸 Login screenshot saved: mobile-test-login.png');
        } else {
            console.log('✅ Already logged in, testing dashboard...');
            
            // Test inventory page
            const inventoryLink = await page.$('a[href*="inventory"]');
            if (inventoryLink) {
                await inventoryLink.click();
                await page.waitForNavigation();
                await page.screenshot({ 
                    path: 'mobile-test-inventory.png', 
                    fullPage: true 
                });
                console.log('📸 Inventory screenshot saved: mobile-test-inventory.png');
            }
            
            // Test recipes page
            await page.goto('http://localhost:8000/recipes/');
            await page.screenshot({ 
                path: 'mobile-test-recipes.png', 
                fullPage: true 
            });
            console.log('📸 Recipes screenshot saved: mobile-test-recipes.png');
        }
        
        console.log('✅ Mobile test completed!');
        console.log('📱 Screenshots saved in current directory');
        
    } catch (error) {
        console.error('❌ Error during mobile test:', error);
    }
    
    // Keep browser open for manual testing
    console.log('🔍 Browser staying open for manual testing...');
    console.log('💡 Press Ctrl+C to close when done');
}

testMobile().catch(console.error);