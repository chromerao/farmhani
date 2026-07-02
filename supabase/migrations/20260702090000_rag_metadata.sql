-- RAG citation metadata support.
-- Applies only to RAG reference tables/functions and does not touch user data.

ALTER TABLE public.rag_chunks
  ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

DROP FUNCTION IF EXISTS public.match_rag_chunks(vector, float, int);

CREATE OR REPLACE FUNCTION public.match_rag_chunks (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id UUID,
  source_id TEXT,
  title TEXT,
  url TEXT,
  publisher TEXT,
  content TEXT,
  metadata JSONB,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    rag_chunks.chunk_id AS id,
    rag_chunks.source_id::text AS source_id,
    COALESCE(rag_chunks.metadata->>'title', rag_sources.title) AS title,
    COALESCE(rag_chunks.metadata->>'url', rag_sources.url) AS url,
    COALESCE(rag_chunks.metadata->>'publisher', rag_sources.publisher) AS publisher,
    rag_chunks.text AS content,
    rag_chunks.metadata,
    1 - (rag_chunks.embedding <=> query_embedding) AS similarity
  FROM public.rag_chunks
  JOIN public.rag_sources ON rag_sources.source_id = rag_chunks.source_id
  WHERE 1 - (rag_chunks.embedding <=> query_embedding) > match_threshold
  ORDER BY rag_chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
