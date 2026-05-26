import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  const res = await fetch(`${agentUrl}/score/momentum`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => null);

  if (!res?.ok) return NextResponse.json({ total: 0, body: 0, money: 0, work: 0, admin: 0 });
  return NextResponse.json(await res.json());
}
