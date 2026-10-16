create type public.app_role as enum ('admin','farmer');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default '',
  phone text not null default '',
  email text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
grant select, insert, update on public.profiles to authenticated;
grant all on public.profiles to service_role;
alter table public.profiles enable row level security;

create table public.user_roles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  role public.app_role not null,
  unique (user_id, role)
);
grant select on public.user_roles to authenticated;
grant all on public.user_roles to service_role;
alter table public.user_roles enable row level security;

create or replace function public.has_role(_user_id uuid, _role public.app_role)
returns boolean language sql stable security definer set search_path = public
as $$ select exists (select 1 from public.user_roles where user_id = _user_id and role = _role) $$;

create policy "own roles readable" on public.user_roles for select to authenticated using (user_id = auth.uid() or public.has_role(auth.uid(),'admin'));

create policy "own profile read" on public.profiles for select to authenticated using (id = auth.uid() or public.has_role(auth.uid(),'admin'));
create policy "own profile insert" on public.profiles for insert to authenticated with check (id = auth.uid());
create policy "own profile update" on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- email is read-only for users
create or replace function public.profiles_guard()
returns trigger language plpgsql set search_path = public as $$
begin
  if length(trim(new.full_name)) < 2 or length(new.full_name) > 100 then raise exception 'Full name must be 2-100 characters'; end if;
  if new.phone <> '' and new.phone !~ '^[0-9+ -]{9,15}$' then raise exception 'Invalid phone number'; end if;
  if tg_op = 'UPDATE' then new.email := old.email; new.created_at := old.created_at; end if;
  new.updated_at := now();
  return new;
end $$;
create trigger profiles_guard before insert or update on public.profiles for each row execute function public.profiles_guard();

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, full_name, phone, email)
  values (new.id,
    coalesce(nullif(new.raw_user_meta_data->>'full_name',''), nullif(new.raw_user_meta_data->>'name',''), split_part(new.email,'@',1) || '  '),
    coalesce(new.raw_user_meta_data->>'phone',''),
    coalesce(new.email,''))
  on conflict (id) do nothing;
  insert into public.user_roles (user_id, role) values (new.id, 'farmer') on conflict do nothing;
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users for each row execute function public.handle_new_user();

create table public.scans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  image_path text not null,
  file_name text not null default '',
  file_size integer not null default 0,
  mime_type text not null default '',
  status text not null default 'not_ready',
  created_at timestamptz not null default now()
);
grant select, insert, delete on public.scans to authenticated;
grant all on public.scans to service_role;
alter table public.scans enable row level security;
create policy "own scans read" on public.scans for select to authenticated using (user_id = auth.uid() or public.has_role(auth.uid(),'admin'));
create policy "own scans insert" on public.scans for insert to authenticated with check (user_id = auth.uid() and status = 'not_ready');
create policy "own scans delete" on public.scans for delete to authenticated using (user_id = auth.uid());

create policy "scan images insert own" on storage.objects for insert to authenticated with check (bucket_id = 'scan-images' and (storage.foldername(name))[1] = auth.uid()::text);
create policy "scan images read own" on storage.objects for select to authenticated using (bucket_id = 'scan-images' and ((storage.foldername(name))[1] = auth.uid()::text or public.has_role(auth.uid(),'admin')));
create policy "scan images delete own" on storage.objects for delete to authenticated using (bucket_id = 'scan-images' and (storage.foldername(name))[1] = auth.uid()::text);