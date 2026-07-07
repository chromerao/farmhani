-- New plants should start without an inferred health score.
-- Health can be set after observation, care logs, or diagnosis results.
ALTER TABLE public.plants
    ALTER COLUMN health_score DROP DEFAULT;
