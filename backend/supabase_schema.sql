-- Run this in your Supabase SQL editor
-- Go to: supabase.com → Your Project → SQL Editor → New Query

CREATE TABLE traffic_analysis (
  id              BIGSERIAL PRIMARY KEY,
  created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  filename        TEXT,
  video_url       TEXT,
  video_public_id TEXT,
  processed_video_url TEXT,
  total_vehicles  INTEGER,
  lane_counts     JSONB,
  signal_decisions JSONB,
  frame_data      JSONB
);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE traffic_analysis ENABLE ROW LEVEL SECURITY;

-- Allow all operations for anon key (for demo purposes)
CREATE POLICY "Allow all" ON traffic_analysis
  FOR ALL USING (true) WITH CHECK (true);
