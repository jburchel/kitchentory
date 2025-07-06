# Kitchentory Design Specification

## Design Principles

### Core Principles

1. **Mobile-First**: Every interface designed for thumb-friendly mobile use
2. **Speed**: Instant feedback, optimistic updates, minimal loading states
3. **Clarity**: Clear visual hierarchy, obvious actions, minimal cognitive load
4. **Flexibility**: Accommodates different user workflows and preferences
5. **Accessibility**: WCAG 2.1 AA compliant, screen reader friendly

### Visual Design Philosophy

- Clean, modern interface with ample whitespace
- Food-inspired color palette with green accents
- Card-based layouts for scannable content
- Consistent iconography from Heroicons
- Typography optimized for readability

## Information Architecture

### Site Structure
```
/ (Dashboard)
├── /inventory
│   ├── /add (Scanner/Search)
│   ├── /categories
│   ├── /item/:id
│   └── /expiring
├── /recipes
│   ├── /discover
│   ├── /browse
│   ├── /recipe/:id
│   ├── /cooking/:id
│   └── /collections
├── /shopping
│   ├── /lists
│   ├── /list/:id
│   └── /history
├── /profile
│   ├── /settings
│   ├── /household
│   └── /preferences
└── /auth
    ├── /login
    ├── /register
    └── /reset-password
```

### Navigation Patterns

- **Mobile**: Fixed bottom navigation with 5 main sections
- **Desktop**: Responsive sidebar with expanded navigation
- **Quick Actions**: Floating action button for primary tasks
- **Breadcrumbs**: Contextual navigation for deeper pages

## Component Design System

### Color Palette
```css
/* Primary Colors */
--primary-green: #10B981;      /* Main brand color */
--primary-dark: #059669;       /* Hover states */
--primary-light: #34D399;      /* Backgrounds */

/* Neutral Colors */
--gray-900: #111827;           /* Primary text */
--gray-700: #374151;           /* Secondary text */
--gray-500: #6B7280;           /* Muted text */
--gray-300: #D1D5DB;           /* Borders */
--gray-100: #F3F4F6;           /* Backgrounds */
--white: #FFFFFF;              /* Base background */

/* Semantic Colors */
--success: #10B981;            /* Success states */
--warning: #F59E0B;            /* Expiring items */
--danger: #EF4444;             /* Errors, expired */
--info: #3B82F6;               /* Information */

/* Category Colors */
--produce: #84CC16;            /* Fruits, vegetables */
--dairy: #60A5FA;              /* Dairy products */
--meat: #F87171;               /* Meat, poultry */
--pantry: #FBBF24;             /* Dry goods */
--frozen: #A78BFA;             /* Frozen items */
```

### Typography

