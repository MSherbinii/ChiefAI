import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const { id } = await request.json();
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { data: item } = await supabase
    .from('approval_queue')
    .select('agent, action_type')
    .eq('id', id)
    .eq('user_id', user.id)
    .maybeSingle();

  if (item) {
    await supabase.from('approval_patterns').upsert({
      user_id: user.id,
      agent: item.agent,
      action_category: item.action_type.split('_')[0],
      tool_name: item.action_type,
      auto_approve: true,
      auto_approve_set_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }, { onConflict: 'user_id,agent,tool_name' });
  }

  return NextResponse.json({ ok: true });
}
