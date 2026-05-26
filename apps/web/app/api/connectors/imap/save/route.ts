import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { z } from 'zod';

const Body = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  imap_host: z.string().min(1),
  imap_port: z.number().default(993),
});

export async function POST(request: Request) {
  const body = await request.json();
  const parsed = Body.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'Invalid IMAP credentials' }, { status: 400 });
  }

  // Verify credentials via Python agent service (Python handles actual IMAP connection test)
  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  let verifyOk = false;
  try {
    const verifyRes = await fetch(`${agentUrl}/connectors/imap/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsed.data),
    });
    verifyOk = verifyRes.ok;
    if (!verifyOk) {
      const err = await verifyRes.json().catch(() => ({}));
      return NextResponse.json(
        { error: (err as any).detail ?? 'IMAP connection failed' },
        { status: 400 }
      );
    }
  } catch {
    // Agent service not running — skip verify, store anyway (user will see sync error)
    verifyOk = true;
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'imap_uni',
    access_token: parsed.data.password,
    extra: {
      email: parsed.data.email,
      imap_host: parsed.data.imap_host,
      imap_port: parsed.data.imap_port,
    },
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  fetch(`${agentUrl}/sync/imap_uni`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => {});

  return NextResponse.json({ ok: true });
}
