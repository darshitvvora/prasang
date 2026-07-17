# Agents.md - Prasang (प्रसंग): Artist Discovery Platform

**Project Name:** Prasang (प्रसंग)  
**Pronunciation:** pruh-SUNG  
**Meaning:** Occasion, opportunity, context, gathering (Sanskrit/Hindi/Gujarati/Marathi)  
**Domain:** prasang.in  
**Tagline:** *"Find artists for every prasang"*

---

## Project Overview

**Prasang** is an AI-powered peer to peer artist discovery platform (like "GigSalad + Google + 99acres for entertainers") connecting performers with event planners in India. Operating on a **pure subscription model**, artists pay ₹299-1,199/month for profile visibility and lead generation, while buyers discover and contact talent completely FREE. Artist will have their individual page to market it on instagram. They can create this pge by embedding their Facebook, instagram, youtube, tiktok, spotify, and other social media pages. They can also use this page to sell tickets to their events, which will be powered by ticketing platform like https://tixcraft.com or https://www.insider.in. The platform will also have a feature of **video reviews**, where buyers can embed youtube/dailymotion/instagram/tiktok video reviews of the artists. These reviews will be AI generated and will be used to improve the search results.

**Core Value Proposition:**
- **For Artists:** Professional microsites with auto-portfolio from Instagram/YouTube, AI-powered discovery, qualified lead generation, NO commissions (keep 100% of earnings)
- **For Buyers:** FREE search platform to discover verified talent, view portfolios with videos/photos, see reviews/ratings, get direct contact info (WhatsApp/phone)

**Revenue Model:** Subscription-Only (NO Commissions, NO Booking Fees)
- Artists subscribe monthly/annually for visibility and lead generation
- Buyers use platform 100% FREE (like 99acres, Justdial)
- Platform tracks leads (when buyer clicks "Get Contact Info")
- Artists and buyers transact directly (no platform intermediation)

**Business Model Inspiration:**
- **GigSalad is almost match of business model and process:** Platform for artist booking/gig booking to be implemented for Indian market. 
- **99acres/MagicBricks:** Real estate discovery, subscription-based listings
- **Justdial:** Business directory, lead generation, subscription revenue
- **LinkedIn:** Professional profiles, freemium + paid tiers

---

## Tech Stack

### Frontend
- **Framework:** React 18+ with TypeScript
- **UI Library:** shadcn/ui (Radix UI primitives + Tailwind CSS)
- **Styling:** Tailwind CSS with custom design tokens
- **State Management:** 
  - React Query (TanStack Query) for server state
  - Zustand for client state
- **Routing:** React Router v6
- **Form Handling:** React Hook Form + Zod validation
- **Build Tool:** Vite
- **Mobile:** Mobile-first responsive design, iOS Safari + Android Chrome tested

### Backend
- **Framework:** Python FastAPI (async/await)
- **Orchestration:** Temporal (self-hosted) - durable workflows
- **API Docs:** FastAPI auto-generated OpenAPI/Swagger

### Data Layer
- **Transactional DB:** MySQL 8.0+ (self-hosted) - users, artists, subscriptions, leads
- **Search Engine:** Elasticsearch 8.x (self-hosted) - artist discovery + semantic search
- **Cache:** Redis 7.x (self-hosted) - sessions, rate limiting, frequently accessed data
- **Object Storage:** AWS S3 (free tier) - profile images, videos

### Infrastructure
- **Hosting:** AWS EC2 t3.micro (free tier for 12 months)/lightsail for start
- **Reverse Proxy:** Nginx
- **SSL:** Let's Encrypt (certbot - free)
- **Container Orchestration:** Docker Compose
- **CI/CD:** GitHub Actions
- **Monitoring:** Prometheus + Grafana (optional for MVP)

### Third-Party Services

**Authentication:**
- Google OAuth 2.0 (via Google Identity Services - FREE)
- MSG91 for Mobile OTP (₹0.20/SMS, 99% delivery rate in India)
- JWT tokens for session management

**Payments:**
- Razorpay Subscriptions API (for monthly/annual subscriptions)
- UPI AutoPay support
- Zero transaction fees (subscription gateway is free)

**Communication:**
- AWS SES - Email (free tier: 62,000 emails/month)
- MSG91 - SMS/WhatsApp (₹0.20/SMS)

**Social Media APIs:**
- Instagram Basic Display API (free)
- YouTube Data API v3 (free tier: 10K requests/day)
- Facebook Graph API (free)

**AI/ML:**
- OpenAI text-embedding-ada-002 (₹0.10/1M tokens) - semantic search
- OpenAI GPT-4o-mini (₹0.15/1M input tokens) - AI bio generation
- Qdrant or Chroma (vector database - free tier) - semantic matching

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                     │
│  Landing, Search, Artist Profiles, Dashboards, Admin        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTPS/REST API
                 │
┌────────────────▼────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Temporal Workflows (Core Engine)            │  │
│  │  - Artist Onboarding Workflow                        │  │
│  │  - AI Portfolio Generation Workflow                  │  │
│  │  - Subscription Management Workflow                  │  │
│  │  - Lead Notification Workflow                        │  │
│  │  - Search Indexing Workflow                          │  │
│  │  - Referral Reward Workflow                          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Activities Layer                         │  │
│  │  - Social Media Import (Instagram, YouTube, FB)      │  │
│  │  - AI Bio Generation (OpenAI GPT-4o-mini)           │  │
│  │  - Subscription Payments (Razorpay)                  │  │
│  │  - Lead Notifications (WhatsApp, SMS, Email)         │  │
│  │  - Search Indexing (Elasticsearch)                   │  │
│  │  - Semantic Embeddings (OpenAI ada-002)             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────┬────────────┬──────────────┬──────────────┬───────────┘
      │            │              │              │
┌─────▼────┐ ┌────▼─────┐ ┌──────▼──────┐ ┌────▼─────────┐
│  MySQL   │ │Elastic   │ │   Redis     │ │  Razorpay    │
│ (Users,  │ │search    │ │ (Sessions,  │ │(Subscriptions│
│ Artists, │ │(Search + │ │  Cache,     │ │    Only)     │
│  Subs,   │ │ Semantic)│ │  Limits)    │ │              │
│  Leads)  │ │          │ │             │ │              │
└──────────┘ └──────────┘ └─────────────┘ └──────────────┘
                   │
          ┌────────▼─────────┐
          │  Social Media    │
          │  APIs (Instagram,│
          │  YouTube, FB)    │
          └──────────────────┘
```

---

## Complete Database Schema

```sql
-- ====================
-- USERS & AUTHENTICATION
-- ====================

CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(15) UNIQUE,
    password_hash VARCHAR(255) NULL,  -- NULL for OAuth/OTP users
    user_type ENUM('artist', 'buyer', 'admin') NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    profile_image_url TEXT,
    
    -- Auth provider tracking
    auth_provider ENUM('google', 'mobile', 'email') NOT NULL,
    google_id VARCHAR(255) UNIQUE NULL,
    phone_verified BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_email (email),
    INDEX idx_phone (phone),
    INDEX idx_google_id (google_id),
    INDEX idx_user_type (user_type),
    INDEX idx_auth_provider (auth_provider)
);

CREATE TABLE otp_verifications (
    otp_id VARCHAR(36) PRIMARY KEY,
    phone VARCHAR(15) NOT NULL,
    otp_code VARCHAR(64) NOT NULL,  -- SHA256 hashed
    purpose ENUM('signup', 'login', 'phone_verification') NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    attempts INT DEFAULT 0,  -- Max 3 attempts
    ip_address VARCHAR(45),  -- For security tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_phone_purpose (phone, purpose),
    INDEX idx_expires (expires_at)
);

CREATE TABLE user_sessions (
    session_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    refresh_token VARCHAR(512) NOT NULL,
    device_info JSON,  -- {browser, OS, IP, user_agent}
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_expires (expires_at)
);

-- ====================
-- ARTIST PROFILES
-- ====================

