# Phase 5: Testing & Production Deployment Guide

## Overview
This guide covers comprehensive testing and production deployment for Kitchentory's subscription system and mobile app preparation. This phase ensures reliability, security, and scalability before launching to paying customers.

## Prerequisites
- Phase 4 completed (PWA and native app wrappers ready)
- Stripe products and Price IDs configured
- Render deployment environment prepared
- Supabase database configured

## Testing Strategy

### 1. Comprehensive Payment Testing

#### Test Environment Setup
```bash
# Set up Stripe test mode
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...

# Create test subscription plans
python manage.py create_subscription_plans --test-mode
```

#### Subscription Flow Testing

**New Subscription Creation**
- [ ] Free user signs up successfully
- [ ] Premium subscription checkout completes
- [ ] Pro subscription checkout completes
- [ ] User receives confirmation email
- [ ] Subscription status updates in database
- [ ] Features unlock immediately after payment

**Plan Upgrades and Downgrades**
- [ ] Free → Premium upgrade works
- [ ] Premium → Pro upgrade works
- [ ] Pro → Premium downgrade works
- [ ] Premium → Free downgrade works
- [ ] Prorations calculated correctly
- [ ] Billing cycles adjusted properly

**Subscription Cancellation**
- [ ] Immediate cancellation works
- [ ] End-of-period cancellation works
- [ ] Features degrade gracefully
- [ ] Data retention follows policy
- [ ] Reactivation within grace period works

**Payment Method Updates**
- [ ] Credit card updates successfully
- [ ] Payment method validation works
- [ ] Failed payment handling works
- [ ] Retry logic functions correctly

#### Webhook Testing

**Critical Webhook Events**
```bash
# Test webhook endpoints locally
stripe listen --forward-to localhost:8000/webhooks/stripe/
```

Test these webhook events:
- [ ] `customer.subscription.created`
- [ ] `customer.subscription.updated`
- [ ] `customer.subscription.deleted`
- [ ] `invoice.payment_succeeded`
- [ ] `invoice.payment_failed`
- [ ] `customer.subscription.trial_will_end`

**Webhook Reliability Testing**
- [ ] Webhook signature verification works
- [ ] Duplicate event handling (idempotency)
- [ ] Failed webhook retry logic
- [ ] Webhook event logging complete
- [ ] Data consistency after webhook processing

#### Mobile Payment Testing

**iOS In-App Purchases**
- [ ] Sandbox environment configured
- [ ] Test subscription purchases
- [ ] Receipt validation works
- [ ] Purchase restoration works
- [ ] Subscription management accessible

**Android Google Play Billing**
- [ ] Test track configured
- [ ] Subscription purchases work
- [ ] License verification works
- [ ] Subscription management accessible
- [ ] Purchase token validation

### 2. Security Testing

#### Authentication & Authorization
- [ ] JWT token validation secure
- [ ] Session management secure
- [ ] Password reset flow secure
- [ ] Social login integrations secure
- [ ] API endpoint authentication works

#### Payment Security
- [ ] No sensitive payment data stored
- [ ] PCI compliance verified
- [ ] HTTPS enforced everywhere
- [ ] Stripe webhook signature validation
- [ ] Payment form security (no card data touches server)

#### Data Protection
- [ ] User data encryption at rest
- [ ] API responses don't leak sensitive data
- [ ] Database access properly restricted
- [ ] Environment variables secure
- [ ] Third-party integrations secure

### 3. Load Testing

#### Database Performance
```bash
# Test database under load
python manage.py test_db_performance --users=1000 --concurrent=50
```

#### API Endpoint Testing
```bash
# Load test critical endpoints
locust -f tests/load/subscription_flows.py --host=https://your-app.onrender.com
```

**Critical Endpoints to Test**
- [ ] User registration/login
- [ ] Subscription checkout
- [ ] Inventory item CRUD
- [ ] Recipe search and matching
- [ ] Shopping list management
- [ ] Stripe webhook processing

**Performance Targets**
- Response time < 500ms for 95th percentile
- Database queries < 100ms average
- Concurrent users: 500+ without degradation
- Memory usage stable under load
- Zero memory leaks during extended runs

## Production Deployment

### 1. Render Configuration

