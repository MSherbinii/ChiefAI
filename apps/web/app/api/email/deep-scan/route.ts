import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';

  const res = await fetch(`${agentUrl}/email/deep-scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
    signal: AbortSignal.timeout(10000),
  }).catch(() => null);

  if (!res?.ok) {
    return NextResponse.json({ error: 'Failed to start scan' }, { status: 500 });
  }
  return NextResponse.json({ ok: true, message: 'Deep scan started' });
}

export async function GET() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  const res = await fetch(`${agentUrl}/email/scan-status/${user.id}`).catch(() => null);
  if (!res?.ok) return NextResponse.json({ status: 'unknown' });
  return NextResponse.json(await res.json());
}
