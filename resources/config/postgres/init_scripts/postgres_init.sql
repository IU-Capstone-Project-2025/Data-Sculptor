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