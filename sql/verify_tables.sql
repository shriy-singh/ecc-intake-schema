-- Confirms the three tables exist in Supabase and test_chats holds the test set.
-- Expected: requests 0, handoffs 0, test_chats 80, routine chats 30, handoff chats 10.
select 'requests' as table_name, count(*) as row_count from public.requests
union all select 'handoffs', count(*) from public.handoffs
union all select 'test_chats', count(*) from public.test_chats
union all select 'test_chats routine chats', count(distinct chat_id) from public.test_chats where chat_label = 'routine'
union all select 'test_chats handoff chats', count(distinct chat_id) from public.test_chats where chat_label = 'handoff';
