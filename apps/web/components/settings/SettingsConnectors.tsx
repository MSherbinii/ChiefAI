'use client';
import { Mail, Calendar, GitBranch, Activity, BookOpen } from 'lucide-react';
import { ConnectorCard } from './ConnectorCard';
import type { ConnectorState } from '@/lib/connectors';

interface Props {
  states: Record<string, ConnectorState>;
}

function getState(states: Record<string, ConnectorState>, id: string): ConnectorState {
  return states[id] ?? {
    connector: id,
    status: 'disconnected',
    lastSynced: null,
    extra: null,
    errorMessage: null,
  };
}

export function SettingsConnectors({ states }: Props) {
  async function connectGitHub(pat: string, username: string) {
    const res = await fetch('/api/connectors/github/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pat, username }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    window.location.reload();
  }

  async function connectIMAP(email: string, password: string, imap_host: string, imap_port: number) {
    const res = await fetch('/api/connectors/imap/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, imap_host, imap_port }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    window.location.reload();
  }

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-[var(--v2-text)]">Connectors</h2>
        <p className="text-[12px] text-[var(--v2-muted)] mt-0.5">
          Connect your sources. Chief builds your Life Graph from these.
        </p>
      </div>
      <div className="space-y-2">
        <ConnectorCard
          id="gmail"
          name="Gmail"
          description="Email threads, subscriptions, receipts, contacts"
          icon={Mail}
          {...getState(states, 'gmail')}
          connectHref="/api/connectors/google/auth"
        />
        <ConnectorCard
          id="google_calendar"
          name="Google Calendar"
          description="Schedule, deadlines, availability"
          icon={Calendar}
          {...getState(states, 'google_calendar')}
          connectHref="/api/connectors/google/auth"
        />
        <ConnectorCard
          id="github"
          name="GitHub"
          description="Repos, commits, activity, PRs"
          icon={GitBranch}
          {...getState(states, 'github')}
          onPATConnect={connectGitHub}
        />
        <ConnectorCard
          id="whoop"
          name="WHOOP"
          description="Sleep, recovery, strain, HRV"
          icon={Activity}
          {...getState(states, 'whoop')}
          connectHref="/api/connectors/whoop/auth"
        />
        <ConnectorCard
          id="imap_uni"
          name="University Email"
          description="Thesis conversations, professor threads, university admin"
          icon={BookOpen}
          {...getState(states, 'imap_uni')}
          onIMAPConnect={connectIMAP}
        />
      </div>
    </section>
  );
}
