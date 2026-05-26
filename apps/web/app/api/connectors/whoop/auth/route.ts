import { NextResponse } from 'next/server';

export async function GET() {
  const params = new URLSearchParams({
    client_id: process.env.WHOOP_CLIENT_ID!,
    redirect_uri: process.env.WHOOP_REDIRECT_URI!,
    response_type: 'code',
    scope: 'read:recovery read:sleep read:workout read:body_measurement read:cycles offline',
  });

  return NextResponse.redirect(
    `https://api.prod.whoop.com/oauth/oauth2/auth?${params}`
  );
}
