-- Tim asked to drop the committee passcode: anyone can undo a logged change or hide a comment.
-- Nothing is deleted: the change stays in rating_events (marked undone) and hidden comments stay in the table.
-- Only the newest change to a standard and grade can be undone, so an undo never overwrites a later rating.
create or replace function undo_change(p_event_id bigint)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare e rating_events%rowtype; v_latest bigint;
begin
  select * into e from rating_events where id = p_event_id and undone = false;
  if not found then raise exception 'This change was already undone.'; end if;
  select id into v_latest from rating_events where framework = e.framework and code = e.code and grade = e.grade
  order by created_at desc, id desc limit 1;
  if v_latest <> e.id then raise exception 'A newer change to this standard exists. Undo that one first.'; end if;
  if e.old_level is null then
    delete from ratings where framework = e.framework and code = e.code and grade = e.grade;
  else
    update ratings set level = e.old_level, team = e.team, updated_at = now()
    where framework = e.framework and code = e.code and grade = e.grade;
  end if;
  update rating_events set undone = true where id = e.id;
end $$;

create or replace function hide_comment(p_comment_id bigint)
returns void language plpgsql security definer set search_path = public, extensions as $$
begin
  update comments set hidden = true where id = p_comment_id;
end $$;

revoke all on function undo_change, hide_comment from public;
grant execute on function undo_change, hide_comment to anon, authenticated;
