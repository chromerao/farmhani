-- =============================================================================
-- AI answer feedback
-- Stores per-user feedback for assistant messages so answer quality can be
-- reviewed and improved without exposing other users' chat data.
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.chat_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID NOT NULL REFERENCES public.chat_messages(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  rating text NOT NULL CHECK (rating IN ('helpful', 'not_helpful', 'unsafe', 'irrelevant')),
  comment text,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (message_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_feedback_user_created
  ON public.chat_feedback (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_feedback_rating_created
  ON public.chat_feedback (rating, created_at DESC);

ALTER TABLE public.chat_feedback ENABLE ROW LEVEL SECURITY;

-- 재실행 안전(멱등)하도록 기존 정책은 삭제 후 재생성
DROP POLICY IF EXISTS "Users can read own chat feedback" ON public.chat_feedback;
DROP POLICY IF EXISTS "Users can insert feedback for own assistant messages" ON public.chat_feedback;
DROP POLICY IF EXISTS "Users can update own chat feedback" ON public.chat_feedback;

CREATE POLICY "Users can read own chat feedback"
  ON public.chat_feedback
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert feedback for own assistant messages"
  ON public.chat_feedback
  FOR INSERT
  WITH CHECK (
    auth.uid() = user_id
    AND EXISTS (
      SELECT 1
      FROM public.chat_messages m
      JOIN public.chat_sessions s ON s.id = m.session_id
      WHERE m.id = chat_feedback.message_id
        AND s.user_id = auth.uid()
        AND m.role = 'assistant'
    )
  );

CREATE POLICY "Users can update own chat feedback"
  ON public.chat_feedback
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
