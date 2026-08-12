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

-- ── Core loop tables (Supabase-only backend) ──

create table if not exists stress_history (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    score real not null,
    level text not null,
    deviation_level text not null,
    stress_probability real not null,
    typing_speed_wpm real,
    error_rate real,
    click_count int,
    created_at timestamptz default now()
);

create table if not exists ema_checkins (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    stress real not null check (stress between 0 and 10),
    fatigue real check (fatigue between 0 and 10),
    ts_epoch real not null,
    created_at timestamptz default now()
);

create table if not exists telemetry_events (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    client text not null default 'desktop',
    event_type text not null,
    ts_epoch real not null,
    key_hash text,
    x real, y real,
    kind text,
    down_ms real, up_ms real,
    received_at timestamptz default now()
);

create table if not exists user_baselines (
    user_id uuid primary key references auth.users(id) on delete cascade,
    mean jsonb not null default '[]',
    std jsonb not null default '[]',
    threshold real not null default 40,
    updated_at timestamptz default now()
);

create table if not exists interventions (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    action text not null,
    intervention_type text,
    notes text,
    created_at timestamptz default now()
);

-- RLS: users own their rows
alter table stress_history enable row level security;
alter table ema_checkins enable row level security;
alter table telemetry_events enable row level security;
alter table user_baselines enable row level security;
alter table interventions enable row level security;
alter table chat_sessions enable row level security;
alter table chat_messages enable row level security;
alter table wellness_checkins enable row level security;
alter table wellness_insights enable row level security;
alter table focus_snapshots enable row level security;
alter table user_shield_settings enable row level security;

create policy "own stress_history" on stress_history for all using (auth.uid() = user_id);
create policy "own ema" on ema_checkins for all using (auth.uid() = user_id);
create policy "own telemetry" on telemetry_events for all using (auth.uid() = user_id);
create policy "own baselines" on user_baselines for all using (auth.uid() = user_id);
create policy "own interventions" on interventions for all using (auth.uid() = user_id);
create policy "own chat sessions" on chat_sessions for all using (auth.uid() = user_id::text);
create policy "own chat messages" on chat_messages for all using (true);
create policy "own wellness" on wellness_checkins for all using (auth.uid() = user_id::text);
create policy "own insights" on wellness_insights for all using (auth.uid() = user_id::text);
create policy "own focus" on focus_snapshots for all using (auth.uid() = user_id::text);
create policy "own shield" on user_shield_settings for all using (auth.uid() = user_id::text);
