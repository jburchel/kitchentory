# Developer Account Setup Guide

## Apple Developer Program Setup

### Prerequisites
- Mac computer for iOS development and testing
- Valid Apple ID
- Credit card for $99 annual fee payment
- Business information (if enrolling as organization)

### Enrollment Process

#### Step 1: Choose Account Type
1. Visit [developer.apple.com](https://developer.apple.com)
2. Click "Account" and sign in with Apple ID
3. Choose enrollment type:
   - **Individual**: Personal account ($99/year)
   - **Organization**: Company account ($99/year) - Recommended for Kitchentory

#### Step 2: Complete Registration
1. **Personal Information**:
   - Full legal name
   - Phone number (for verification)
   - Address information
   
2. **Organization Information** (if applicable):
   - Legal entity name
   - D-U-N-S Number (obtain from Dun & Bradstreet if needed)
   - Legal entity type (LLC, Corporation, etc.)
   - Website URL

3. **Agreement Acceptance**:
   - Apple Developer Program License Agreement
   - Terms and conditions

#### Step 3: Identity Verification
- Apple may require phone verification
- Document submission for organization accounts
- Processing time: 24-48 hours for individual, up to 7 days for organization

#### Step 4: Payment
- $99 USD annual fee
- Auto-renewal enabled by default
- Payment methods: Credit card, PayPal

### Post-Enrollment Setup

#### App Store Connect Access
1. Visit [appstoreconnect.apple.com](https://appstoreconnect.apple.com)
2. Accept App Store Connect Terms
3. Set up banking information for revenue
4. Configure tax information (W-9 for US entities)

#### Certificates and Identifiers
1. **App Identifier**:
   - Bundle ID: `com.kitchentory.app`
   - Description: "Kitchentory - Smart Kitchen Management"
   - Capabilities: Push Notifications, Camera, Network Extensions

2. **Development Certificate**:
   - Download and install Xcode
   - Generate Certificate Signing Request (CSR)
   - Create iOS Development certificate

3. **Distribution Certificate**:
   - Create iOS Distribution certificate for App Store releases

4. **Provisioning Profiles**:
   - Development profile for testing
   - Distribution profile for App Store submission

#### App Store Connect App Setup
1. **Create New App**:
   - Platform: iOS
   - Name: "Kitchentory"
   - Bundle ID: com.kitchentory.app
   - SKU: KITCHENTORY001
   - Primary Language: English (U.S.)

2. **App Information**:
   - Subtitle: "Smart Kitchen Management"
   - Categories: Primary (Food & Drink), Secondary (Productivity)
   - Content Rights: Does not use third-party content
   - Age Rating: 4+ (no objectionable content)

3. **Pricing and Availability**:
   - Price: Free (with in-app purchases)
   - Availability: All countries/regions
   - Educational Discount: No

## Google Play Console Setup

### Prerequisites
- Google account
- $25 one-time registration fee
- Valid payment method
- Developer identification (government ID may be required)

### Registration Process

#### Step 1: Create Developer Account
1. Visit [play.google.com/console](https://play.google.com/console)
2. Sign in with Google account
3. Accept Google Play Developer Distribution Agreement
4. Pay $25 registration fee (one-time)

#### Step 2: Account Type Selection
- **Personal Account**: Individual developer
- **Organization Account**: Company/business - Recommended for Kitchentory

#### Step 3: Developer Information
1. **Personal Information**:
   - Full name matching government ID
   - Phone number for verification
   - Country/territory of residence

2. **Organization Information** (if applicable):
   - Organization name
   - Organization type
   - Website URL
   - Contact information

#### Step 4: Identity Verification
- Government-issued ID upload
- Address verification (utility bill or bank statement)
- Processing time: 1-3 business days

### Google Play Console Configuration

#### Account Settings
1. **Developer Profile**:
   - Public developer name: "Kitchentory Team"
   - Website: kitchentory.com
   - Email address for user inquiries

2. **Financial Details**:
   - Set up Google Payments merchant account
   - Bank account information for revenue
   - Tax information and forms

#### App Creation
1. **Create New App**:
   - App name: "Kitchentory: Smart Kitchen Manager"
   - Default language: English (United States)
   - App or game: App
   - Free or paid: Free (with in-app purchases)

2. **Store Settings**:
   - App category: Food & Drink
   - Content rating: Everyone
   - Target audience: General audience
   - Contains ads: No

#### App Signing
1. **Play App Signing**:
   - Let Google manage and protect app signing key
   - Generate upload key for app bundles
   - Configure signing key certificate

## Payment Processing Setup

### Apple App Store In-App Purchases

#### Banking Information
1. **Bank Details**:
   - Bank name and address
   - Account holder name
   - Account number/IBAN
   - SWIFT/BIC code
   - Currency: USD

2. **Tax Information**:
   - Complete appropriate tax forms (W-9 for US)
   - Provide taxpayer identification number
   - Select tax treaty benefits if applicable

#### Product Setup
1. **Subscription Groups**:
   - Group Name: "Kitchentory Premium Plans"
   - Reference Name: "premium_plans"

2. **Auto-Renewable Subscriptions**:
   
   **Premium Monthly**:
   - Product ID: `premium_monthly`
   - Reference Name: "Premium Monthly"
   - Price: $4.99/month
   - Subscription Duration: 1 month
   - Free Trial: 14 days

   **Pro Monthly**:
   - Product ID: `pro_monthly`  
   - Reference Name: "Pro Monthly"
   - Price: $9.99/month
   - Subscription Duration: 1 month
   - Free Trial: 14 days

### Google Play Billing

#### Merchant Account Setup
1. **Google Payments Profile**:
   - Business information
   - Tax information
   - Bank account details
   - Identity verification

#### Subscription Products
1. **Product Configuration**:

   **Premium Monthly**:
   - Product ID: `premium_monthly`
   - Name: "Kitchentory Premium"
   - Price: $4.99/month
   - Billing period: Monthly
   - Free trial: 14 days
   - Grace period: 3 days

   **Pro Monthly**:
   - Product ID: `pro_monthly`
   - Name: "Kitchentory Pro"
   - Price: $9.99/month  
   - Billing period: Monthly
   - Free trial: 14 days
   - Grace period: 3 days

## Content Rating and Compliance

### iOS App Store Review Guidelines
- **Content**: No objectionable material
- **Functionality**: Core features work as described
- **Business Model**: Clear subscription terms
- **Data Collection**: Privacy policy required
- **Third-party Services**: All integrations approved

### Google Play Policy Compliance
- **Content Policy**: Family-friendly content
- **User Data Policy**: Transparent data collection
- **Permissions**: Only request necessary permissions
- **Restricted Content**: No prohibited content types
- **Spam and Minimum Functionality**: Substantial app functionality

## Testing and Distribution

### iOS Testing
1. **TestFlight Setup**:
   - Add internal testers (up to 100)
   - Create beta testing groups
   - Set up external testing (up to 10,000 testers)
   - Configure automatic distribution

2. **Testing Process**:
   - Upload build to App Store Connect
   - Submit for TestFlight review (24-48 hours)
   - Invite testers and collect feedback
   - Iterate based on feedback

### Android Testing
1. **Internal Testing**:
   - Upload app bundle to Play Console
   - Create internal testing track
   - Add internal testers (up to 100)

2. **Closed Testing**:
   - Create alpha/beta testing tracks
   - Add testers via email lists or Google Groups
   - Manage feedback and ratings

3. **Open Testing**:
   - Make app available to anyone with link
   - Collect public feedback before full release

## Launch Preparation Checklist

### Pre-Launch Requirements
- [ ] Developer accounts fully verified and active
- [ ] Payment processing configured and tested
- [ ] App store listings complete with descriptions and screenshots
- [ ] Privacy policy published and linked
- [ ] Terms of service published and linked
- [ ] Customer support email configured
- [ ] App icons created for all required sizes
- [ ] Beta testing completed with 50+ testers
- [ ] App store review guidelines compliance verified
- [ ] All required legal agreements accepted

### Technical Preparations
- [ ] Production API endpoints configured
- [ ] Database backups and monitoring in place  
- [ ] Error tracking and logging implemented
- [ ] Performance monitoring dashboard setup
- [ ] Customer support ticket system ready
- [ ] Documentation for support team created
- [ ] Rollback plan prepared for critical issues

### Marketing Preparations
- [ ] Press release drafted and scheduled
- [ ] Social media accounts created and content planned
- [ ] Influencer outreach list prepared
- [ ] Product Hunt launch scheduled
- [ ] App store optimization keywords researched
- [ ] Launch day communication plan finalized

## Post-Launch Monitoring

### Key Metrics to Track
- **Downloads**: Daily active installs
- **Ratings**: Average rating and review sentiment
- **Crashes**: Crash-free user percentage
- **Revenue**: Subscription conversion rates
- **Retention**: 1-day, 7-day, and 30-day retention
- **Support**: Customer service ticket volume

### Response Planning
- **Review Management**: Respond to reviews within 24 hours
- **Critical Issues**: Emergency patch deployment process
- **Customer Support**: Escalation procedures for complex issues
- **Performance Monitoring**: Alert thresholds and response procedures

This comprehensive setup ensures both Apple and Google developer accounts are properly configured for Kitchentory's successful app store launch and ongoing operations.