#### Environment Variables Setup
```bash
# Production environment variables (set in Render dashboard)
DEBUG=False
DJANGO_ENV=production
ALLOWED_HOSTS=your-app.onrender.com,yourdomain.com

# Database (Supabase)
DATABASE_URL=postgresql://postgres:PASSWORD@db.pfoizwkexmveytjurgcs.supabase.co:5432/postgres
SUPABASE_URL=https://pfoizwkexmveytjurgcs.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=your-service-key # Get from Supabase dashboard

# Stripe (LIVE keys for production)
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_... # Configure after deployment

# Security
SECRET_KEY=your-production-secret-key-256-chars
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
```

#### Secrets vs Environment Variables
**Store in Secrets (encrypted):**
- DATABASE_URL
- SUPABASE_SERVICE_KEY  
- STRIPE_SECRET_KEY
- SECRET_KEY
- Email passwords

**Store in Environment:**
- DEBUG
- ALLOWED_HOSTS
- SUPABASE_URL
- SUPABASE_ANON_KEY
- STRIPE_PUBLISHABLE_KEY

### 2. Deployment Process

#### Pre-Deployment Checklist
- [ ] All tests passing in CI/CD
- [ ] Database migrations ready
- [ ] Static files optimized
- [ ] Environment variables configured
- [ ] Domain name configured
- [ ] SSL certificate ready
- [ ] Monitoring tools configured

#### Deploy to Render
1. **Connect GitHub Repository**
   - Link your repository to Render
   - Set auto-deploy on main branch
   - Configure build settings

2. **Configure Build Settings**
   - Build Command: (leave empty for Docker)
   - Start Command: (handled by Dockerfile)
   - Environment: Python 3.11

3. **Deploy and Verify**
   ```bash
   # Check deployment logs
   # Verify all services running
   # Test critical user flows
   ```

### 3. Post-Deployment Configuration

#### Stripe Webhook Setup
1. **Create Webhook Endpoint**
   - URL: `https://your-app.onrender.com/webhooks/stripe/`
   - Events: All subscription and payment events
   - Copy webhook secret to environment variables

2. **Test Webhook Delivery**
   ```bash
   # Send test webhook from Stripe dashboard
   # Verify webhook processing in logs
   ```

#### Domain Configuration
1. **Custom Domain Setup**
   - Configure DNS records
   - Set up SSL certificate
   - Update ALLOWED_HOSTS
   - Test HTTPS redirect

#### Monitoring Setup
1. **Sentry Error Tracking**
   - Configure Sentry project
   - Add DSN to environment
   - Test error reporting

2. **Database Monitoring**
   - Supabase dashboard monitoring
   - Query performance tracking
   - Connection pool monitoring

### 4. Data Migration & Seeding

#### Production Database Setup
```bash
# Run on production (Render will auto-run via Dockerfile)
python manage.py migrate

# Create subscription plans with live Stripe Price IDs
python manage.py create_subscription_plans --production

# Create superuser
python manage.py createsuperuser
```

#### Seed Data (Optional)
```bash
# Add sample categories, storage locations
python manage.py seed_initial_data

# Import popular recipes (if applicable)
python manage.py import_recipes --source=featured
```

## Quality Assurance

### 1. User Acceptance Testing

#### Test User Personas
**Free User Journey**
- [ ] Sign up and onboard
- [ ] Add 5-10 inventory items
- [ ] Search for recipes (hit daily limit)
- [ ] Create shopping list (hit limit)
- [ ] Encounter upgrade prompts
- [ ] View pricing page

**Premium User Journey**  
- [ ] Upgrade from free to premium
- [ ] Access unlimited inventory
- [ ] Use advanced recipe matching
- [ ] Create multiple shopping lists
- [ ] Access basic analytics
- [ ] Manage subscription

**Pro User Journey**
- [ ] Upgrade to pro tier
- [ ] Access all premium features
- [ ] Use advanced analytics
- [ ] Export data functionality
- [ ] Priority support access

#### Device Testing Matrix
- [ ] iPhone 12/13/14 (iOS 15+)
- [ ] iPhone SE (small screen)
- [ ] iPad (tablet layout)
- [ ] Android phones (Samsung, Pixel)
- [ ] Android tablets
- [ ] Desktop browsers (Chrome, Safari, Firefox)

