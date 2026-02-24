-- summary_ratings: thumbs up/down on AI briefs
CREATE TABLE IF NOT EXISTS summary_ratings (
    id SERIAL PRIMARY KEY,
    case_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating IN (-1, 1)),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(case_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_summary_ratings_case_id ON summary_ratings(case_id);

-- comment_votes: upvote/downvote on comments
CREATE TABLE IF NOT EXISTS comment_votes (
    id SERIAL PRIMARY KEY,
    comment_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    vote_type INTEGER NOT NULL CHECK (vote_type IN (-1, 1)),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(comment_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_comment_votes_comment_id ON comment_votes(comment_id);
