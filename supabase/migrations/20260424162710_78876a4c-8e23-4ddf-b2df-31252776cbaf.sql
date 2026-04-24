-- Enable case-insensitive text for handles
create extension if not exists citext;

-- Profiles table (one row per auth.users entry)
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  handle citext unique,
  avatar_url text,
  bio text,
  affiliation text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- Public catalog: anyone can read author profiles
create policy "profiles are publicly readable"
  on public.profiles for select
  using (true);

-- Owner-only writes
create policy "users insert own profile"
  on public.profiles for insert
  to authenticated
  with check (id = auth.uid());

create policy "users update own profile"
  on public.profiles for update
  to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

-- updated_at trigger reuses the existing helper
create trigger profiles_touch_updated_at
  before update on public.profiles
  for each row execute function public.touch_updated_at();

-- Auto-provision a profile on signup. Separate trigger from handle_new_user
-- so the role-grant flow stays untouched.
create or replace function public.handle_new_user_profile()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  base_handle text;
  candidate text;
  attempt int := 0;
begin
  -- Default display name = email local-part
  base_handle := lower(regexp_replace(split_part(coalesce(new.email, ''), '@', 1), '[^a-z0-9_]+', '_', 'g'));
  if base_handle is null or length(base_handle) = 0 then
    base_handle := 'user_' || substr(replace(new.id::text, '-', ''), 1, 8);
  end if;

  candidate := base_handle;
  -- Resolve handle collisions deterministically
  while exists (select 1 from public.profiles where handle = candidate) and attempt < 50 loop
    attempt := attempt + 1;
    candidate := base_handle || '_' || attempt;
  end loop;

  insert into public.profiles (id, display_name, handle)
  values (
    new.id,
    coalesce(nullif(split_part(coalesce(new.email, ''), '@', 1), ''), 'Researcher'),
    candidate
  )
  on conflict (id) do nothing;

  return new;
end;
$$;

create trigger on_auth_user_created_profile
  after insert on auth.users
  for each row execute function public.handle_new_user_profile();

create index profiles_handle_idx on public.profiles (handle);