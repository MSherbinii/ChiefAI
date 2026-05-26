import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const { id } = await request.json();
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  await supabase
    .from('approval_queue')
    .update({ status: 'approved' })
    .eq('id', id)
    .eq('user_id', user.id);

  // Fire-and-forget: send approval signal to RL feedback loop
  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  fetch(`${agentUrl}/feedback/approval`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ queue_item_id: id, user_id: user.id, approved: true }),
  }).catch(() => {});

  return NextResponse.json({ ok: true });
}
