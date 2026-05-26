import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const body = await request.json();
  const agentServiceUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';

  try {
    const res = await fetch(`${agentServiceUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
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
