import Link from 'next/link';
import { Button } from '@/components/design-system';
import { Zap } from 'lucide-react';

export function ConnectGate() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center space-y-5 pb-16">
      <div className="w-14 h-14 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
        <Zap size={22} className="text-white" />
      </div>
      <div className="space-y-2 max-w-sm">
        <h2 className="text-lg font-semibold text-[var(--v2-text)]">Connect your first source</h2>
        <p className="text-[13px] text-[var(--v2-muted)] leading-relaxed">
          Chief needs at least Gmail connected to build your Morning Brief. Connect it in Settings — takes about 30 seconds.
        </p>
      </div>
      <Link href="/settings">
        <Button variant="solid" size="md">Go to Settings →</Button>
      </Link>
    </div>
  );
}
