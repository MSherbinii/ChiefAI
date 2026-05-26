'use client';
import { useState } from 'react';
import { Panel, Button, StatusDot } from '@/components/design-system';
import type { LucideIcon } from 'lucide-react';
import type { ConnectorStatus } from '@/lib/connectors';
import { toast } from 'sonner';
import { ConnectorSyncButton } from './ConnectorSyncButton';

interface ConnectorCardProps {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  status: ConnectorStatus;
  lastSynced: string | null;
  extra: Record<string, string> | null;
  errorMessage: string | null;
  connectHref?: string;
  syncConnector?: string;
  onPATConnect?: (pat: string, username: string) => Promise<void>;
  onIMAPConnect?: (email: string, password: string, host: string, port: number) => Promise<void>;
}

const STATUS_SEVERITY: Record<ConnectorStatus, 'ok' | 'info' | 'high' | 'med'> = {
  connected:    'ok',
  syncing:      'info',
  error:        'high',
  disconnected: 'med',
};

const inputCls = 'w-full h-8 px-3 rounded-[8px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-[13px] focus:outline-none focus:border-[var(--v2-border-focus)]';

export function ConnectorCard({
  id, name, description, icon: Icon,
  status, lastSynced, extra, errorMessage,
  connectHref, syncConnector, onPATConnect, onIMAPConnect,
}: ConnectorCardProps) {
  const [showForm, setShowForm] = useState(false);
  const [patValue, setPatValue] = useState('');
  const [patUser, setPatUser] = useState('');
  const [imapEmail, setImapEmail] = useState('');
  const [imapPass, setImapPass] = useState('');
  const [imapHost, setImapHost] = useState('');
  const [imapPort, setImapPort] = useState(993);
  const [loading, setLoading] = useState(false);

  async function handlePATSubmit() {
    if (!onPATConnect) return;
    setLoading(true);
    try {
      await onPATConnect(patValue, patUser);
      toast.success(`GitHub connected as @${patUser}`);
      setShowForm(false);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to connect GitHub');
    } finally { setLoading(false); }
  }

  async function handleIMAPSubmit() {
    if (!onIMAPConnect) return;
    setLoading(true);
    try {
      await onIMAPConnect(imapEmail, imapPass, imapHost, imapPort);
      toast.success('University email connected');
      setShowForm(false);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'IMAP connection failed');
    } finally { setLoading(false); }
  }

  return (
    <Panel className="p-4 space-y-3">
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-[10px] bg-[rgba(138,58,255,0.12)] border border-[rgba(138,58,255,0.20)] flex items-center justify-center flex-shrink-0">
          <Icon size={15} className="text-[var(--v2-violet)]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-[var(--v2-text)]">{name}</span>
            {extra?.email && <span className="text-[11px] text-[var(--v2-muted)]">{extra.email}</span>}
            {extra?.username && <span className="text-[11px] text-[var(--v2-muted)]">@{extra.username}</span>}
          </div>
          <p className="text-[12px] text-[var(--v2-muted)] truncate">{description}</p>
          {errorMessage && <p className="text-[11px] text-[var(--v2-crit)] mt-0.5">{errorMessage}</p>}
          {lastSynced && status === 'connected' && (
            <p className="text-[10px] text-[var(--v2-subtle)] mt-0.5">
              Last synced {new Date(lastSynced).toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusDot severity={STATUS_SEVERITY[status]} size="xs" showLabel />
          {status === 'disconnected' || status === 'error' ? (
            connectHref ? (
              <Button variant="solid" size="xs" onClick={() => { window.location.href = connectHref; }}>
                Connect
              </Button>
            ) : (
              <Button variant="solid" size="xs" onClick={() => setShowForm(v => !v)}>
                {showForm ? 'Cancel' : 'Connect'}
              </Button>
            )
          ) : (
            <>
              {syncConnector && status === 'connected' && (
                <ConnectorSyncButton connector={syncConnector} />
              )}
              <Button variant="outline" size="xs" disabled={status === 'syncing'}>
                {status === 'syncing' ? 'Syncing…' : 'Synced'}
              </Button>
            </>
          )}
        </div>
      </div>

      {showForm && onPATConnect && (
        <div className="space-y-2 pt-1 border-t border-[var(--v2-border)]">
          <input className={inputCls} placeholder="GitHub username" value={patUser} onChange={e => setPatUser(e.target.value)} />
          <input className={inputCls} placeholder="Personal Access Token (ghp_...)" type="password" value={patValue} onChange={e => setPatValue(e.target.value)} />
          <Button variant="solid" size="sm" loading={loading} onClick={handlePATSubmit}>Save PAT</Button>
        </div>
      )}

      {showForm && onIMAPConnect && (
        <div className="space-y-2 pt-1 border-t border-[var(--v2-border)]">
          <input className={inputCls} placeholder="University email address" value={imapEmail} onChange={e => setImapEmail(e.target.value)} />
          <input className={inputCls} placeholder="Password or app password" type="password" value={imapPass} onChange={e => setImapPass(e.target.value)} />
          <input className={inputCls} placeholder="IMAP host (e.g. imap.uni-example.de)" value={imapHost} onChange={e => setImapHost(e.target.value)} />
          <input className={inputCls} placeholder="Port (default 993)" type="number" value={imapPort} onChange={e => setImapPort(Number(e.target.value))} />
          <Button variant="solid" size="sm" loading={loading} onClick={handleIMAPSubmit}>Save IMAP</Button>
        </div>
      )}
    </Panel>
  );
}
