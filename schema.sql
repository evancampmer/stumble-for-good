CREATE TABLE IF NOT EXISTS sites (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    domain TEXT,
    description TEXT,
    thumbnail TEXT,
    fetched_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sites_category ON sites (category);

CREATE TABLE IF NOT EXISTS saved_sites (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    description TEXT,
    domain TEXT,
    category TEXT,
    thumbnail TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (session_id, url)
);
