-- MindPulse — Supabase schema for extended features
-- Apply to the NEW Supabase project (SQL Editor):
--   https://supabase.com/dashboard -> new project -> SQL Editor -> paste -> Run
-- Then set in backend/.env:
--   SUPABASE_URL=https://<project-ref>.supabase.co
--   SUPABASE_ANON_KEY=<anon key from Settings -> API>
-- (Service key optional; the app falls back to local SQLite until then)

create table if not exists chat_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    title text default 'New Chat',
    is_active boolean default true,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists chat_messages (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references chat_sessions(id) on delete cascade,
    role text not null,
    content text not null,
    created_at timestamptz default now()
);

create table if not exists wellness_checkins (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    check_date date not null,
    energy_level text not null,
    sleep_quality text not null,
    note text,
    created_at timestamptz default now(),
    unique (user_id, check_date)
);

create table if not exists wellness_insights (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    insight_type text not null,
    content text not null,
    generated_at timestamptz default now()
);

create table if not exists focus_snapshots (
    id uuid primary key default gen_random_uuid(),
    user_id text not null,
    focus_score real,
    context_switches int default 0,
    tab_hopping int default 0,
    created_at timestamptz default now()
);

create table if not exists user_shield_settings (
    id uuid primary key default gen_random_uuid(),
    user_id text not null unique,
    enabled boolean default false,
    updated_at timestamptz default now()
);

create index if not exists idx_chat_sessions_user on chat_sessions(user_id);
create index if not exists idx_chat_messages_session on chat_messages(session_id);
create index if not exists idx_wellness_user_date on wellness_checkins(user_id, check_date);
create index if not exists idx_focus_user_time on focus_snapshots(user_id, created_at);
