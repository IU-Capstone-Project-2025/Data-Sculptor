-- Schema for chat service
create extension if not exists "uuid-ossp";

create table if not exists conversations (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid,
    created_at timestamptz default now()
);

create table if not exists messages (
    id uuid primary key default uuid_generate_v4(),
    conversation_id uuid references conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    token_count integer not null,
    created_at timestamptz default now()
);

-- Schema for profile uploader service

create table if not exists cases (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    bucket_url text not null,
    created_at timestamptz default now()
);

create table if not exists profile_descriptions (
    case_id uuid primary key references cases(id) on delete cascade,
    description text not null,
    created_at timestamptz default now()
);

create table if not exists profile_sections (
    case_id uuid not null references cases(id) on delete cascade,
    section_id integer not null,
    description text not null,
    code text not null,
    created_at timestamptz default now(),
    primary key (case_id, section_id)
); 