CREATE TABLE artist_profiles (
    artist_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    unique_slug VARCHAR(100) UNIQUE NOT NULL,  -- for prasang.in/profile/{slug}
    artist_type ENUM('magician', 'dj', 'singer', 'comedian', 'bubble_artist', 'band', 'body_double', 'anchor', 'other') NOT NULL,
    bio TEXT,
    
    -- Pricing
    hourly_rate_min DECIMAL(10, 2),
    hourly_rate_max DECIMAL(10, 2),
    per_event_rate_min DECIMAL(10, 2),
    per_event_rate_max DECIMAL(10, 2),
    
    -- Location
    location_city VARCHAR(100),
    location_area VARCHAR(100),  -- Bandra West, Andheri East, etc.
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    service_radius_km INT DEFAULT 20,  -- How far willing to travel
    
    -- Performance metrics
    profile_views INT DEFAULT 0,
    contact_clicks INT DEFAULT 0,
    whatsapp_clicks INT DEFAULT 0,
    phone_clicks INT DEFAULT 0,
    total_leads INT DEFAULT 0,
    
    -- Reviews
    average_rating DECIMAL(3, 2) DEFAULT 0.00,
    total_reviews INT DEFAULT 0,
    
    -- Subscription
    subscription_tier ENUM('free', 'basic', 'pro', 'premium') DEFAULT 'free',
    subscription_start_date DATE NULL,
    subscription_end_date DATE NULL,
    
    -- Search & Visibility
    is_featured BOOLEAN DEFAULT FALSE,
    search_boost_score INT DEFAULT 0,  -- 0, 10, 25, 50 based on tier
    is_verified BOOLEAN DEFAULT FALSE,  -- Manually verified by admin
    
    -- Social media
    instagram_handle VARCHAR(100),
    youtube_channel VARCHAR(255),
    facebook_url VARCHAR(255),
    website_url VARCHAR(255),
    
    -- Portfolio status
    portfolio_auto_generated BOOLEAN DEFAULT FALSE,
    portfolio_complete BOOLEAN DEFAULT FALSE,  -- Min 3 media + bio
    
    availability_status ENUM('available', 'busy', 'unavailable') DEFAULT 'available',
    languages_spoken JSON,  -- ["Hindi", "English", "Marathi"]
    experience_years INT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_slug (unique_slug),
    INDEX idx_artist_type (artist_type),
    INDEX idx_location_city (location_city),
    INDEX idx_location_area (location_city, location_area),
    INDEX idx_subscription_tier (subscription_tier),
    INDEX idx_search_boost (search_boost_score),
    INDEX idx_verified (is_verified),
    INDEX idx_featured (is_featured),
    INDEX idx_rating (average_rating)
);

CREATE TABLE artist_media (
    media_id VARCHAR(36) PRIMARY KEY,
    artist_id VARCHAR(36) NOT NULL,
    media_type ENUM('image', 'video', 'instagram_embed', 'youtube_embed', 'facebook_embed') NOT NULL,
    media_url TEXT NOT NULL,
    thumbnail_url TEXT,
    source ENUM('upload', 'instagram', 'youtube', 'facebook') NOT NULL,
    source_post_id VARCHAR(255),
    caption TEXT,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES artist_profiles(artist_id) ON DELETE CASCADE,
    INDEX idx_artist_media (artist_id, is_featured),
    INDEX idx_display_order (artist_id, display_order)
);

-- ====================
-- SUBSCRIPTIONS
-- ====================

CREATE TABLE subscription_plans (
    plan_id VARCHAR(36) PRIMARY KEY,
    plan_name VARCHAR(50) NOT NULL,
    plan_tier ENUM('free', 'basic', 'pro', 'premium') NOT NULL UNIQUE,
    monthly_price DECIMAL(10, 2) NOT NULL,
    annual_price DECIMAL(10, 2) NOT NULL,  -- 17% discount typically
    
    -- Features per tier
    max_media_uploads INT DEFAULT 10,
    lead_limit_monthly INT DEFAULT -1,  -- -1 = unlimited
    featured_listing BOOLEAN DEFAULT FALSE,
    priority_support BOOLEAN DEFAULT FALSE,
    search_boost_score INT DEFAULT 0,
    verified_badge_eligible BOOLEAN DEFAULT FALSE,
    analytics_access BOOLEAN DEFAULT FALSE,
    map_view_priority BOOLEAN DEFAULT FALSE,
    
    features_json JSON,  -- Detailed feature list for pricing page
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tier (plan_tier)
);

CREATE TABLE subscription_transactions (
    transaction_id VARCHAR(36) PRIMARY KEY,
    artist_id VARCHAR(36) NOT NULL,
    plan_id VARCHAR(36) NOT NULL,
    amount_paid DECIMAL(10, 2) NOT NULL,
    billing_cycle ENUM('monthly', 'annual') NOT NULL,
    payment_method ENUM('razorpay', 'free_trial', 'referral_reward') NOT NULL,
    razorpay_subscription_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100),
    subscription_start_date DATE NOT NULL,
    subscription_end_date DATE NOT NULL,
    transaction_status ENUM('pending', 'success', 'failed', 'refunded') DEFAULT 'pending',
    is_renewal BOOLEAN DEFAULT FALSE,
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES artist_profiles(artist_id),
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(plan_id),
    INDEX idx_artist_subs (artist_id, subscription_end_date),
    INDEX idx_renewal_due (subscription_end_date, auto_renew)
);

-- ====================
-- LEAD TRACKING
-- ====================

CREATE TABLE leads (
    lead_id VARCHAR(36) PRIMARY KEY,
    artist_id VARCHAR(36) NOT NULL,
    buyer_id VARCHAR(36) NULL,  -- NULL if buyer not logged in
    buyer_name VARCHAR(255),
    buyer_phone VARCHAR(15),
    buyer_email VARCHAR(255),
    event_type ENUM('birthday', 'wedding', 'pre_wedding', 'anniversary', 'corporate', 'house_party', 'other'),
    event_date DATE,
    budget_range VARCHAR(50),  -- "₹10K-15K", "₹15K-25K", etc.
    special_requirements TEXT,
    lead_source ENUM('search', 'featured', 'direct_link', 'map_view', 'similar_artists', 'referral', 'homepage') NOT NULL,
    contact_method ENUM('whatsapp_click', 'phone_click', 'email_click', 'view_contact_info') NOT NULL,
    lead_quality_score INT,  -- Artist can rate lead quality (1-5)
    artist_contacted_buyer BOOLEAN DEFAULT FALSE,
    booking_confirmed BOOLEAN DEFAULT FALSE,  -- Artist self-reports
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES artist_profiles(artist_id),
    FOREIGN KEY (buyer_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_artist_leads (artist_id, created_at),
    INDEX idx_buyer_leads (buyer_id),
    INDEX idx_event_date (event_date)
);

-- ====================
-- REVIEWS & RATINGS
-- ====================

CREATE TABLE reviews (
    review_id VARCHAR(36) PRIMARY KEY,
    artist_id VARCHAR(36) NOT NULL,
    reviewer_name VARCHAR(255) NOT NULL,
    reviewer_phone VARCHAR(15),  -- For verification
    reviewer_email VARCHAR(255),
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    event_date DATE,
    event_type ENUM('birthday', 'wedding', 'pre_wedding', 'anniversary', 'corporate', 'house_party', 'other'),
    verified_booking BOOLEAN DEFAULT FALSE,  -- Admin verified this is real
    artist_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES artist_profiles(artist_id) ON DELETE CASCADE,
    INDEX idx_artist_reviews (artist_id, created_at),
    INDEX idx_verified (artist_id, verified_booking),
    INDEX idx_rating (rating)
);

-- ====================
-- REFERRALS
-- ====================

CREATE TABLE referrals (
    referral_id VARCHAR(36) PRIMARY KEY,
    referrer_artist_id VARCHAR(36) NOT NULL,
    referred_artist_id VARCHAR(36) NOT NULL,
    referral_code VARCHAR(20) UNIQUE NOT NULL,  -- PRASANG-ARTIST123
    status ENUM('pending', 'completed', 'rewarded', 'expired') DEFAULT 'pending',
    reward_type ENUM('free_month_pro', 'subscription_discount', 'featured_listing', 'cash') DEFAULT 'free_month_pro',
    reward_description VARCHAR(255),
    completed_at TIMESTAMP NULL,  -- When referred artist upgraded
    rewarded_at TIMESTAMP NULL,
    expires_at TIMESTAMP,  -- 90 days from creation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_artist_id) REFERENCES artist_profiles(artist_id),
    FOREIGN KEY (referred_artist_id) REFERENCES artist_profiles(artist_id),
    INDEX idx_referrer (referrer_artist_id),
    INDEX idx_code (referral_code),
    INDEX idx_status (status)
);

