-- Arbitrage Bot Supabase Database Schema
-- Run these queries in your Supabase SQL Editor to set up the database
-- Project: https://supabase.com/dashboard/projects

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Odds table: stores normalized odds from all data sources
CREATE TABLE IF NOT EXISTS odds (
  odds_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  event_name TEXT,
  sport TEXT NOT NULL,
  league TEXT NOT NULL,
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  selection TEXT NOT NULL,
  market_type TEXT NOT NULL,
  price FLOAT NOT NULL,
  american_odds FLOAT,
  implied_probability FLOAT,
  source TEXT NOT NULL,
  start_time TIMESTAMP WITH TIME ZONE,
  last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(odds_id)
);

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_odds_event_id ON odds(event_id);
CREATE INDEX IF NOT EXISTS idx_odds_source ON odds(source);
CREATE INDEX IF NOT EXISTS idx_odds_start_time ON odds(start_time);

-- Trades table: records all executed trades
CREATE TABLE IF NOT EXISTS trades (
  trade_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id TEXT NOT NULL,
  price FLOAT NOT NULL,
  stake FLOAT NOT NULL,
  status TEXT NOT NULL,
  mode TEXT NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for trade lookups
CREATE INDEX IF NOT EXISTS idx_trades_event_id ON trades(event_id);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp DESC);

-- Positions table: tracks current position size per event
CREATE TABLE IF NOT EXISTS positions (
  event_id TEXT PRIMARY KEY,
  size FLOAT NOT NULL DEFAULT 0.0,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE odds ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;

-- Allow all operations (no auth required for public use)
CREATE POLICY "Enable read access for all users" ON odds FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON odds FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON odds FOR UPDATE USING (true);

CREATE POLICY "Enable read access for all users" ON trades FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON trades FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable read access for all users" ON positions FOR SELECT USING (true);
CREATE POLICY "Enable insert/update for all users" ON positions FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON positions FOR UPDATE USING (true);
