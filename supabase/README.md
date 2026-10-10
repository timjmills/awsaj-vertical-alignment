# Database (Supabase)

Project: awsaj-vertical-alignment (ref mmcblwddwgwhtlhrqmfi, region ap-south-1), org mycurricula.app, Free plan.
URL: https://mmcblwddwgwhtlhrqmfi.supabase.co   Public key: sb_publishable_rfubWiFJpgX5ZcSBXrb1AA_bSG0MB-y (safe in the browser).

- No sign-in. Tables are read-only to the public key (RLS). All writes go through functions:
  set_rating (logs every change to rating_events), add_comment, undo_change and hide_comment (migration 003, no passcode: Tim asked to drop it; undo only works on the
  newest change to a standard, and the history keeps everything). admin_undo / admin_hide_comment still exist but the site no longer uses them.
  undo_my_rating (migration 002) lets a device take back its own latest change to a standard within 15 minutes, no passcode.
- Ratings are stored per standard per grade, so any grade can claim a band standard placed elsewhere.
- Free projects pause after 7 days without activity: a scheduled GitHub Action pings the API (to be added with the site).
- Loading data: scripts/load_supabase.py via a temporary token-protected load_rows() function; remove it after loading.
