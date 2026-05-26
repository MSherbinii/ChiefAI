// apps/web/app/api/chat/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const body = await request.json();
  const agentServiceUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';

  // Attach user_id so agents can load Life Graph context
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const enrichedBody = { ...body, user_id: user?.id ?? null };

  try {
    const res = await fetch(`${agentServiceUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(enrichedBody),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({
      reply: "Hey — I'm Chief. The agent service is starting up. Try again in a moment.",
      agent: 'Chief',
    });
  }
}