```css
/* Font Stack */
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
             "Helvetica Neue", Arial, sans-serif;

/* Font Sizes */
--text-xs: 0.75rem;     /* 12px - Labels, captions */
--text-sm: 0.875rem;    /* 14px - Secondary text */
--text-base: 1rem;      /* 16px - Body text */
--text-lg: 1.125rem;    /* 18px - Emphasized text */
--text-xl: 1.25rem;     /* 20px - Section headers */
--text-2xl: 1.5rem;     /* 24px - Page titles */
--text-3xl: 1.875rem;   /* 30px - Hero text */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### Spacing System

```css
/* Spacing Scale (rem) */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
```

## Page Layouts

### Dashboard

```
┌─────────────────────────────────┐
│ Welcome, [Name]      [Avatar]   │ Header
├─────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ │
│ │ Quick Stats │ │ Quick Stats │ │ Stats Cards
│ └─────────────┘ └─────────────┘ │
├─────────────────────────────────┤
│ Expiring Soon                   │ Section Header
│ ┌─────────────────────────────┐ │
│ │ [Item] [Item] [Item] →      │ │ Horizontal Scroll
│ └─────────────────────────────┘ │
├─────────────────────────────────┤
│ Recent Recipes                  │
│ ┌──────┐ ┌──────┐ ┌──────┐    │ Recipe Cards
│ │      │ │      │ │      │    │
│ └──────┘ └──────┘ └──────┘    │
├─────────────────────────────────┤
│ [+] Quick Add Button            │ FAB
└─────────────────────────────────┘
```

### Inventory List

```
┌─────────────────────────────────┐
│ [<] Inventory      [Search] [⋮] │ Header
├─────────────────────────────────┤
│ [All] [Fridge] [Pantry] [...]   │ Filter Tabs
├─────────────────────────────────┤
│ ┌─────────────────────────────┐ │
│ │ [IMG] Item Name        [>]  │ │ Item Card
│ │       Qty • Expires in 3d   │ │
│ └─────────────────────────────┘ │
│ ┌─────────────────────────────┐ │
│ │ [IMG] Item Name        [>]  │ │
│ │       Qty • Location        │ │
│ └─────────────────────────────┘ │
├─────────────────────────────────┤
│ [+] Add Item                    │ FAB
└─────────────────────────────────┘
```

### Recipe Discovery

```
┌─────────────────────────────────┐
│ Recipe Discovery                │ Header
├─────────────────────────────────┤
│ ┌─────────────────────────────┐ │
│ │ You can make 12 recipes now │ │ Hero Card
│ │ [View All →]                │ │
│ └─────────────────────────────┘ │
├─────────────────────────────────┤
│ Almost There (2 items away)     │
│ ┌────────┐ ┌────────┐          │ Recipe Grid
│ │ [IMG]  │ │ [IMG]  │          │
│ │ Title  │ │ Title  │          │
│ │ 30 min │ │ 45 min │          │
│ └────────┘ └────────┘          │
└─────────────────────────────────┘
```

## Component Library

### Cards

```html
<!-- Inventory Item Card -->
<div class="card">
  <img class="card-image" src="..." alt="...">
  <div class="card-content">
    <h3 class="card-title">Milk</h3>
    <p class="card-meta">2L • Fridge • Expires in 3 days</p>
  </div>
  <button class="card-action">→</button>
</div>

<!-- Recipe Card -->
<div class="recipe-card">
  <img class="recipe-image" src="..." alt="...">
  <div class="recipe-content">
    <span class="recipe-badge">Ready to make</span>
    <h3 class="recipe-title">Spaghetti Carbonara</h3>
    <div class="recipe-meta">
      <span>30 min</span>
      <span>4 servings</span>
      <span>Italian</span>
    </div>
  </div>
</div>
```

### Forms

```html
<!-- Search Input -->
<div class="search-container">
  <input type="search" 
         class="search-input" 
         placeholder="Search items...">
  <button class="search-button">
    <svg><!-- search icon --></svg>
  </button>
</div>

<!-- Quantity Input -->
<div class="quantity-input">
  <button class="qty-decrease">-</button>
  <input type="number" class="qty-value" value="1">
  <button class="qty-increase">+</button>
</div>
```

### Navigation
```html
<!-- Mobile Bottom Nav -->
<nav class="bottom-nav">
  <a class="nav-item active">
    <svg><!-- icon --></svg>
    <span>Home</span>
  </a>
  <a class="nav-item">
    <svg><!-- icon --></svg>
    <span>Inventory</span>
  </a>
  <button class="nav-fab">+</button>
  <a class="nav-item">
    <svg><!-- icon --></svg>
    <span>Recipes</span>
  </a>
  <a class="nav-item">
    <svg><!-- icon --></svg>
    <span>Shopping</span>
  </a>
