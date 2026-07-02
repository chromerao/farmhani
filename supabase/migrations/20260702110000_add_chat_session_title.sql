-- Add a human-readable title for chat sessions so each plant/topic is distinguishable.

ALTER TABLE public.chat_sessions
  ADD COLUMN IF NOT EXISTS title TEXT;
