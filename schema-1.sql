-- SMC Lens Database Schema
-- Run this in your Supabase SQL editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  plan TEXT DEFAULT 'trial' CHECK (plan IN ('trial', 'pro')),
  role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin', 'super_admin')),
  trial_start TIMESTAMPTZ DEFAULT NOW(),
  trial_end TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),
  is_active BOOLEAN DEFAULT TRUE,
  is_suspended BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- PAYMENTS TABLE (EcoCash manual)
CREATE TABLE IF NOT EXISTS payments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  ecocash_reference TEXT NOT NULL,
  amount DECIMAL(10,2) DEFAULT 10.00,
  currency TEXT DEFAULT 'USD',
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  reviewed_by UUID REFERENCES users(id),
  reviewed_at TIMESTAMPTZ,
  period_start TIMESTAMPTZ,
  period_end TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SUBSCRIPTIONS TABLE
CREATE TABLE IF NOT EXISTS subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  plan TEXT DEFAULT 'pro',
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'cancelled', 'expired')),
  start_date TIMESTAMPTZ DEFAULT NOW(),
  end_date TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),
  payment_id UUID REFERENCES payments(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SIGNALS TABLE
CREATE TABLE IF NOT EXISTS signals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  pair TEXT NOT NULL,
  entry_timeframe TEXT NOT NULL,
  bias TEXT NOT NULL,
  entry_price DECIMAL(10,5),
  stop_loss DECIMAL(10,5),
  take_profit_1 DECIMAL(10,5),
  take_profit_2 DECIMAL(10,5),
  rr_ratio DECIMAL(5,2),
  confluence_score INTEGER,
  confluence_details JSONB,
  structure_data JSONB,
  ob_data JSONB,
  fvg_data JSONB,
  candlestick_pattern TEXT,
  volume_status TEXT,
  ai_narrative TEXT,
  htf_bias_summary TEXT,
  signal_valid BOOLEAN DEFAULT TRUE,
  conflict_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ANNOUNCEMENTS TABLE
CREATE TABLE IF NOT EXISTS announcements (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- FEATURE FLAGS TABLE
CREATE TABLE IF NOT EXISTS feature_flags (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  feature_name TEXT UNIQUE NOT NULL,
  is_enabled BOOLEAN DEFAULT TRUE,
  applies_to TEXT DEFAULT 'all' CHECK (applies_to IN ('all', 'pro', 'trial')),
  description TEXT,
  updated_by UUID REFERENCES users(id),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- SUPPORT TICKETS TABLE
CREATE TABLE IF NOT EXISTS support_tickets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  subject TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'resolved', 'closed')),
  admin_reply TEXT,
  resolved_by UUID REFERENCES users(id),
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- API USAGE TABLE
CREATE TABLE IF NOT EXISTS api_usage (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  service TEXT NOT NULL CHECK (service IN ('twelvedata', 'groq')),
  calls_made INTEGER DEFAULT 0,
  date DATE DEFAULT CURRENT_DATE,
  UNIQUE(service, date)
);

-- Insert default feature flags
INSERT INTO feature_flags (feature_name, is_enabled, applies_to, description) VALUES
  ('top_down_analysis', TRUE, 'pro', 'Multi-timeframe top-down analysis cascade'),
  ('signal_history_unlimited', TRUE, 'pro', 'Unlimited signal history'),
  ('ai_full_narrative', TRUE, 'pro', 'Full 5-sentence AI narrative'),
  ('screenshot_pro_watermark', TRUE, 'pro', 'Pro Analysis watermark on screenshots')
ON CONFLICT (feature_name) DO NOTHING;

-- Set super admin
-- This runs after you create your account via the app
-- UPDATE users SET role = 'super_admin', plan = 'pro' WHERE email = 'haroldmanduna388@gmail.com';

-- Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Users can only read their own data
CREATE POLICY "Users read own data" ON users FOR SELECT USING (auth.uid()::text = id::text);
CREATE POLICY "Users read own signals" ON signals FOR SELECT USING (auth.uid()::text = user_id::text);
CREATE POLICY "Users read own payments" ON payments FOR SELECT USING (auth.uid()::text = user_id::text);

-- Announcements are public read
CREATE POLICY "Anyone can read announcements" ON announcements FOR SELECT USING (is_active = TRUE);
