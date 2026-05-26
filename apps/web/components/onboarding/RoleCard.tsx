import { cn } from '@/lib/cn';
import type { LucideIcon } from 'lucide-react';

interface RoleCardProps {
  label: string;
  icon: LucideIcon;
  selected: boolean;
  onToggle: () => void;
}

export function RoleCard({ label, icon: Icon, selected, onToggle }: RoleCardProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        'relative flex flex-col items-center gap-3 p-4 rounded-[14px] border transition-all duration-150 cursor-pointer select-none text-center',
        selected
          ? 'border-[rgba(138,58,255,0.55)] bg-[rgba(138,58,255,0.10)] shadow-[0_0_0_1px_rgba(138,58,255,0.25)]'
          : 'border-[rgba(247,240,255,0.10)] bg-[rgba(247,240,255,0.03)] hover:border-[rgba(247,240,255,0.18)] hover:bg-[rgba(247,240,255,0.06)]'
      )}
    >
      <div className={cn(
        'w-10 h-10 rounded-[10px] flex items-center justify-center transition-colors',
        selected ? 'bg-[rgba(138,58,255,0.20)]' : 'bg-[rgba(247,240,255,0.06)]'
      )}>
        <Icon size={18} className={selected ? 'text-[var(--v2-violet)]' : 'text-[var(--v2-muted)]'} />
      </div>
      <span className={cn(
        'text-[13px] font-medium transition-colors',
        selected ? 'text-[var(--v2-text)]' : 'text-[var(--v2-muted)]'
      )}>
        {label}
      </span>
      {selected && (
        <div className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-[var(--v2-violet)]" />
      )}
    </button>
  );
}
