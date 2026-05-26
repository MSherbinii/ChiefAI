import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { z } from 'zod';

const Body = z.object({
  pat: z.string().min(10),
  username: z.string().min(1),
});

export async function POST(request: Request) {
  const body = await request.json();
  const parsed = Body.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'Invalid PAT or username' }, { status: 400 });
  }

  // Verify PAT works against GitHub API
  const verifyRes = await fetch('https://api.github.com/user', {
    headers: {
      Authorization: `token ${parsed.data.pat}`,
      'User-Agent': 'chief-app',
    },
  });

  if (!verifyRes.ok) {
    return NextResponse.json({ error: 'GitHub PAT is invalid or expired' }, { status: 400 });
  }

  const ghUser = await verifyRes.json();

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'github',
    access_token: parsed.data.pat,
    extra: { username: ghUser.login, avatar_url: ghUser.avatar_url },
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  fetch(`${agentUrl}/sync/github`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => {});

  return NextResponse.json({ ok: true, username: ghUser.login });
}
