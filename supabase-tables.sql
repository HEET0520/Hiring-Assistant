-- Enable Row Level Security (RLS)
alter table candidates enable row level security;
alter table tech_stack enable row level security;
alter table technical_assessments enable row level security;
alter table conversation_history enable row level security;

-- Create tables
create table candidates (
    id bigint primary key generated always as identity,
    name varchar(100) not null,
    email varchar(100) unique not null,
    phone varchar(20) not null,
    experience decimal(4,1) not null,
    position varchar(100) not null,
    location varchar(100) not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table tech_stack (
    id bigint primary key generated always as identity,
    candidate_id bigint references candidates(id),
    technology varchar(50) not null,
    unique(candidate_id, technology)
);

create table technical_assessments (
    id bigint primary key generated always as identity,
    candidate_id bigint references candidates(id),
    question text not null,
    answer text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create table conversation_history (
    id bigint primary key generated always as identity,
    candidate_id bigint references candidates(id),
    role varchar(20) not null,
    message text not null,
    timestamp timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create policies
create policy "Enable read access for all users" on candidates for select using (true);
create policy "Enable insert access for all users" on candidates for insert with check (true);

create policy "Enable read access for all users" on tech_stack for select using (true);
create policy "Enable insert access for all users" on tech_stack for insert with check (true);

create policy "Enable read access for all users" on technical_assessments for select using (true);
create policy "Enable insert access for all users" on technical_assessments for insert with check (true);

create policy "Enable read access for all users" on conversation_history for select using (true);
create policy "Enable insert access for all users" on conversation_history for insert with check (true);