### 2. Performance Monitoring

#### Key Metrics Dashboard
**Application Performance**
- Response time (95th percentile < 500ms)
- Error rate (< 0.1%)
- Database query time (avg < 100ms)
- Memory usage (stable)
- CPU utilization (< 70%)

**Business Metrics**
- Subscription conversion rate
- Payment success rate
- User retention (1d, 7d, 30d)
- Feature usage by tier
- Support ticket volume

#### Alerting Setup
```python
# Configure alerts for:
# - High error rate (> 1%)
# - Slow response times (> 2s)
# - Failed payments (> 5%)
# - Database connection issues
# - Memory/CPU thresholds exceeded
```

### 3. Customer Support Preparation

#### Support Documentation
- [ ] Billing FAQ
- [ ] Feature usage guides
- [ ] Troubleshooting guides
- [ ] Refund policy
- [ ] Subscription management guide

#### Support Tools
- [ ] Help desk software configured
- [ ] User lookup tools
- [ ] Subscription management tools
- [ ] Issue escalation process
- [ ] Response time targets set

## Launch Strategy

### 1. Gradual Rollout Plan

#### Phase 1: Internal Testing (1 week)
- Team members and close friends
- 10-20 test users
- Full feature testing
- Bug fixes and polish

#### Phase 2: Closed Beta (2 weeks)
- Invite 100 beta users
- Email existing user list
- Collect feedback
- Monitor system performance

#### Phase 3: Public Launch (1 week prep)
- Open registration
- Marketing campaigns
- Social media announcement
- Product Hunt launch

### 2. Launch Day Checklist

#### 24 Hours Before
- [ ] All systems green
- [ ] Support team briefed
- [ ] Monitoring alerts configured
- [ ] Emergency contacts available
- [ ] Rollback plan ready

#### Launch Day
- [ ] Monitor system performance
- [ ] Watch error rates
- [ ] Track user registrations
- [ ] Respond to support requests
- [ ] Monitor social media
- [ ] Be ready for scaling issues

#### 48 Hours After
- [ ] Review performance metrics
- [ ] Analyze user feedback
- [ ] Plan immediate fixes
- [ ] Celebrate success! 🎉

## Risk Management

### 1. Common Issues & Solutions

**Payment Processing Issues**
- Webhook delivery failures → Retry logic + manual reconciliation
- Stripe rate limits → Implement exponential backoff
- Currency/tax complications → Start with USD only

**Performance Issues**
- Database slowdowns → Query optimization + caching
- High memory usage → Profile and optimize Django views
- Slow API responses → Add Redis caching layer

**User Experience Issues**
- Confusing upgrade flows → A/B test different approaches
- Mobile app approval delays → Focus on PWA initially
- Feature discovery problems → Add onboarding tutorials

### 2. Emergency Procedures

**Payment System Down**
1. Switch to maintenance mode
2. Notify users via status page
3. Contact Stripe support
4. Implement temporary workarounds
5. Communicate timeline to users

**Database Issues**
1. Check Supabase status
2. Review recent migrations
3. Scale database resources if needed
4. Restore from backup if necessary
5. Document incident for post-mortem

## Success Metrics

### Technical Milestones
- [ ] 99.9% uptime in first month
- [ ] < 0.5% payment failure rate
- [ ] Sub-second average response times
- [ ] Zero security incidents
- [ ] Successful mobile app deployments

### Business Milestones
- [ ] First 100 paying customers
- [ ] $1,000 Monthly Recurring Revenue (MRR)
- [ ] 80%+ customer satisfaction score
- [ ] 90%+ payment success rate
- [ ] Positive app store reviews (4.0+ stars)

## Next Steps After Phase 5

Once Phase 5 is complete and the system is stable in production:

1. **Phase 6: Post-Launch Optimization**
   - A/B test pricing strategies
   - Optimize conversion funnels
   - Implement customer success campaigns

2. **Feature Expansion**
   - Voice input integration
   - Receipt scanning with OCR
   - Advanced AI recommendations

3. **Scale Preparation**
   - Auto-scaling configuration
   - Database optimization
   - CDN implementation

This comprehensive testing and deployment strategy ensures Kitchentory launches successfully with a robust, scalable foundation for growth.