-- ====================
-- DISCOVERY & UX (99acres inspired)
-- ====================

CREATE TABLE user_favorites (
    favorite_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    artist_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (artist_id) REFERENCES artist_profiles(artist_id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_artist (user_id, artist_id),
    INDEX idx_user_favorites (user_id, created_at)
);

CREATE TABLE recently_viewed (
    view_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NULL,  -- NULL for anonymous users
    session_id VARCHAR(100) NOT NULL,  -- Cookie-based session
    artist_id VARCHAR(36) NOT NULL,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    referrer_url TEXT,  -- Where they came from
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (artist_id) REFERENCES artist_profiles(artist_id) ON DELETE CASCADE,
    INDEX idx_session_recent (session_id, viewed_at),
    INDEX idx_user_recent (user_id, viewed_at)
);

CREATE TABLE search_history (
    search_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NULL,
    session_id VARCHAR(100) NOT NULL,
    search_query TEXT NOT NULL,
    filters_applied JSON,  -- {artist_type, location, price_range, etc.}
    results_count INT DEFAULT 0,
    clicked_artist_id VARCHAR(36) NULL,  -- Which result they clicked
    clicked_position INT,  -- Position in results (1-indexed)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (clicked_artist_id) REFERENCES artist_profiles(artist_id) ON DELETE SET NULL,
    INDEX idx_session_search (session_id, created_at),
    INDEX idx_user_search (user_id, created_at)
);

CREATE TABLE localities (
    locality_id VARCHAR(36) PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    area_name VARCHAR(255) NOT NULL,  -- Bandra West, Andheri East, etc.
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    artist_count INT DEFAULT 0,  -- Cached, updated nightly
    popular_artist_types JSON,  -- ["DJ", "Singer", "Magician"]
    avg_price_min DECIMAL(10, 2),
    avg_price_max DECIMAL(10, 2),
    search_volume INT DEFAULT 0,  -- How often this area is searched
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_city_area (city, area_name),
    INDEX idx_city (city),
    INDEX idx_popular (search_volume DESC)
);

-- ====================
-- MONITORING
-- ====================

CREATE TABLE temporal_workflow_executions (
    workflow_id VARCHAR(255) PRIMARY KEY,
    workflow_type VARCHAR(100) NOT NULL,
    run_id VARCHAR(255) NOT NULL,
    entity_id VARCHAR(36),  -- artist_id, user_id, lead_id, etc.
    status ENUM('running', 'completed', 'failed', 'terminated') DEFAULT 'running',
    input_data JSON,
    result_data JSON,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_entity (entity_id),
    INDEX idx_type_status (workflow_type, status),
    INDEX idx_started (started_at)
);
```

### Seed Data: Subscription Plans

```sql
INSERT INTO subscription_plans (plan_id, plan_name, plan_tier, monthly_price, annual_price, max_media_uploads, featured_listing, search_boost_score, verified_badge_eligible, analytics_access, features_json) VALUES

('plan-free', 'Free', 'free', 0.00, 0.00, 5, FALSE, 0, FALSE, FALSE,
 '{"features": ["Basic profile page", "5 media uploads (photos/videos)", "Standard search listing", "WhatsApp/Phone contact buttons", "Manual profile updates", "Basic analytics (views only)"]}'),

('plan-basic', 'Basic', 'basic', 299.00, 2999.00, 15, FALSE, 10, FALSE, FALSE,
 '{"features": ["All Free features", "15 media uploads", "Priority search ranking (+10 boost)", "AI-generated bio from social media", "Weekly performance email", "Email support", "Featured in area listings"]}'),

('plan-pro', 'Pro', 'pro', 599.00, 5999.00, 30, TRUE, 25, TRUE, TRUE,
 '{"features": ["All Basic features", "30 media uploads", "Featured badge (crown icon)", "Top search ranking (+25 boost)", "Verified artist badge (blue checkmark)", "Full analytics dashboard", "Priority support (4-hour response)", "Featured in homepage carousel", "Map view priority", "Similar artists section"]}'),

('plan-premium', 'Premium', 'premium', 1199.00, 11999.00, -1, TRUE, 50, TRUE, TRUE,
 '{"features": ["All Pro features", "Unlimited media uploads", "Guaranteed top 5 search (+50 boost)", "Premium badge (gold border)", "Dedicated account manager", "Same-day support", "Featured in all locality pages", "Custom profile URL", "API access for integrations", "Advanced lead analytics"]}');
```

### Seed Data: Mumbai Localities

```sql
INSERT INTO localities (locality_id, city, area_name, latitude, longitude) VALUES
(UUID(), 'Mumbai', 'Bandra West', 19.0596, 72.8295),
(UUID(), 'Mumbai', 'Bandra East', 19.0544, 72.8447),
(UUID(), 'Mumbai', 'Andheri West', 19.1136, 72.8697),
(UUID(), 'Mumbai', 'Andheri East', 19.1197, 72.8694),
(UUID(), 'Mumbai', 'Juhu', 19.0990, 72.8265),
(UUID(), 'Mumbai', 'Powai', 19.1176, 72.9060),
(UUID(), 'Mumbai', 'Goregaon', 19.1663, 72.8526),
(UUID(), 'Mumbai', 'Malad', 19.1864, 72.8493),
(UUID(), 'Mumbai', 'Borivali', 19.2403, 72.8576),
(UUID(), 'Mumbai', 'Dadar', 19.0178, 72.8478),
(UUID(), 'Mumbai', 'Lower Parel', 18.9985, 72.8302),
(UUID(), 'Mumbai', 'Worli', 19.0176, 72.8158),
(UUID(), 'Mumbai', 'Colaba', 18.9067, 72.8147),
(UUID(), 'Mumbai', 'Fort', 18.9338, 72.8349),
(UUID(), 'Mumbai', 'Navi Mumbai', 19.0330, 73.0297),
(UUID(), 'Mumbai', 'Thane', 19.2183, 72.9781);
```

---

## Elasticsearch Index Schema

```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "hindi_english_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "asciifolding"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "artist_id": { "type": "keyword" },
      "unique_slug": { "type": "keyword" },
      "full_name": {
        "type": "text",
        "fields": { "keyword": { "type": "keyword" } },
        "analyzer": "hindi_english_analyzer"
      },
      "artist_type": { "type": "keyword" },
      "bio": {
        "type": "text",
        "analyzer": "hindi_english_analyzer"
      },
      "location_city": { "type": "keyword" },
      "location_area": { "type": "keyword" },
      "location": {
        "type": "geo_point"  // For map view and nearby search
      },
      "hourly_rate_min": { "type": "float" },
      "hourly_rate_max": { "type": "float" },
      "average_rating": { "type": "float" },
      "total_reviews": { "type": "integer" },
      "profile_views": { "type": "integer" },
      "total_leads": { "type": "integer" },
      "subscription_tier": { "type": "keyword" },
      "search_boost_score": { "type": "integer" },
      "is_featured": { "type": "boolean" },
      "is_verified": { "type": "boolean" },
      "portfolio_complete": { "type": "boolean" },
      "availability_status": { "type": "keyword" },
      "languages_spoken": { "type": "keyword" },
      "experience_years": { "type": "integer" },
      "created_at": { "type": "date" },
      "updated_at": { "type": "date" },
      
      // AI semantic search
      "embedding": {
        "type": "dense_vector",
        "dims": 1536,  // OpenAI text-embedding-ada-002
        "index": true,
        "similarity": "cosine"
      },
      
      // Auto-complete suggestions
      "suggest": {
        "type": "completion",
        "analyzer": "hindi_english_analyzer",
        "contexts": [
          {
            "name": "city",
            "type": "category"
          },
          {
            "name": "artist_type",
            "type": "category"
          }
        ]
      }
    }
  }
}
```

---

## Temporal Workflows (Complete Implementation)

### 1. Artist Onboarding Workflow

```python
from temporalio import workflow
from datetime import timedelta
import asyncio

