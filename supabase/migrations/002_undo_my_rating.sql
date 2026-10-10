-- Easy undo: a team can take back its own latest rating on a standard without the committee passcode.
-- Only the most recent change to that standard and grade, only from the same device, and only within 15 minutes;
-- anything older still needs admin_undo. The undo is logged by marking the event undone.
create or replace function undo_my_rating(p_framework text, p_code text, p_grade text, p_device text)
returns smallint language plpgsql security definer set search_path = public, extensions as $$
declare e rating_events%rowtype;
begin
  if coalesce(p_device, '') = '' then raise exception 'cannot undo from this device'; end if;
  select * into e from rating_events where framework = p_framework and code = p_code and grade = p_grade
  order by created_at desc, id desc limit 1;
  if not found or e.undone or e.device_id <> p_device or e.created_at < now() - interval '15 minutes' then
    raise exception 'This change can no longer be undone here. Ask the committee to undo it from Activity.';
  end if;
  if e.old_level is null then
    delete from ratings where framework = e.framework and code = e.code and grade = e.grade;
  else
    update ratings set level = e.old_level, team = e.team, updated_at = now()
    where framework = e.framework and code = e.code and grade = e.grade;
  end if;
  update rating_events set undone = true where id = e.id;
  return e.old_level;
end $$;

revoke all on function undo_my_rating from public;
grant execute on function undo_my_rating to anon, authenticated;
