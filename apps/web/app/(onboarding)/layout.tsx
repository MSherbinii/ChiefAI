import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';

export default async function OnboardingLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const { data: profile } = await supabase
    .from('profiles')
    .select('display_name')
    .eq('id', user.id)
    .maybeSingle();

  if (profile?.display_name) redirect('/today');

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      {children}
    </div>
  );
}
