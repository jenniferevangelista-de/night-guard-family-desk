-- Fictional demo data for the recording. No real child, chat or account.
TRUNCATE case_events, case_drafts, case_steps, case_shares, cases;
-- start the recording with an empty agent chat history
TRUNCATE chat_thread_viewer_state, chat_thread_shares, chat_threads;
\set org '''cc492695c44447b5b58bab3f63498cc8'''
\set me '''dev@local.test'''

INSERT INTO cases (id, child_alias, app, risk_type, severity, flagged_phrase, detected_at, status, closing_note, owner_email, org_id, visibility) VALUES
('11111111-1111-4111-8111-111111111111', 'Theo', 'Discord', 'bullying', 'medium', 'nobody in the server wants you here, just leave already', '2026-10-28T21:12:00Z', 'closed', 'Talked with Theo, the school counselor spoke with the class. Checked in a week later: all good.', :me, :org, 'org'),
('22222222-2222-4222-8222-222222222222', 'Lia', 'Roblox', 'scam', 'low', 'give me your password and I''ll send you 10,000 free Robux', '2026-11-01T18:40:00Z', 'open', NULL, :me, :org, 'org');

INSERT INTO case_steps (id, case_id, kind, title, detail, status, proposed_by, position, owner_email, org_id, updated_at) VALUES
(gen_random_uuid()::text, '11111111-1111-4111-8111-111111111111', 'talk', 'Talk with Theo tonight', 'Tell him it is not his fault and ask how long it has been going on.', 'done', 'agent', 1, :me, :org, '2026-10-28T22:00:00Z'),
(gen_random_uuid()::text, '11111111-1111-4111-8111-111111111111', 'support', 'Contact the school counselor', 'The server is his class group; ask the counselor to talk with the class.', 'done', 'agent', 2, :me, :org, '2026-10-29T10:00:00Z'),
(gen_random_uuid()::text, '22222222-2222-4222-8222-222222222222', 'talk', 'Talk about passwords', 'Free Robux offers are scams. Nobody needs your password.', 'done', 'agent', 1, :me, :org, '2026-11-01T19:30:00Z'),
(gen_random_uuid()::text, '22222222-2222-4222-8222-222222222222', 'block', 'Block and report the account', 'Use Report on the profile, then Block.', 'approved', 'agent', 2, :me, :org, '2026-11-01T19:31:00Z'),
(gen_random_uuid()::text, '22222222-2222-4222-8222-222222222222', 'follow_up', 'Turn on 2-step verification', 'Change the password together and enable 2-step verification.', 'approved', 'parent', 3, :me, :org, '2026-11-01T19:32:00Z');

INSERT INTO case_events (id, case_id, actor, message, owner_email, org_id, created_at) VALUES
(gen_random_uuid()::text, '11111111-1111-4111-8111-111111111111', 'night_guard', 'Alert received: bullying on Discord (medium). Only the flagged phrase was shared.', :me, :org, '2026-10-28T21:12:00Z'),
(gen_random_uuid()::text, '11111111-1111-4111-8111-111111111111', 'parent', 'Case closed: Talked with Theo, the school counselor spoke with the class.', :me, :org, '2026-11-02T20:00:00Z'),
(gen_random_uuid()::text, '22222222-2222-4222-8222-222222222222', 'night_guard', 'Alert received: scam on Roblox (low). Only the flagged phrase was shared.', :me, :org, '2026-11-01T18:40:00Z');
