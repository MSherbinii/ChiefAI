import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const { id } = await request.json();
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  await supabase
    .from('approval_queue')
    .update({ status: 'rejected' })
    .eq('id', id)
    .eq('user_id', user.id);

  return NextResponse.json({ ok: true });
}
