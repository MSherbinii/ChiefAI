import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { TopBar } from '@/components/layout/TopBar';
import { LifeGraphBrowser } from '@/components/graph/LifeGraphBrowser';

export default async function GraphPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  // Fetch entities
  const { data: entities } = await supabase
    .from('entities')
    .select('id, type, name, properties, source, created_at')
    .eq('user_id', user.id)
    .order('updated_at', { ascending: false })
    .limit(100);

  // Fetch entity counts by type
  const { data: typeCounts } = await supabase
    .from('entities')
    .select('type')
    .eq('user_id', user.id);

  const countByType: Record<string, number> = {};
  for (const row of typeCounts ?? []) {
    countByType[row.type] = (countByType[row.type] ?? 0) + 1;
  }

  // Fetch recent facts
  const { data: facts } = await supabase
    .from('facts')
    .select('id, predicate, object, confidence, subject_id, entities!facts_subject_id_fkey(name, type)')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
    .limit(20);

  // Total relationships
  const { count: relCount } = await supabase
    .from('relationships')
    .select('id', { count: 'exact', head: true })
    .eq('user_id', user.id);

  return (
    <>
      <TopBar title="Life Graph" />
      <main className="flex-1 overflow-y-auto p-4">
        <LifeGraphBrowser
          entities={entities ?? []}
          countByType={countByType}
          facts={(facts ?? []) as any[]}
          relationshipCount={relCount ?? 0}
        />
      </main>
    </>
  );
}
