import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { z } from 'zod';

const Body = z.object({
  display_name: z.string().min(1).max(100),
  timezone: z.string().min(1),
  roles: z.array(z.string()),
  focuses: z.array(z.string()).max(3),
});

export async function POST(request: Request) {
  const body = await request.json();
  const parsed = Body.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'Invalid input' }, { status: 400 });
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { display_name, timezone, roles, focuses } = parsed.data;

  const { error: profileError } = await supabase
    .from('profiles')
    .upsert({
      id: user.id,
      display_name,
      timezone,
    }, { onConflict: 'id' });

  if (profileError) {
    return NextResponse.json({ error: profileError.message }, { status: 500 });
  }

  if (focuses.length > 0) {
    const goals = focuses.map(focus => ({
      user_id: user.id,
      domain: 'projects',
      title: focus,
      status: 'active',
      progress: 0,
    }));
    await supabase.from('lg_goals').insert(goals);
  }

  return NextResponse.json({ ok: true });
}
