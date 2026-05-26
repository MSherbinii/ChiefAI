'use client';
import { useState, useRef } from 'react';
import { Upload, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/cn';

const DOC_TYPES = [
  { value: 'insurance_card', label: 'Insurance Card' },
  { value: 'letter', label: 'Letter / Document' },
  { value: 'id', label: 'ID / Passport' },
  { value: 'contract', label: 'Contract' },
  { value: 'document', label: 'Other' },
];

export function DocumentUpload() {
  const [docType, setDocType] = useState('insurance_card');
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('type', docType);
      const res = await fetch('/api/documents/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.ok) {
        setUploaded(data.extracted?.title ?? 'Document uploaded');
        toast.success(`Extracted: ${data.extracted?.summary ?? 'Document saved'}`);
      } else {
        toast.error(data.error ?? 'Upload failed');
      }
    } catch {
      toast.error('Upload failed');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2 flex-wrap">
        {DOC_TYPES.map(t => (
          <button
            key={t.value}
            onClick={() => setDocType(t.value)}
            className={cn(
              'px-2.5 py-1 rounded-full text-[12px] border transition-all',
              docType === t.value
                ? 'bg-[rgba(138,58,255,0.12)] border-[rgba(138,58,255,0.35)] text-[var(--v2-text)]'
                : 'border-[rgba(247,240,255,0.10)] text-[var(--v2-muted)]'
            )}
          >{t.label}</button>
        ))}
      </div>

      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'border-2 border-dashed rounded-[12px] p-6 text-center cursor-pointer transition-all',
          dragging
            ? 'border-[var(--v2-violet)] bg-[rgba(138,58,255,0.08)]'
            : 'border-[rgba(247,240,255,0.12)] hover:border-[rgba(247,240,255,0.20)] hover:bg-[rgba(247,240,255,0.03)]'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*,.pdf"
          className="hidden"
          onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        {uploading ? (
          <div className="space-y-2">
            <div className="w-8 h-8 rounded-full border-2 border-[var(--v2-violet)] border-t-transparent animate-spin mx-auto" />
            <p className="text-[13px] text-[var(--v2-muted)]">Extracting fields…</p>
          </div>
        ) : uploaded ? (
          <div className="space-y-2">
            <CheckCircle size={24} className="text-[var(--v2-ok)] mx-auto" />
            <p className="text-[13px] text-[var(--v2-text)]">{uploaded}</p>
            <button
              onClick={e => { e.stopPropagation(); setUploaded(null); }}
              className="text-[11px] text-[var(--v2-violet)] hover:underline"
            >Upload another</button>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload size={20} className="text-[var(--v2-subtle)] mx-auto" />
            <p className="text-[13px] text-[var(--v2-text)]">Drop a photo or click to upload</p>
            <p className="text-[11px] text-[var(--v2-subtle)]">Insurance cards, letters, IDs, contracts — Clerk extracts the fields</p>
          </div>
        )}
      </div>
    </div>
  );
}
