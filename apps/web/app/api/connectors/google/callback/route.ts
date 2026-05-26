import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');
  const error = searchParams.get('error');

  if (error || !code) {
    return NextResponse.redirect(`${origin}/settings?error=google_auth_failed`);
  }

  const tokenRes = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      code,
      client_id: process.env.GOOGLE_CLIENT_ID!,
      client_secret: process.env.GOOGLE_CLIENT_SECRET!,
      redirect_uri: process.env.GOOGLE_REDIRECT_URI!,
      grant_type: 'authorization_code',
    }),
  });

  if (!tokenRes.ok) {
    return NextResponse.redirect(`${origin}/settings?error=token_exchange_failed`);
  }

  const tokens = await tokenRes.json();

  const userInfoRes = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  const userInfo = await userInfoRes.json();

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.redirect(`${origin}/login`);

  const expiry = new Date(Date.now() + tokens.expires_in * 1000).toISOString();

  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'gmail',
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    token_expiry: expiry,
    extra: { email: userInfo.email },
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'google_calendar',
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    token_expiry: expiry,
    extra: { email: userInfo.email },
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  // Fire-and-forget sync trigger
  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  fetch(`${agentUrl}/sync/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => {});

  return NextResponse.redirect(`${origin}/settings?connected=google`);
}
