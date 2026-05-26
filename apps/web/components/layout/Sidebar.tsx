'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/cn';
import { Sun, MessageSquare, LayoutGrid, GitBranch, RotateCcw, Settings, Zap } from 'lucide-react';

const NAV = [
  { href: '/today',   icon: Sun,           label: 'Today' },
  { href: '/chat',    icon: MessageSquare, label: 'Chat' },
  { href: '/domains', icon: LayoutGrid,    label: 'Domains' },
  { href: '/graph',   icon: GitBranch,     label: 'Life Graph' },
  { href: '/replay',  icon: RotateCcw,     label: 'Replay' },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-14 lg:w-52 flex-shrink-0 flex flex-col h-full border-r border-[var(--v2-border)] bg-[var(--v2-sidebar)]">
      <div className="h-12 flex items-center px-4 border-b border-[var(--v2-border)]">
        <span className="hidden lg:flex items-center gap-2">
          <Zap size={16} className="text-[var(--v2-violet)]" />
          <span className="text-sm font-bold text-[var(--v2-text)] tracking-wider">CHIEF</span>
        </span>
        <Zap size={16} className="lg:hidden text-[var(--v2-violet)]" />
      </div>
      <nav className="flex-1 py-3 space-y-0.5 px-2">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-2 py-2 rounded-[10px] transition-all duration-100',
                'text-[13px] font-medium',
                active
                  ? 'bg-[rgba(138,58,255,0.12)] text-[var(--v2-text)] border border-[rgba(138,58,255,0.20)]'
                  : 'text-[var(--v2-muted)] hover:bg-[rgba(247,240,255,0.05)] hover:text-[var(--v2-text-dim)]'
              )}
            >
              <Icon size={15} />
              <span className="hidden lg:block">{label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="p-2 border-t border-[var(--v2-border)]">
        <Link
          href="/settings"
          className={cn(
            'flex items-center gap-3 px-2 py-2 rounded-[10px] transition-all duration-100',
            'text-[13px] font-medium',
            pathname.startsWith('/settings')
              ? 'bg-[rgba(138,58,255,0.12)] text-[var(--v2-text)] border border-[rgba(138,58,255,0.20)]'
              : 'text-[var(--v2-muted)] hover:bg-[rgba(247,240,255,0.05)] hover:text-[var(--v2-text-dim)]'
          )}
        >
          <Settings size={15} />
          <span className="hidden lg:block">Settings</span>
        </Link>
      </div>
    </aside>
  );
}
