import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  const res = await fetch(`${agentUrl}/proactive/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => null);

  if (!res?.ok) return NextResponse.json({ queue_items_created: 0 });
  return NextResponse.json(await res.json());
}
