import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');
  const error = searchParams.get('error');

  if (error || !code) {
    return NextResponse.redirect(`${origin}/settings?error=whoop_auth_failed`);
  }

  const tokenRes = await fetch('https://api.prod.whoop.com/oauth/oauth2/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      code,
      client_id: process.env.WHOOP_CLIENT_ID!,
      client_secret: process.env.WHOOP_CLIENT_SECRET!,
      redirect_uri: process.env.WHOOP_REDIRECT_URI!,
      grant_type: 'authorization_code',
    }),
  });

  if (!tokenRes.ok) {
    return NextResponse.redirect(`${origin}/settings?error=whoop_token_failed`);
  }

  const tokens = await tokenRes.json();

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.redirect(`${origin}/login`);

  const expiry = new Date(Date.now() + tokens.expires_in * 1000).toISOString();

  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'whoop',
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    token_expiry: expiry,
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  fetch(`${agentUrl}/sync/whoop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => {});

  return NextResponse.redirect(`${origin}/settings?connected=whoop`);
}