@workflow.defn
class ArtistOnboardingWorkflow:
    """
    Orchestrates complete artist registration:
    - Create user + artist profile
    - Import Instagram/YouTube content
    - Generate AI bio
    - Create semantic embeddings
    - Index in Elasticsearch
    - Send welcome notifications
    """
    
    @workflow.run
    async def run(self, input: ArtistOnboardingInput) -> ArtistOnboardingResult:
        
        # Step 1: Create user account
        user_id = await workflow.execute_activity(
            create_user_activity,
            CreateUserInput(
                email=input.email,
                phone=input.phone,
                full_name=input.full_name,
                user_type="artist",
                auth_provider=input.auth_provider,  # google or mobile
                google_id=input.google_id  # if Google OAuth
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=workflow.RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1)
            )
        )
        
        # Step 2: Create artist profile
        artist_id = await workflow.execute_activity(
            create_artist_profile_activity,
            CreateArtistInput(
                user_id=user_id,
                artist_type=input.artist_type,
                location_city=input.location_city,
                location_area=input.location_area,
                bio=input.bio,
                hourly_rate_min=input.hourly_rate_min,
                hourly_rate_max=input.hourly_rate_max
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 3: Import social media (parallel execution)
        import_tasks = []
        
        if input.instagram_handle:
            import_tasks.append(
                workflow.execute_activity(
                    import_instagram_media_activity,
                    ImportInstagramInput(
                        artist_id=artist_id,
                        instagram_handle=input.instagram_handle
                    ),
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=2)
                )
            )
        
        if input.youtube_channel:
            import_tasks.append(
                workflow.execute_activity(
                    import_youtube_videos_activity,
                    ImportYouTubeInput(
                        artist_id=artist_id,
                        youtube_channel=input.youtube_channel
                    ),
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=2)
                )
            )
        
        # Wait for all imports (handle failures gracefully)
        media_results = await asyncio.gather(*import_tasks, return_exceptions=True)
        successful_imports = [r for r in media_results if not isinstance(r, Exception)]
        
        # Step 4: Generate AI bio if not provided or media imported successfully
        if (not input.bio and len(successful_imports) > 0):
            generated_bio = await workflow.execute_activity(
                generate_ai_bio_activity,
                GenerateAIBioInput(
                    artist_id=artist_id,
                    artist_type=input.artist_type,
                    media_captions=[r.caption for r in successful_imports if hasattr(r, 'caption')],
                    instagram_bio=input.instagram_bio
                ),
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=workflow.RetryPolicy(maximum_attempts=2)
            )
            
            # Update artist bio
            await workflow.execute_activity(
                update_artist_bio_activity,
                UpdateBioInput(artist_id=artist_id, bio=generated_bio),
                start_to_close_timeout=timedelta(seconds=15)
            )
        
        # Step 5: Generate semantic embeddings for AI search
        await workflow.execute_activity(
            generate_artist_embeddings_activity,
            GenerateEmbeddingsInput(
                artist_id=artist_id,
                text_to_embed=f"{input.full_name} {input.artist_type} {input.bio or generated_bio}"
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3)
        )
        
        # Step 6: Index in Elasticsearch
        await workflow.execute_activity(
            index_artist_in_elasticsearch_activity,
            IndexArtistInput(artist_id=artist_id),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3)
        )
        
        # Step 7: Send welcome email + WhatsApp
        await workflow.execute_activity(
            send_welcome_notification_activity,
            SendWelcomeInput(
                user_id=user_id,
                email=input.email,
                phone=input.phone,
                profile_url=f"https://prasang.in/profile/{artist_id[:8]}"
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        return ArtistOnboardingResult(
            artist_id=artist_id,
            user_id=user_id,
            unique_slug=artist_id[:8],  # Simplified, real implementation better
            profile_url=f"https://prasang.in/profile/{artist_id[:8]}",
            media_imported=len(successful_imports),
            ai_bio_generated=not input.bio
        )
```

### 2. Lead Notification Workflow

```python
@workflow.defn
class LeadNotificationWorkflow:
    """
    Tracks when buyer contacts artist and sends instant notifications.
    This is the CORE monetization workflow - more leads = more artist value.
    """
    
    @workflow.run
    async def run(self, input: LeadInput) -> LeadResult:
        
        # Step 1: Create lead record
        lead_id = await workflow.execute_activity(
            create_lead_activity,
            CreateLeadInput(
                artist_id=input.artist_id,
                buyer_id=input.buyer_id,
                buyer_name=input.buyer_name,
                buyer_phone=input.buyer_phone,
                buyer_email=input.buyer_email,
                event_type=input.event_type,
                event_date=input.event_date,
                budget_range=input.budget_range,
                lead_source=input.lead_source,
                contact_method=input.contact_method
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 2: Get artist details for notification
        artist_details = await workflow.execute_activity(
            get_artist_contact_activity,
            GetArtistInput(artist_id=input.artist_id),
            start_to_close_timeout=timedelta(seconds=15)
        )
        
        # Step 3: Send instant notifications (parallel)
        notification_tasks = []
        
        # WhatsApp notification (highest priority)
        if artist_details.phone:
            notification_tasks.append(
                workflow.execute_activity(
                    send_whatsapp_notification_activity,
                    SendWhatsAppInput(
                        phone=artist_details.phone,
                        message=f"""🎉 New lead from Prasang!

Name: {input.buyer_name}
Phone: {input.buyer_phone}
Event: {input.event_type} on {input.event_date}
Budget: {input.budget_range}

Call them now: {input.buyer_phone}
"""
                    ),
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=2)
                )
            )
        
        # SMS notification (backup)
        notification_tasks.append(
            workflow.execute_activity(
                send_sms_notification_activity,
                SendSMSInput(
                    phone=artist_details.phone,
                    message=f"New lead on Prasang! {input.buyer_name} ({input.buyer_phone}) wants to book you for {input.event_type}. Login to view details."
                ),
                start_to_close_timeout=timedelta(seconds=60)
            )
        )
        
        # Email notification (detailed info)
        notification_tasks.append(
            workflow.execute_activity(
                send_email_notification_activity,
                SendEmailInput(
                    email=artist_details.email,
                    template="new_lead_notification",
                    data={
                        "artist_name": artist_details.full_name,
                        "buyer_name": input.buyer_name,
                        "buyer_phone": input.buyer_phone,
                        "event_type": input.event_type,
                        "event_date": input.event_date,
                        "budget_range": input.budget_range,
                        "lead_url": f"https://prasang.in/artist/leads/{lead_id}"
                    }
                ),
                start_to_close_timeout=timedelta(seconds=60)
            )
        )
        
        # Execute all notifications in parallel
        await asyncio.gather(*notification_tasks, return_exceptions=True)
        
        # Step 4: Update artist metrics
        await workflow.execute_activity(
            increment_artist_lead_counter_activity,
            IncrementLeadInput(artist_id=input.artist_id),
            start_to_close_timeout=timedelta(seconds=15)
        )
        
        # Step 5: Check if artist should be prompted to upgrade
        if artist_details.subscription_tier == 'free' and artist_details.total_leads >= 3:
            # Send upgrade suggestion after 3 leads
            await workflow.execute_activity(
                send_upgrade_prompt_activity,
                UpgradePromptInput(
                    artist_id=input.artist_id,
                    reason="You've received 3 leads! Upgrade to Basic for 10x more visibility."
                ),
                start_to_close_timeout=timedelta(seconds=30)
            )
        
        return LeadResult(
            lead_id=lead_id,
            status="notified",
            notifications_sent=len(notification_tasks)
        )
```

### 3. Subscription Management Workflow

```python
@workflow.defn
class SubscriptionManagementWorkflow:
    """
    Manages subscription lifecycle:
    - Creation via Razorpay
    - Payment confirmation
    - Search boost update
    - Renewal reminders
    - Downgrade on failure
    """
    
    def __init__(self):
        self.payment_confirmed = False
        self.payment_failed = False
    
    @workflow.run
    async def run(self, input: SubscriptionInput) -> SubscriptionResult:
        
        # Step 1: Create Razorpay subscription
        razorpay_sub = await workflow.execute_activity(
            create_razorpay_subscription_activity,
            CreateRazorpaySubInput(
                artist_id=input.artist_id,
                plan_id=input.plan_id,
                billing_cycle=input.billing_cycle  # monthly or annual
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3)
        )
        
        # Step 2: Wait for payment confirmation (Razorpay webhook sends signal)
        payment_confirmed = await workflow.wait_condition(
            lambda: self.payment_confirmed or self.payment_failed,
            timeout=timedelta(hours=24)  # 24-hour payment window
        )
        
        if self.payment_failed or not self.payment_confirmed:
            # Payment failed or timeout
            await workflow.execute_activity(
                cancel_razorpay_subscription_activity,
                CancelSubInput(razorpay_subscription_id=razorpay_sub.subscription_id),
                start_to_close_timeout=timedelta(seconds=30)
            )
            return SubscriptionResult(status="failed", message="Payment not completed")
        
        # Step 3: Update artist subscription tier
        subscription_dates = await workflow.execute_activity(
            update_artist_subscription_activity,
            UpdateSubscriptionInput(
                artist_id=input.artist_id,
                plan_id=input.plan_id,
                billing_cycle=input.billing_cycle,
                razorpay_subscription_id=razorpay_sub.subscription_id
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 4: Update search boost in Elasticsearch
        await workflow.execute_activity(
            update_search_boost_activity,
            UpdateBoostInput(
                artist_id=input.artist_id,
                new_boost_score=input.plan_boost_score,
                is_featured=input.plan_is_featured
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 5: Send confirmation notifications
        await workflow.execute_activity(
            send_subscription_confirmation_activity,
            ConfirmationInput(
                artist_id=input.artist_id,
                plan_name=input.plan_name,
                amount_paid=input.amount_paid,
                billing_cycle=input.billing_cycle,
                subscription_end_date=subscription_dates.end_date
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 6: Schedule renewal reminder (25 days before expiry for monthly, 335 for annual)
        reminder_delay = timedelta(days=335 if input.billing_cycle == "annual" else 25)
        await workflow.sleep(reminder_delay)
        
        await workflow.execute_activity(
            send_renewal_reminder_activity,
            RenewalReminderInput(
                artist_id=input.artist_id,
                days_until_expiry=30 if input.billing_cycle == "annual" else 5
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        return SubscriptionResult(
            status="success",
            subscription_id=razorpay_sub.subscription_id,
            message=f"Subscribed to {input.plan_name} successfully"
        )
    
    @workflow.signal
    async def payment_confirmed_signal(self, payment_data: dict):
        """Signal from Razorpay webhook when payment succeeds"""
        self.payment_confirmed = True
        self.payment_data = payment_data
    
    @workflow.signal
    async def payment_failed_signal(self, error: str):
        """Signal from Razorpay webhook when payment fails"""
        self.payment_failed = True
        self.error = error
```

### 4. Referral Reward Workflow

```python
@workflow.defn
class ReferralRewardWorkflow:
    """
    Tracks referral lifecycle and rewards referrer when referred artist upgrades.
    """
    
    def __init__(self):
        self.referred_artist_upgraded = False
    
    @workflow.run
    async def run(self, input: ReferralInput) -> ReferralResult:
        
        # Step 1: Create referral record
        referral_id = await workflow.execute_activity(
            create_referral_record_activity,
            CreateReferralInput(
                referrer_artist_id=input.referrer_artist_id,
                referred_artist_id=input.referred_artist_id,
                referral_code=input.referral_code
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 2: Wait for referred artist to upgrade (90-day window)
        upgraded = await workflow.wait_condition(
            lambda: self.referred_artist_upgraded,
            timeout=timedelta(days=90)
        )
        
        if not upgraded:
            # Referral expired without conversion
            await workflow.execute_activity(
                mark_referral_expired_activity,
                MarkExpiredInput(referral_id=referral_id),
                start_to_close_timeout=timedelta(seconds=15)
            )
            return ReferralResult(status="expired")
        
        # Step 3: Grant reward to referrer (1 month free Pro subscription)
        await workflow.execute_activity(
            grant_referral_reward_activity,
            GrantRewardInput(
                referrer_artist_id=input.referrer_artist_id,
                referral_id=referral_id,
                reward_type="free_month_pro",
                reward_plan_id="plan-pro"
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Step 4: Notify referrer about reward
        await workflow.execute_activity(
            send_referral_reward_notification_activity,
            NotifyRewardInput(
                artist_id=input.referrer_artist_id,
                reward_description="1 month free Pro subscription (worth ₹599!)"
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        return ReferralResult(
            status="rewarded",
            reward_type="free_month_pro",
            reward_value=599.00
        )
    
    @workflow.signal
    async def referred_artist_upgraded_signal(self, plan_tier: str):
        """Sent when referred artist subscribes to paid plan"""
        if plan_tier in ['basic', 'pro', 'premium']:
            self.referred_artist_upgraded = True
```

### 5. Search Indexing Workflow

```python
@workflow.defn
class SearchIndexingWorkflow:
    """
    Keeps Elasticsearch synchronized with MySQL database.
    Runs as scheduled workflow (nightly) or triggered on profile updates.
    """
    
    @workflow.run
    async def run(self, input: IndexingInput) -> IndexingResult:
        
        if input.artist_ids:
            # Reindex specific artists (triggered by profile update)
            for artist_id in input.artist_ids:
                await workflow.execute_activity(
                    reindex_single_artist_activity,
                    ReindexInput(artist_id=artist_id),
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=workflow.RetryPolicy(
                        maximum_attempts=3,
                        initial_interval=timedelta(seconds=2)
                    )
                )
            
            return IndexingResult(
                status="completed",
                artists_indexed=len(input.artist_ids)
            )
        
        else:
            # Full reindex (nightly scheduled workflow)
            offset = 0
            batch_size = 100
            total_indexed = 0
            
            while True:
                # Fetch batch of artists from MySQL
                artist_batch = await workflow.execute_activity(
                    fetch_artists_batch_activity,
                    FetchBatchInput(offset=offset, limit=batch_size),
                    start_to_close_timeout=timedelta(seconds=30)
                )
                
                if not artist_batch:
                    break  # No more artists
                
                # Bulk reindex batch in Elasticsearch
                indexed_count = await workflow.execute_activity(
                    bulk_reindex_artists_activity,
                    BulkReindexInput(artists=artist_batch),
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=2)
                )
                
                total_indexed += indexed_count
                offset += batch_size
                
                # Rate limiting (don't overwhelm Elasticsearch)
                await asyncio.sleep(2)
            
            return IndexingResult(
                status="completed",
                artists_indexed=total_indexed
            )
```

---

## API Endpoints (Complete)

### Authentication (Google OAuth + Mobile OTP)

```
# Google OAuth Flow
POST   /api/v1/auth/google/init       - Initiate Google OAuth (returns auth URL)
POST   /api/v1/auth/google/callback   - Handle OAuth callback, create/login user
POST   /api/v1/auth/google/link       - Link Google account to existing user

# Mobile OTP Flow  
POST   /api/v1/auth/mobile/send-otp   - Send 6-digit OTP to phone (MSG91)
POST   /api/v1/auth/mobile/verify-otp - Verify OTP and login/register
POST   /api/v1/auth/mobile/resend-otp - Resend OTP (60-second cooldown)

# Session Management
POST   /api/v1/auth/refresh           - Refresh JWT access token
POST   /api/v1/auth/logout            - Logout (invalidate session)
GET    /api/v1/auth/status            - Check auth status

# Profile
GET    /api/v1/users/me               - Get current user profile
PUT    /api/v1/users/me               - Update profile
POST   /api/v1/users/me/verify-phone  - Verify phone (if registered via Google)
```

### Artist Management

```
POST   /api/v1/artists/onboard        - Start artist onboarding workflow (Temporal)
GET    /api/v1/artists/:slug          - Get artist profile by slug (PUBLIC)
PUT    /api/v1/artists/:id            - Update artist profile (AUTH)
DELETE /api/v1/artists/:id            - Deactivate profile (soft delete)

# Media Management
POST   /api/v1/artists/:id/media      - Upload media (S3)
DELETE /api/v1/artists/:id/media/:media_id - Delete media
PUT    /api/v1/artists/:id/media/:media_id/reorder - Reorder media

# Social Media Import
POST   /api/v1/artists/:id/import/instagram - Import Instagram posts
POST   /api/v1/artists/:id/import/youtube   - Import YouTube videos
POST   /api/v1/artists/:id/import/facebook  - Import Facebook posts
GET    /api/v1/artists/:id/import/status    - Check import status

# Analytics (Artist Dashboard)
GET    /api/v1/artists/:id/analytics  - Get performance metrics
  Response: {profile_views, contact_clicks, leads_by_month, conversion_rate}

# Referrals
POST   /api/v1/artists/:id/referral-code - Generate/get referral code
GET    /api/v1/artists/:id/referrals     - Get referral stats

# Availability
PUT    /api/v1/artists/:id/availability - Update availability status
```

### Search & Discovery (PUBLIC - No Auth Required)

```
# Main Search
GET    /api/v1/search/artists
  Query params:
    - q: search query (supports natural language)
    - artist_type: DJ, Magician, Singer, Comedian, etc.
    - location_city: Mumbai, Pune, Delhi, etc.
    - location_area: Bandra West, Andheri, etc. (locality filter)
    - lat, lng, radius: geo-search (km)
    - min_price, max_price: hourly rate range
    - rating_min: minimum rating (1-5)
    - verified_only: true/false
    - featured_only: true/false
    - availability: available, busy, any
    - sort_by: relevance, price_low, price_high, rating, popularity, newest
    - page, limit: pagination

# AI Semantic Search
GET    /api/v1/search/semantic
  Query params:
    - query: "professional DJ for corporate Diwali party in Bandra"
    - k: number of results (default 10)
    - filters: optional JSON with additional filters

# Auto-Suggestions (99acres pattern)
GET    /api/v1/search/suggestions
  Query params:
    - q: partial query ("dj for wedding in ban")
    - limit: number of suggestions (default 5)

# Locality-Based Discovery
GET    /api/v1/locations/cities       - Get all cities with artist count
GET    /api/v1/locations/areas/:city  - Get areas/localities in city
  Response: [{area_name, artist_count, avg_price_min, avg_price_max, popular_types}]

GET    /api/v1/locations/:city/:area/artists - Get artists in specific locality

# Nearby Artists (Geo-search)
GET    /api/v1/artists/nearby
  Query params:
    - lat, lng: coordinates
    - radius: km (default 10km)
    - artist_type: optional filter

# Featured & Trending
GET    /api/v1/artists/featured       - Featured artists (premium subscribers)
GET    /api/v1/artists/trending       - Trending (high engagement last 7 days)
GET    /api/v1/artists/new            - Newly joined (last 30 days)
GET    /api/v1/artists/top-rated      - Highest rated (min 10 reviews)

# Similar Artists (AI-powered)
GET    /api/v1/artists/:id/similar    - Get similar artists
  Uses: AI embeddings + type/price/location matching

# Personalized Recommendations
GET    /api/v1/recommendations
  Query params:
    - user_id: for logged-in users
    - session_id: for anonymous users
  Based on: search history, recently viewed, favorites
```

### Favorites & Recently Viewed (99acres Pattern)

```
POST   /api/v1/favorites/add          - Add to shortlist
  Body: {artist_id}

DELETE /api/v1/favorites/remove/:artist_id - Remove from shortlist
GET    /api/v1/favorites              - Get user's shortlisted artists
POST   /api/v1/favorites/compare      - Compare multiple artists
  Body: {artist_ids: [id1, id2, id3]}

# Recently Viewed (automatic tracking)
GET    /api/v1/recently-viewed        - Get recently viewed profiles
  Tracked automatically via session_id or user_id

POST   /api/v1/tracking/view          - Track profile view
  Body: {artist_id, referrer_url}
```

### Lead Tracking

```
POST   /api/v1/leads/create           - Create lead (starts LeadNotificationWorkflow)
  Body: {
    artist_id,
    buyer_name,
    buyer_phone,
    buyer_email?,
    event_type,
    event_date,
    budget_range,
    contact_method
  }

GET    /api/v1/leads/artist/:artist_id - Get artist's leads (AUTH)
GET    /api/v1/leads/:id/details      - Get lead details (AUTH)
PUT    /api/v1/leads/:id/mark-contacted - Artist marks lead as contacted
PUT    /api/v1/leads/:id/mark-booked  - Artist reports booking confirmed
PUT    /api/v1/leads/:id/rate-quality - Artist rates lead quality (1-5)
```

### Subscriptions

```
GET    /api/v1/subscriptions/plans    - Get all subscription plans (PUBLIC)
POST   /api/v1/subscriptions/subscribe - Subscribe to plan (starts Temporal workflow)
  Body: {artist_id, plan_id, billing_cycle}

POST   /api/v1/subscriptions/webhook  - Razorpay webhook (payment confirmation)
GET    /api/v1/subscriptions/status/:artist_id - Get subscription status
PUT    /api/v1/subscriptions/cancel   - Cancel subscription
PUT    /api/v1/subscriptions/upgrade  - Upgrade plan
PUT    /api/v1/subscriptions/downgrade - Downgrade plan
GET    /api/v1/subscriptions/history  - Transaction history
```

### Reviews

```
POST   /api/v1/reviews/submit         - Submit review (PUBLIC or AUTH)
  Body: {
    artist_id,
    reviewer_name,
    reviewer_phone,
    rating,
    review_text,
    event_date,
    event_type
  }

GET    /api/v1/reviews/artist/:artist_id - Get artist reviews (PUBLIC)
PUT    /api/v1/reviews/:id/respond    - Artist responds (AUTH)
PUT    /api/v1/reviews/:id/verify     - Admin verifies review (ADMIN)
DELETE /api/v1/reviews/:id            - Delete review (ADMIN only)
```

### Referrals

```
GET    /api/v1/referrals/my-code      - Get artist's referral code (AUTH)
POST   /api/v1/referrals/track        - Track referral signup
  Body: {referrer_artist_id, referred_artist_id, referral_code}

GET    /api/v1/referrals/stats        - Get referral statistics (AUTH)
GET    /api/v1/referrals/rewards      - Get referral rewards history
```

### Admin

```
GET    /api/v1/admin/dashboard        - Platform statistics
GET    /api/v1/admin/artists          - List artists (paginated, filterable)
PUT    /api/v1/admin/artists/:id/verify - Verify artist manually
PUT    /api/v1/admin/artists/:id/feature - Feature/unfeature artist
GET    /api/v1/admin/reviews/pending  - Reviews pending moderation
PUT    /api/v1/admin/reviews/:id/verify - Verify review
GET    /api/v1/admin/subscriptions    - Subscription analytics
POST   /api/v1/admin/localities/update - Update locality artist counts
POST   /api/v1/admin/search/reindex   - Trigger full reindex
```

---

## Frontend Pages & Components

### Public Pages (No Auth Required)

```
/                          - Landing page (hero, how it works, featured artists, testimonials)
/search                    - Artist search page (99acres pattern with filters)
/search?city=Mumbai        - City-specific search
/search?city=Mumbai&area=Bandra - Locality-specific
/profile/:slug             - Artist microsite (public)
/localities/:city          - Browse artists by locality (99acres pattern)
/localities/:city/:area    - Artists in specific area
/featured                  - Featured artists showcase
/trending                  - Trending artists
/pricing                   - Subscription pricing plans
/about                     - About Prasang
/contact                   - Contact form
/blog                      - SEO blog
/blog/:slug                - Individual blog post
/terms                     - Terms of service
/privacy                   - Privacy policy
```

### Artist Pages (Auth Required)

```
/artist/dashboard          - Main dashboard (leads, views, earnings potential)
/artist/onboarding         - Onboarding wizard (3-step process)
/artist/profile/edit       - Edit profile
/artist/media              - Manage media (upload, delete, reorder)
/artist/leads              - View all leads
/artist/leads/:id          - Lead details
/artist/analytics          - Performance analytics (charts, metrics)
/artist/subscription       - Subscription management (upgrade, cancel, billing)
/artist/referrals          - Referral program dashboard
/artist/reviews            - View and respond to reviews
/artist/settings           - Account settings
```

### Buyer Pages (Optional - Mostly Public)

```
/buyer/favorites           - Saved/shortlisted artists
/buyer/search-history      - Recent searches
/buyer/recently-viewed     - Recently viewed artists
/buyer/compare             - Comparison tool
```

### Auth Pages

```
/login                     - Login page (Google + Mobile OTP + Email)
/signup                    - Signup page (choose artist or buyer)
/verify-phone              - Phone verification (post-Google OAuth)
/forgot-password           - Password reset (email-based users only)
```

### Admin Pages (ADMIN Role Only)

```
/admin                     - Admin dashboard
/admin/artists             - Artist management
/admin/artists/:id         - Artist details + moderation
/admin/reviews             - Review moderation
/admin/subscriptions       - Subscription analytics
/admin/leads               - Lead analytics
/admin/localities          - Manage localities
/admin/analytics           - Platform-wide analytics
```

---

## Key Features Implementation

### 1. Google OAuth Login (Frontend)

```tsx
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

function App() {
  return (
    <GoogleOAuthProvider clientId="YOUR_GOOGLE_CLIENT_ID">
      <LoginPage />
    </GoogleOAuthProvider>
  );
}

function LoginPage() {
  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const response = await fetch('/api/v1/auth/google/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          credential: credentialResponse.credential 
        })
      });
      
      const data = await response.json();
      
      // Store tokens
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      
      // Check if phone verification needed
      if (data.user.needs_phone) {
        navigate('/verify-phone');
      } else if (data.user.user_type === 'artist') {
        navigate('/artist/dashboard');
      } else {
        navigate('/search');
      }
      
    } catch (error) {
      toast.error('Login failed. Please try again.');
    }
  };
  
  return (
    <div className="flex flex-col items-center gap-6 p-8">
      <h1 className="text-3xl font-bold">Welcome to Prasang</h1>
      <p className="text-muted-foreground">Find artists for every prasang</p>
      
      {/* Google OAuth Button */}
      <GoogleLogin
        onSuccess={handleGoogleSuccess}
        onError={() => toast.error('Google login failed')}
        useOneTap
        theme="filled_blue"
        size="large"
        text="continue_with"
        shape="pill"
      />
      
      {/* Divider */}
      <div className="flex items-center gap-4 w-full">
        <div className="flex-1 border-t" />
        <span className="text-sm text-muted-foreground">OR</span>
        <div className="flex-1 border-t" />
      </div>
      
      {/* Mobile OTP Button */}
      <Button 
        variant="outline" 
        size="lg"
        className="w-full"
        onClick={() => navigate('/login/mobile')}
      >
        📱 Continue with Mobile Number
      </Button>
    </div>
  );
}
```

### 2. Mobile OTP Login (Frontend)

```tsx
function MobileOTPLogin() {
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState<'phone' | 'otp'>('phone');
  const [countdown, setCountdown] = useState(0);
  
  const sendOTP = async () => {
    if (!/^[6-9]\d{9}$/.test(phone)) {
      toast.error('Please enter a valid 10-digit mobile number');
      return;
    }
    
    try {
      await fetch('/api/v1/auth/mobile/send-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          phone, 
          purpose: 'login'  // or 'signup' based on context
        })
      });
      
      setStep('otp');
      setCountdown(60);  // 60-second resend cooldown
      
      // Start countdown timer
      const timer = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      
    } catch (error) {
      toast.error('Failed to send OTP. Please try again.');
    }
  };
  
  const verifyOTP = async () => {
    try {
      const response = await fetch('/api/v1/auth/mobile/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          phone, 
          otp_code: otp,
          user_data: {  // Only for signup
            full_name: 'John Doe',  // From previous form if signup
            user_type: 'buyer'
          }
        })
      });
      
      const data = await response.json();
      
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      
      navigate('/dashboard');
      
    } catch (error) {
      toast.error('Invalid OTP. Please try again.');
    }
  };
  
  return (
    <div className="max-w-md mx-auto p-8">
      <h2 className="text-2xl font-bold mb-6">Login with Mobile</h2>
      
      {step === 'phone' ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Mobile Number
            </label>
            <div className="flex gap-2">
              <div className="flex items-center px-3 border rounded-md bg-muted">
                +91
              </div>
              <Input
                type="tel"
                placeholder="9876543210"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                maxLength={10}
                className="flex-1"
              />
            </div>
          </div>
          
          <Button onClick={sendOTP} className="w-full">
            Send OTP
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Enter the 6-digit OTP sent to +91 {phone}
          </p>
          
          <Input
            type="text"
            placeholder="000000"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
            maxLength={6}
            className="text-center text-2xl tracking-widest"
          />
          
          <Button onClick={verifyOTP} className="w-full">
            Verify & Login
          </Button>
          
          <Button 
            variant="outline" 
            onClick={sendOTP}
            disabled={countdown > 0}
            className="w-full"
          >
            {countdown > 0 ? `Resend OTP in ${countdown}s` : 'Resend OTP'}
          </Button>
          
          <Button 
            variant="ghost" 
            onClick={() => setStep('phone')}
            className="w-full"
          >
            Change Number
          </Button>
        </div>
      )}
    </div>
  );
}
```

### 3. Artist Search Page (99acres Pattern)

```tsx
function ArtistSearchPage() {
  const [filters, setFilters] = useState({
    city: 'Mumbai',
    area: '',
    artist_type: '',
    min_price: 0,
    max_price: 100000,
    rating_min: 0,
    verified_only: false,
    sort_by: 'relevance'
  });
  
  const [viewMode, setViewMode] = useState<'grid' | 'map'>('grid');
  
  const { data: artists, isLoading } = useQuery({
    queryKey: ['artists', filters],
    queryFn: () => fetchArtists(filters)
  });
  
  return (
    <div className="flex">
      {/* Sidebar Filters (Desktop) */}
      <aside className="w-64 border-r p-4 hidden lg:block">
        <h3 className="font-bold mb-4">Filters</h3>
        
        {/* Location Filter */}
        <div className="mb-6">
          <label className="font-medium">Location</label>
          <Select value={filters.city} onValueChange={(v) => setFilters({...filters, city: v})}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Mumbai">Mumbai</SelectItem>
              <SelectItem value="Pune">Pune</SelectItem>
              <SelectItem value="Delhi">Delhi</SelectItem>
            </SelectContent>
          </Select>
          
          {filters.city && (
            <Select value={filters.area} onValueChange={(v) => setFilters({...filters, area: v})}>
              <SelectTrigger className="mt-2">
                <SelectValue placeholder="Select Area" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Areas</SelectItem>
                <SelectItem value="Bandra West">Bandra West</SelectItem>
                <SelectItem value="Andheri">Andheri</SelectItem>
                <SelectItem value="Juhu">Juhu</SelectItem>
              </SelectContent>
            </Select>
          )}
        </div>
        
        {/* Artist Type */}
        <div className="mb-6">
          <label className="font-medium">Artist Type</label>
          <Select value={filters.artist_type} onValueChange={(v) => setFilters({...filters, artist_type: v})}>
            <SelectTrigger>
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Types</SelectItem>
              <SelectItem value="dj">DJ</SelectItem>
              <SelectItem value="singer">Singer</SelectItem>
              <SelectItem value="magician">Magician</SelectItem>
              <SelectItem value="comedian">Stand-up Comedian</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        {/* Price Range Slider */}
        <div className="mb-6">
          <label className="font-medium">Budget Range</label>
          <Slider
            min={0}
            max={100000}
            step={1000}
            value={[filters.min_price, filters.max_price]}
            onValueChange={([min, max]) => setFilters({...filters, min_price: min, max_price: max})}
          />
          <div className="flex justify-between text-sm mt-2">
            <span>₹{filters.min_price.toLocaleString()}</span>
            <span>₹{filters.max_price.toLocaleString()}</span>
          </div>
        </div>
        
        {/* Rating Filter */}
        <div className="mb-6">
          <label className="font-medium">Minimum Rating</label>
          <div className="flex gap-2 mt-2">
            {[4, 3, 2, 1, 0].map((rating) => (
              <Button
                key={rating}
                variant={filters.rating_min === rating ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({...filters, rating_min: rating})}
              >
                {rating > 0 ? `${rating}+ ★` : 'Any'}
              </Button>
            ))}
          </div>
        </div>
        
        {/* Verified Only */}
        <div className="flex items-center gap-2 mb-4">
          <Checkbox 
            checked={filters.verified_only}
            onCheckedChange={(checked) => setFilters({...filters, verified_only: checked})}
          />
          <label>Verified Artists Only</label>
        </div>
      </aside>
      
      {/* Main Content */}
      <main className="flex-1">
        {/* Top Bar */}
        <div className="border-b p-4 flex justify-between items-center">
          <div>
            <p className="text-sm text-muted-foreground">
              {artists?.total || 0} artists found in {filters.city} {filters.area && `• ${filters.area}`}
            </p>
          </div>
          
          <div className="flex gap-4 items-center">
            {/* Sort Dropdown */}
            <Select value={filters.sort_by} onValueChange={(v) => setFilters({...filters, sort_by: v})}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="relevance">Most Relevant</SelectItem>
                <SelectItem value="price_low">Price: Low to High</SelectItem>
                <SelectItem value="price_high">Price: High to Low</SelectItem>
                <SelectItem value="rating">Highest Rated</SelectItem>
                <SelectItem value="popularity">Most Popular</SelectItem>
                <SelectItem value="newest">Newest First</SelectItem>
              </SelectContent>
            </Select>
            
            {/* View Toggle */}
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('grid')}
              >
                Grid
              </Button>
              <Button
                variant={viewMode === 'map' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('map')}
              >
                Map
              </Button>
            </div>
          </div>
        </div>
        
        {/* Search Results */}
        {viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
            {artists?.results.map((artist) => (
              <ArtistCard key={artist.artist_id} artist={artist} />
            ))}
          </div>
        ) : (
          <MapView artists={artists?.results || []} />
        )}
      </main>
    </div>
  );
}
```

### 2. Artist Card Component (99acres Pattern)

```tsx
function ArtistCard({ artist }) {
  const [isFavorited, setIsFavorited] = useState(false);
  
  return (
    <Card className={cn(
      "overflow-hidden hover:shadow-lg transition-shadow",
      artist.is_featured && "border-2 border-yellow-400"
    )}>
      {/* Badges */}
      <div className="absolute top-2 left-2 flex gap-2 z-10">
        {artist.is_featured && (
          <Badge className="bg-yellow-400 text-black">🌟 Featured</Badge>
        )}
        {artist.is_verified && (
          <Badge className="bg-blue-500">✓ Verified</Badge>
        )}
        {artist.subscription_tier === 'pro' && (
          <Badge className="bg-purple-500">👑 Pro</Badge>
        )}
        {artist.subscription_tier === 'premium' && (
          <Badge className="bg-gold-500">⭐ Premium</Badge>
        )}
      </div>
      
      {/* Favorite Button */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2 z-10"
        onClick={() => toggleFavorite(artist.artist_id)}
      >
        <Heart className={isFavorited ? "fill-red-500 text-red-500" : ""} />
      </Button>
      
      {/* Profile Image */}
      <div className="relative h-48 bg-muted">
        <img 
          src={artist.profile_image_url} 
          alt={artist.full_name}
          className="w-full h-full object-cover"
        />
      </div>
      
      {/* Content */}
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <h3 className="font-bold text-lg">{artist.full_name}</h3>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{artist.artist_type}</span>
              <span>•</span>
              <span>{artist.location_area}, {artist.location_city}</span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
            <span className="font-medium">{artist.average_rating}</span>
            <span className="text-sm text-muted-foreground">
              ({artist.total_reviews})
            </span>
          </div>
        </div>
        
        {/* Price */}
        <p className="text-sm font-medium mb-3">
          ₹{artist.hourly_rate_min?.toLocaleString()} - 
          ₹{artist.hourly_rate_max?.toLocaleString()} per event
        </p>
        
        {/* Bio Excerpt */}
        <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
          {artist.bio}
        </p>
        
        {/* CTA Buttons */}
        <div className="flex gap-2">
          <Button 
            variant="default" 
            className="flex-1"
            onClick={() => handleGetContactInfo(artist)}
          >
            📞 Get Contact Info
          </Button>
          <Button 
            variant="outline"
            onClick={() => navigate(`/profile/${artist.unique_slug}`)}
          >
            View Profile
          </Button>
        </div>
        
        {/* Metadata */}
        <p className="text-xs text-muted-foreground mt-3">
          Last active: {formatRelativeTime(artist.updated_at)} • 
          {artist.profile_views} views this month
        </p>
      </CardContent>
    </Card>
  );
}
```

### 3. "Get Contact Info" Modal (Lead Capture)

```tsx
function GetContactInfoModal({ artist, isOpen, onClose }) {
  const [formData, setFormData] = useState({
    buyer_name: '',
    buyer_phone: '',
    buyer_email: '',
    event_type: 'birthday',
    event_date: '',
    budget_range: '₹10K-15K'
  });
  
  const [step, setStep] = useState<'form' | 'revealed'>('form');
  
  const handleSubmit = async () => {
    try {
      // Create lead (starts LeadNotificationWorkflow)
      const response = await fetch('/api/v1/leads/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          artist_id: artist.artist_id,
          ...formData,
          lead_source: 'search',
          contact_method: 'view_contact_info'
        })
      });
      
      const leadData = await response.json();
      setStep('revealed');
      
    } catch (error) {
      toast.error('Failed to get contact info');
    }
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        {step === 'form' ? (
          <>
            <DialogHeader>
              <DialogTitle>Get {artist.full_name}'s Contact Details</DialogTitle>
              <DialogDescription>
                Share your details so the artist can prepare a personalized quote for you.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Your Name *</label>
                <Input
                  value={formData.buyer_name}
                  onChange={(e) => setFormData({...formData, buyer_name: e.target.value})}
                  placeholder="John Doe"
                />
              </div>
              
              <div>
                <label className="text-sm font-medium">Your Phone *</label>
                <div className="flex gap-2">
                  <div className="flex items-center px-3 border rounded-md bg-muted">+91</div>
                  <Input
                    type="tel"
                    value={formData.buyer_phone}
                    onChange={(e) => setFormData({...formData, buyer_phone: e.target.value})}
                    placeholder="9876543210"
                    maxLength={10}
                  />
                </div>
              </div>
              
              <div>
                <label className="text-sm font-medium">Event Date</label>
                <Input
                  type="date"
                  value={formData.event_date}
                  onChange={(e) => setFormData({...formData, event_date: e.target.value})}
                />
              </div>
              
              <div>
                <label className="text-sm font-medium">Event Type</label>
                <Select value={formData.event_type} onValueChange={(v) => setFormData({...formData, event_type: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="birthday">Birthday Party</SelectItem>
                    <SelectItem value="wedding">Wedding</SelectItem>
                    <SelectItem value="pre_wedding">Pre-Wedding</SelectItem>
                    <SelectItem value="anniversary">Anniversary</SelectItem>
                    <SelectItem value="corporate">Corporate Event</SelectItem>
                    <SelectItem value="house_party">House Party</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <label className="text-sm font-medium">Your Budget</label>
                <Select value={formData.budget_range} onValueChange={(v) => setFormData({...formData, budget_range: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="₹5K-10K">₹5,000 - ₹10,000</SelectItem>
                    <SelectItem value="₹10K-15K">₹10,000 - ₹15,000</SelectItem>
                    <SelectItem value="₹15K-25K">₹15,000 - ₹25,000</SelectItem>
                    <SelectItem value="₹25K-50K">₹25,000 - ₹50,000</SelectItem>
                    <SelectItem value="₹50K+">₹50,000+</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={onClose}>Cancel</Button>
              <Button onClick={handleSubmit}>View Contact Info</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>{artist.full_name}'s Contact Details</DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4">
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">Phone Number</p>
                <p className="text-2xl font-bold">+91 {artist.phone}</p>
              </div>
              
              {artist.email && (
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground mb-2">Email</p>
                  <p className="font-medium">{artist.email}</p>
                </div>
              )}
              
              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  onClick={() => window.open(`tel:+91${artist.phone}`)}
                >
                  📞 Call Now
                </Button>
                <Button
                  className="flex-1"
                  variant="outline"
                  onClick={() => window.open(`https://wa.me/91${artist.phone}`)}
                >
                  💬 WhatsApp
                </Button>
              </div>
              
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-sm">
                  ✓ We've notified {artist.full_name} about your interest. 
                  They'll contact you soon!
                </p>
              </div>
            </div>
            
            <DialogFooter>
              <Button onClick={onClose}>Close</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

This is a comprehensive implementation guide with everything you need! The complete Agents.md file now includes full authentication flows, real estate marketplace UX patterns, and all the database tables needed.

Would you like me to also create:
1. **Detailed Temporal workflow code** for all 5 workflows in Python?
2. **React component library** structure with shadcn/ui?
3. **Docker Compose** configuration for local development?
4. **MSG91 API integration** code for OTP sending?

<function_calls>
<invoke name="present_files">
<parameter name="filepaths">["/mnt/user-data/outputs/Agents.md", "/mnt/user-data/outputs/Prasang_Complete_Execution_Plan.md"]