-- Awsaj K-12 Vertical Alignment: Part 1 schema
-- No sign-in: the site uses the public (anon) key. Reads are open; writes go only through
-- the functions below, which log every change. Admin actions need the admin passcode.

create extension if not exists pgcrypto with schema extensions;

-- Standards (one row per standard per placed grade; band standards appear in each grade of the band)
create table if not exists standards (
  id                    bigserial primary key,
  subject               text not null,          -- Math | ELA | Science | Social Studies
  framework             text not null,          -- WI-CC-MATH, WI-CC-ELA, NGSS, WI-SCI, AERO-SCI, WI-SS, AERO-SS
  code                  text not null,
  grade                 text not null,          -- K, 1..12 (suggested placement when grade_is_suggested)
  grade_band            text not null default '',
  grade_is_suggested    boolean not null default false,
  division              text not null,          -- Elementary | Middle | High
  course                text not null default '',
  strand                text not null default '',
  cluster               text not null default '',
  text                  text not null,
  ee_code               text not null default '',
  ee_text               text not null default '',
  crosswalk             text[] not null default '{}',
  descriptors           jsonb not null default '{}',
  descriptor_source     text not null default '',
  descriptor_flag       text not null default '',
  descriptors_suggested jsonb,
  power_standard        boolean,
  source                text not null default '',
  text_source           text not null default '',
  extra                 jsonb not null default '{}',
  unique (framework, code, grade)
);
create index if not exists standards_subject_grade on standards (subject, grade);
create index if not exists standards_framework_code on standards (framework, code);

-- Teams (picked from a dropdown; no accounts)
create table if not exists teams (
  id       serial primary key,
  name     text not null unique,               -- e.g. "Grade 5", "MS Science", "Algebra 1"
  subjects text[] not null default '{}',
  grades   text[] not null default '{}'
);

-- Current rating of a standard IN A GIVEN GRADE (any grade, so teachers can claim band
-- standards placed elsewhere). level: 0 Not taught, 1 Introduced/Exposed, 2 Taught in Depth
create table if not exists ratings (
  framework  text not null,
  code       text not null,
  grade      text not null,
  level      smallint not null check (level between 0 and 2),
  team       text not null,
  updated_at timestamptz not null default now(),
  primary key (framework, code, grade)
);

-- Every change, for history and undo
create table if not exists rating_events (
  id         bigserial primary key,
  framework  text not null,
  code       text not null,
  grade      text not null,
  old_level  smallint,
  new_level  smallint not null,
  team       text not null,
  device_id  text not null default '',
  created_at timestamptz not null default now(),
  undone     boolean not null default false
);
create index if not exists rating_events_key on rating_events (framework, code, grade, created_at desc);

create table if not exists comments (
  id         bigserial primary key,
  framework  text not null,
  code       text not null,
  grade      text,
  team       text not null,
  author     text not null default '',
  body       text not null check (length(body) between 1 and 2000),
  created_at timestamptz not null default now(),
  hidden     boolean not null default false
);
create index if not exists comments_key on comments (framework, code);

create table if not exists app_settings (
  key   text primary key,
  value text not null
);

-- Row level security: anyone can read; nobody writes tables directly
alter table standards     enable row level security;
alter table teams         enable row level security;
alter table ratings       enable row level security;
alter table rating_events enable row level security;
alter table comments      enable row level security;
alter table app_settings  enable row level security;

create policy read_standards on standards     for select using (true);
create policy read_teams     on teams         for select using (true);
create policy read_ratings   on ratings       for select using (true);
create policy read_events    on rating_events for select using (true);
create policy read_comments  on comments      for select using (hidden = false);
-- app_settings: no policies, so it is not readable by the public key

-- Set (or cycle) a rating; logs the change
create or replace function set_rating(p_framework text, p_code text, p_grade text, p_level smallint,
                                      p_team text, p_device text default '')
returns smallint language plpgsql security definer set search_path = public, extensions as $$
declare v_old smallint;
begin
  if p_level not between 0 and 2 then raise exception 'level must be 0, 1 or 2'; end if;
  if not exists (select 1 from teams where name = p_team) then raise exception 'unknown team'; end if;
  if not exists (select 1 from standards where framework = p_framework and code = p_code) then
    raise exception 'unknown standard'; end if;
  select level into v_old from ratings where framework = p_framework and code = p_code and grade = p_grade;
  insert into ratings (framework, code, grade, level, team, updated_at)
  values (p_framework, p_code, p_grade, p_level, p_team, now())
  on conflict (framework, code, grade) do update set level = excluded.level, team = excluded.team, updated_at = now();
  insert into rating_events (framework, code, grade, old_level, new_level, team, device_id)
  values (p_framework, p_code, p_grade, v_old, p_level, p_team, left(coalesce(p_device, ''), 64));
  return p_level;
end $$;

create or replace function add_comment(p_framework text, p_code text, p_grade text, p_team text,
                                       p_author text, p_body text)
returns bigint language plpgsql security definer set search_path = public, extensions as $$
declare v_id bigint;
begin
  if not exists (select 1 from teams where name = p_team) then raise exception 'unknown team'; end if;
  insert into comments (framework, code, grade, team, author, body)
  values (p_framework, p_code, p_grade, p_team, left(coalesce(p_author, ''), 80), p_body)
  returning id into v_id;
  return v_id;
end $$;

-- Admin: undo one logged change (restores the previous level); needs the admin passcode
create or replace function admin_undo(p_event_id bigint, p_passcode text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare e rating_events%rowtype;
begin
  if not exists (select 1 from app_settings where key = 'admin_passcode_hash'
                 and value = crypt(p_passcode, value)) then raise exception 'not allowed'; end if;
  select * into e from rating_events where id = p_event_id and undone = false;
  if not found then raise exception 'no such change'; end if;
  if e.old_level is null then
    delete from ratings where framework = e.framework and code = e.code and grade = e.grade;
  else
    update ratings set level = e.old_level, team = 'admin undo', updated_at = now()
    where framework = e.framework and code = e.code and grade = e.grade;
  end if;
  update rating_events set undone = true where id = p_event_id;
end $$;

create or replace function admin_hide_comment(p_comment_id bigint, p_passcode text)
returns void language plpgsql security definer set search_path = public, extensions as $$
begin
  if not exists (select 1 from app_settings where key = 'admin_passcode_hash'
                 and value = crypt(p_passcode, value)) then raise exception 'not allowed'; end if;
  update comments set hidden = true where id = p_comment_id;
end $$;

revoke all on function set_rating, add_comment, admin_undo, admin_hide_comment from public;
grant execute on function set_rating, add_comment, admin_undo, admin_hide_comment to anon, authenticated;