</nav>
```

## Interactive Elements

### Barcode Scanner

```
┌─────────────────────────────────┐
│ [X] Scan Barcode                │
├─────────────────────────────────┤
│                                 │
│   ┌───────────────────────┐     │
│   │                       │     │ Camera View
│   │    [Scanning Area]    │     │
│   │                       │     │
│   └───────────────────────┘     │
│                                 │
│ Point at barcode to scan        │
├─────────────────────────────────┤
│ [Enter Manually]                │
└─────────────────────────────────┘
```

### Cooking Mode

```
┌─────────────────────────────────┐
│ [X] Cooking: Pasta Carbonara    │
├─────────────────────────────────┤
│ Step 3 of 8                     │ Progress
├─────────────────────────────────┤
│                                 │
│ Cook pasta according to         │ Step Content
│ package directions until        │
│ al dente                        │
│                                 │
│ [Timer: 8:00]                   │ Timer
│                                 │
├─────────────────────────────────┤
│ Ingredients for this step:      │
│ ☐ 400g Spaghetti               │ Checklist
│ ☐ Salt for water               │
├─────────────────────────────────┤
│ [← Previous]      [Next Step →] │
└─────────────────────────────────┘
```

## Responsive Breakpoints

### Breakpoint System

```css
/* Mobile First Approach */
--screen-sm: 640px;   /* Small tablets */
--screen-md: 768px;   /* Tablets */
--screen-lg: 1024px;  /* Desktop */
--screen-xl: 1280px;  /* Large desktop */
```

### Layout Adaptations

- **Mobile (< 640px)**: Single column, bottom navigation
- **Tablet (640px - 1024px)**: 2 column grids, side navigation
- **Desktop (> 1024px)**: 3-4 column grids, expanded sidebar

## Animation & Transitions

### Micro-interactions

```css
/* Standard Transitions */
--transition-fast: 150ms ease-in-out;
--transition-base: 200ms ease-in-out;
--transition-slow: 300ms ease-in-out;

/* Animation Examples */
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.button:active {
  transform: scale(0.95);
}

/* Loading States */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### Page Transitions

- Slide transitions between main sections
- Fade in/out for modal overlays
- Smooth scroll for anchor links
- Skeleton screens while loading

## Accessibility Guidelines

### WCAG 2.1 AA Compliance

- Minimum contrast ratio 4.5:1 for normal text
- Minimum contrast ratio 3:1 for large text
- All interactive elements keyboard accessible
- Focus indicators on all focusable elements
- ARIA labels for icon-only buttons

### Screen Reader Support

```html
<!-- Accessible Card Example -->
<article class="card" role="article" aria-label="Inventory item">
  <img src="..." alt="Milk carton">
  <h3>Whole Milk</h3>
  <p>
    <span class="sr-only">Quantity:</span> 2 liters
    <span class="sr-only">Location:</span> Fridge
    <span class="sr-only">Status:</span> Expires in 3 days
  </p>
</article>
```

## Performance Considerations

### Image Optimization

- Lazy load images below the fold
- Use WebP format with JPEG fallback
- Responsive images with srcset
- Blur-up technique for progressive loading

### Code Splitting

- Route-based code splitting
- Lazy load heavy components (scanner, charts)
- Preload critical resources
- Service worker for offline functionality

### Caching Strategy

- Cache static assets aggressively
- API response caching with invalidation
- Optimistic UI updates
- Background sync for offline actions

## Error States & Empty States

### Error Handling

```html
<!-- Error Message Component -->
<div class="error-state">
  <svg class="error-icon"><!-- error icon --></svg>
  <h3>Something went wrong</h3>
  <p>We couldn't load your inventory. Please try again.</p>
  <button class="retry-button">Retry</button>
</div>
```

### Empty States

```html
<!-- Empty Inventory -->
<div class="empty-state">
  <svg class="empty-icon"><!-- empty box icon --></svg>
  <h3>Your inventory is empty</h3>
  <p>Start by adding items to track what's in your kitchen</p>
  <button class="primary-button">Add Your First Item</button>
</div>
```

## Mobile-Specific Features

### Touch Gestures

- Swipe to delete/archive items
- Pull to refresh on lists
- Pinch to zoom on images
- Long press for context menus

### Device Features

- Camera access for barcode scanning
- Haptic feedback for actions
- Push notifications (PWA)
- Add to home screen prompt

### Offline Functionality

- View cached inventory
- Add items to queue
- Browse saved recipes
- Sync when online

## Future Design Considerations

### Dark Mode

- System preference detection
- Manual toggle option
- Adjusted color palette
- Reduced contrast for comfort

### Internationalization

- RTL layout support
- Flexible text containers
- Culturally neutral icons
- Date/time format flexibility

### Tablet Optimization

- Multi-column layouts
- Sidebar navigation
- Keyboard shortcuts
- Hover states

This design specification serves as the foundation for implementing a consistent, user-friendly interface across the Kitchentory application.