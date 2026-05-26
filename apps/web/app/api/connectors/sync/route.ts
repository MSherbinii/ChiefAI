import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { z } from 'zod';

const Body = z.object({ connector: z.enum(['google', 'github', 'whoop', 'imap_uni']) });

export async function POST(request: Request) {
  const body = await request.json();
  const parsed = Body.safeParse(body);
  if (!parsed.success) return NextResponse.json({ error: 'Invalid connector' }, { status: 400 });

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  const endpoint = parsed.data.connector === 'imap_uni' ? 'imap_uni' : parsed.data.connector;

  fetch(`${agentUrl}/sync/${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => {});

  return NextResponse.json({ ok: true, started: parsed.data.connector });
}
