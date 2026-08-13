-- MIGRATION: chat message security (run in Supabase SQL Editor)
-- Fixes: chat_messages were readable/writable by ANY authenticated user.

ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE;

DROP POLICY IF EXISTS "own chat messages" ON chat_messages;
CREATE POLICY "own chat messages" ON chat_messages
    FOR ALL USING (auth.uid() = user_id);
