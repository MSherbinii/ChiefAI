import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(
  request: Request,
  { params }: { params: Promise<{ caseId: string }> }
) {
  const { caseId } = await params;
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const body = await request.json().catch(() => ({}));
  const note = body.note || 'Resolved by user';

  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  const res = await fetch(`${agentUrl}/email/case/${caseId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id, note }),
  }).catch(() => null);

  if (!res?.ok) return NextResponse.json({ error: 'Failed to resolve' }, { status: 500 });
  return NextResponse.json({ ok: true });
}
