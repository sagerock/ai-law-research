-- Supabase Social Features Schema
-- Run this in your Supabase project (not Hetzner)

-- User profiles (extends Supabase auth.users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    reputation INTEGER DEFAULT 0,
    law_school TEXT,
    graduation_year INTEGER,
    practice_areas TEXT[],  -- e.g., ['torts', 'contracts', 'criminal']
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments on cases
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id TEXT NOT NULL,  -- References case on Hetzner DB
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES comments(id) ON DELETE CASCADE,  -- For replies
    content TEXT NOT NULL,
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Votes on comments
CREATE TABLE comment_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    vote_type INTEGER NOT NULL CHECK (vote_type IN (-1, 1)),  -- -1 = downvote, 1 = upvote
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(comment_id, user_id)  -- One vote per user per comment
);

-- Case bookmarks/saves
CREATE TABLE bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    case_id TEXT NOT NULL,  -- References case on Hetzner DB
    folder TEXT DEFAULT 'default',  -- Allow organizing into folders
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, case_id)
);

-- Study collections (like playlists for cases)
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    subject TEXT,  -- e.g., 'torts', 'contracts'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE collection_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    case_id TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(collection_id, case_id)
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX idx_comments_case_id ON comments(case_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_comments_parent_id ON comments(parent_id);
CREATE INDEX idx_comment_votes_comment_id ON comment_votes(comment_id);
CREATE INDEX idx_bookmarks_user_id ON bookmarks(user_id);
CREATE INDEX idx_bookmarks_case_id ON bookmarks(case_id);
CREATE INDEX idx_collections_user_id ON collections(user_id);
CREATE INDEX idx_collections_public ON collections(is_public) WHERE is_public = TRUE;

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE comment_votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_cases ENABLE ROW LEVEL SECURITY;

-- Profiles: Anyone can read, users can insert/update their own
CREATE POLICY "Profiles are viewable by everyone"
    ON profiles FOR SELECT USING (true);

CREATE POLICY "Users can insert own profile"
    ON profiles FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE USING (auth.uid() = id);

-- Comments: Anyone can read, authenticated users can create, owners can edit/delete
CREATE POLICY "Comments are viewable by everyone"
    ON comments FOR SELECT USING (true);

CREATE POLICY "Authenticated users can create comments"
    ON comments FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own comments"
    ON comments FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own comments"
    ON comments FOR DELETE USING (auth.uid() = user_id);

-- Votes: Authenticated users can vote, one per comment
CREATE POLICY "Votes are viewable by everyone"
    ON comment_votes FOR SELECT USING (true);

CREATE POLICY "Authenticated users can vote"
    ON comment_votes FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can change own vote"
    ON comment_votes FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can remove own vote"
    ON comment_votes FOR DELETE USING (auth.uid() = user_id);

-- Bookmarks: Private to each user
CREATE POLICY "Users can view own bookmarks"
    ON bookmarks FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create bookmarks"
    ON bookmarks FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own bookmarks"
    ON bookmarks FOR DELETE USING (auth.uid() = user_id);

-- Collections: Public ones visible to all, private only to owner
CREATE POLICY "Public collections are viewable by everyone"
    ON collections FOR SELECT USING (is_public = TRUE OR auth.uid() = user_id);

CREATE POLICY "Users can create collections"
    ON collections FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own collections"
    ON collections FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own collections"
    ON collections FOR DELETE USING (auth.uid() = user_id);

-- Collection cases: Same as parent collection
CREATE POLICY "Collection cases follow collection visibility"
    ON collection_cases FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM collections
            WHERE id = collection_cases.collection_id
            AND (is_public = TRUE OR user_id = auth.uid())
        )
    );

CREATE POLICY "Users can add to own collections"
    ON collection_cases FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM collections
            WHERE id = collection_cases.collection_id
            AND user_id = auth.uid()
        )
    );

CREATE POLICY "Users can remove from own collections"
    ON collection_cases FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM collections
            WHERE id = collection_cases.collection_id
            AND user_id = auth.uid()
        )
    );

-- ============================================
-- FUNCTIONS
-- ============================================

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, username, display_name)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'username',
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- Update reputation when votes change
CREATE OR REPLACE FUNCTION update_reputation()
RETURNS TRIGGER AS $$
DECLARE
    comment_author_id UUID;
    vote_delta INTEGER;
BEGIN
    -- Get the comment author
    SELECT user_id INTO comment_author_id
    FROM comments
    WHERE id = COALESCE(NEW.comment_id, OLD.comment_id);

    -- Calculate vote change
    IF TG_OP = 'INSERT' THEN
        vote_delta := NEW.vote_type;
    ELSIF TG_OP = 'DELETE' THEN
        vote_delta := -OLD.vote_type;
    ELSIF TG_OP = 'UPDATE' THEN
        vote_delta := NEW.vote_type - OLD.vote_type;
    END IF;

    -- Update reputation
    UPDATE profiles
    SET reputation = reputation + vote_delta
    WHERE id = comment_author_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_vote_change
    AFTER INSERT OR UPDATE OR DELETE ON comment_votes
    FOR EACH ROW EXECUTE FUNCTION update_reputation();

-- Get comment with vote count
CREATE OR REPLACE FUNCTION get_comments_for_case(p_case_id TEXT)
RETURNS TABLE (
    id UUID,
    case_id TEXT,
    user_id UUID,
    username TEXT,
    display_name TEXT,
    avatar_url TEXT,
    user_reputation INTEGER,
    parent_id UUID,
    content TEXT,
    is_edited BOOLEAN,
    created_at TIMESTAMPTZ,
    vote_count BIGINT,
    user_vote INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.case_id,
        c.user_id,
        p.username,
        p.display_name,
        p.avatar_url,
        p.reputation as user_reputation,
        c.parent_id,
        c.content,
        c.is_edited,
        c.created_at,
        COALESCE(SUM(cv.vote_type), 0) as vote_count,
        (SELECT vote_type FROM comment_votes WHERE comment_id = c.id AND user_id = auth.uid()) as user_vote
    FROM comments c
    JOIN profiles p ON c.user_id = p.id
    LEFT JOIN comment_votes cv ON c.id = cv.comment_id
    WHERE c.case_id = p_case_id
    GROUP BY c.id, p.username, p.display_name, p.avatar_url, p.reputation
    ORDER BY vote_count DESC, c.created_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- REALTIME
-- ============================================

-- Enable realtime for comments (live updates)
ALTER PUBLICATION supabase_realtime ADD TABLE comments;
ALTER PUBLICATION supabase_realtime ADD TABLE comment_votes;
