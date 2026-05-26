import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { data: profile } = await supabase.from('profiles').select('display_name').eq('id', user.id).maybeSingle();
  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';

  const res = await fetch(`${agentUrl}/brief/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id, user_name: profile?.display_name ?? 'there' }),
  }).catch(() => null);

  if (!res?.ok) return NextResponse.json({ greeting: 'Brief generation failed. Make sure the agent service is running.' });
  return NextResponse.json(await res.json());
}
