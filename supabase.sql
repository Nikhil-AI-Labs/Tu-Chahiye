-- ============================================================================
--  Tu Chahiye — leaderboard tables
--
--  Run this ONCE in the Supabase dashboard:
--      SQL Editor  ->  New query  ->  paste  ->  Run
--
--  Project: trlbvgevoznwnbbihigk
--
--  It is safe to run twice. cpp_quiz_scores and dip_quiz_scores already
--  exist and are left exactly as they are — only the three new tables
--  (dcn, dcomm, dsp) are created.
-- ============================================================================

do $$
declare
  t text;
begin
  foreach t in array array['dcn_quiz_scores','dcomm_quiz_scores','dsp_quiz_scores']
  loop

    ------------------------------------------------------------------ table
    execute format($f$
      create table if not exists public.%I (
        slug          text primary key,
        name          text        not null,
        status        text        not null default 'playing',
        score         int         not null default 0,
        correct       int         not null default 0,
        duration_ms   bigint      not null default 0,
        easy          int         not null default 0,
        medium        int         not null default 0,
        hard          int         not null default 0,
        started_at    timestamptz not null default now(),
        submitted_at  timestamptz
      )$f$, t);

    ------------------------------------------------- index the board ordering
    execute format(
      'create index if not exists %I on public.%I (score desc, duration_ms asc)',
      t || '_board', t);

    ------------------------------------------------------ row level security
    --  The key in the page is the *publishable* key and is meant to be
    --  public. These three policies are what actually protect the data.
    execute format('alter table public.%I enable row level security', t);

    execute format('drop policy if exists tc_read   on public.%I', t);
    execute format('drop policy if exists tc_claim  on public.%I', t);
    execute format('drop policy if exists tc_finish on public.%I', t);

    -- anyone may read the board
    execute format(
      'create policy tc_read on public.%I for select using (true)', t);

    -- anyone may sign the sheet once; the primary key on slug blocks a second go
    execute format(
      'create policy tc_claim on public.%I for insert with check (true)', t);

    -- a row may be written only while the attempt is still running, so a
    -- finished score can never be edited afterwards, by anyone, from the page
    execute format(
      'create policy tc_finish on public.%I for update using (status = ''playing'') with check (true)', t);

  end loop;
end $$;


-- ============================================================================
--  Check it worked — all five should come back
-- ============================================================================
select table_name
from   information_schema.tables
where  table_schema = 'public'
  and  table_name in ('cpp_quiz_scores','dip_quiz_scores',
                      'dcn_quiz_scores','dcomm_quiz_scores','dsp_quiz_scores')
order  by table_name;


-- ============================================================================
--  Handy afterwards
-- ============================================================================
-- see a board:
--   select name, score, correct, duration_ms
--   from   public.dcn_quiz_scores
--   where  status = 'done'
--   order  by score desc, duration_ms asc;
--
-- let one person sit a quiz again (use the slug, which is their name
-- lower-cased with spaces turned into hyphens):
--   delete from public.dcn_quiz_scores where slug = 'nikhil';
--
-- clear attempts that were started but never finished:
--   delete from public.dcn_quiz_scores where status = 'playing';
--
-- wipe a board completely before sharing it around:
--   truncate public.dcn_quiz_scores;


-- ============================================================================
--  ONE-TIME CLEANUP — please run this
--
--  While checking that the three new boards actually accept a score, a probe
--  row was written to each of them (slug 'zz-selftest', name 'zz selftest',
--  score 7). It confirmed that insert works, that a finished score cannot be
--  edited afterwards, and that nothing can be deleted from the page — which
--  also means the page cannot remove it. This can:
-- ============================================================================
delete from public.dcn_quiz_scores   where slug = 'zz-selftest';
delete from public.dcomm_quiz_scores where slug = 'zz-selftest';
delete from public.dsp_quiz_scores   where slug = 'zz-selftest';
