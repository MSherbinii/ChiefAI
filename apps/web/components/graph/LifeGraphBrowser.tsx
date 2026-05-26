'use client';
import { useState } from 'react';
import { Panel, StatusDot } from '@/components/design-system';
import { User, Briefcase, Wrench, MapPin, Lightbulb, Calendar, GitBranch, Search } from 'lucide-react';
import { cn } from '@/lib/cn';

const TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  person:   { icon: User,       color: 'text-[#8A3AFF]',         label: 'People' },
  project:  { icon: Briefcase,  color: 'text-[#38F2A8]',         label: 'Projects' },
  tool:     { icon: Wrench,     color: 'text-[#18E6D8]',         label: 'Tools' },
  place:    { icon: MapPin,     color: 'text-[#F7A93B]',         label: 'Places' },
  concept:  { icon: Lightbulb,  color: 'text-[var(--v2-violet)]', label: 'Concepts' },
  event:    { icon: Calendar,   color: 'text-[#3B82F6]',         label: 'Events' },
  document: { icon: GitBranch,  color: 'text-[var(--v2-muted)]', label: 'Documents' },
};

interface Entity {
  id: string;
  type: string;
  name: string;
  properties: Record<string, unknown> | null;
  source: string | null;
  created_at: string;
}

interface Fact {
  id: string;
  predicate: string;
  object: string;
  confidence: number;
  entities: { name: string; type: string } | null;
}

interface Props {
  entities: Entity[];
  countByType: Record<string, number>;
  facts: Fact[];
  relationshipCount: number;
}

export function LifeGraphBrowser({ entities, countByType, facts, relationshipCount }: Props) {
  const [search, setSearch] = useState('');
  const [activeType, setActiveType] = useState<string | null>(null);

  const filtered = entities.filter(e => {
    const matchSearch = !search || e.name.toLowerCase().includes(search.toLowerCase());
    const matchType = !activeType || e.type === activeType;
    return matchSearch && matchType;
  });

  const totalEntities = entities.length;

  if (totalEntities === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center space-y-3">
        <GitBranch size={32} className="text-[var(--v2-violet)] opacity-40" />
        <p className="text-sm font-medium text-[var(--v2-text)]">Life Graph is empty.</p>
        <p className="text-[13px] text-[var(--v2-muted)] max-w-xs">
          Connect Gmail and GitHub to start building your knowledge graph.
          Entities (people, projects, tools) are extracted automatically.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-3xl">
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{totalEntities}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Entities</p>
        </Panel>
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{relationshipCount}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Relationships</p>
        </Panel>
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{facts.length}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Recent Facts</p>
        </Panel>
      </div>

      {/* Type filter pills */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveType(null)}
          className={cn(
            'px-2.5 py-1 rounded-full text-[12px] font-medium border transition-all',
            !activeType
              ? 'bg-[rgba(138,58,255,0.12)] border-[rgba(138,58,255,0.35)] text-[var(--v2-text)]'
              : 'border-[rgba(247,240,255,0.10)] text-[var(--v2-muted)] hover:border-[rgba(247,240,255,0.18)]'
          )}
        >
          All ({totalEntities})
        </button>
        {Object.entries(countByType).map(([type, count]) => {
          const cfg = TYPE_CONFIG[type] ?? TYPE_CONFIG.concept;
          const Icon = cfg.icon;
          return (
            <button
              key={type}
              onClick={() => setActiveType(activeType === type ? null : type)}
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-medium border transition-all',
                activeType === type
                  ? 'bg-[rgba(138,58,255,0.12)] border-[rgba(138,58,255,0.35)] text-[var(--v2-text)]'
                  : 'border-[rgba(247,240,255,0.10)] text-[var(--v2-muted)] hover:border-[rgba(247,240,255,0.18)]'
              )}
            >
              <Icon size={11} className={cfg.color} />
              {cfg.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)]" />
        <input
          type="text"
          placeholder="Search entities..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full h-9 pl-9 pr-4 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)] transition-colors"
        />
      </div>

      {/* Entity grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {filtered.slice(0, 50).map(entity => {
          const cfg = TYPE_CONFIG[entity.type] ?? TYPE_CONFIG.concept;
          const Icon = cfg.icon;
          const props = entity.properties as Record<string, string> ?? {};
          const subtitle = props.email ?? props.institution ?? props.language ?? entity.source ?? '';
          return (
            <Panel key={entity.id} className="p-3 flex items-start gap-3" interactive>
              <div className="w-7 h-7 rounded-[8px] bg-[rgba(247,240,255,0.06)] flex items-center justify-center flex-shrink-0 mt-0.5">
                <Icon size={13} className={cfg.color} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium text-[var(--v2-text)] truncate">{entity.name}</p>
                {subtitle && <p className="text-[11px] text-[var(--v2-subtle)] truncate">{subtitle}</p>}
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] uppercase tracking-[0.08em] text-[var(--v2-subtle)]">{cfg.label}</span>
                  {entity.source && (
                    <span className="text-[10px] text-[var(--v2-subtle)] opacity-60">via {entity.source}</span>
                  )}
                </div>
              </div>
            </Panel>
          );
        })}
      </div>

      {filtered.length > 50 && (
        <p className="text-[12px] text-[var(--v2-muted)] text-center">
          Showing 50 of {filtered.length} — use search to narrow down
        </p>
      )}

      {/* Recent facts */}
      {facts.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-[12px] uppercase tracking-[0.08em] font-semibold text-[var(--v2-muted)]">
            Recent Facts
          </h3>
          <div className="space-y-1.5">
            {facts.slice(0, 10).map(fact => (
              <div key={fact.id} className="flex items-center gap-2 text-[12px]">
                <span className="text-[var(--v2-text-dim)] font-medium truncate max-w-[120px]">
                  {(fact as any).entities?.name ?? 'Unknown'}
                </span>
                <span className="text-[var(--v2-subtle)]">{fact.predicate}</span>
                <span className="text-[var(--v2-muted)] truncate">{fact.object}</span>
                <span className="text-[var(--v2-subtle)] ml-auto flex-shrink-0">
                  {Math.round(fact.confidence * 100)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
