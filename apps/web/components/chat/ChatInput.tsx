'use client';
import { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/design-system';
import { SendHorizontal, Mic, MicOff } from 'lucide-react';
import { cn } from '@/lib/cn';

// Quick-action slash commands shown as suggestions
const SLASH_COMMANDS = [
  { cmd: '/brief', desc: "Generate today's morning brief" },
  { cmd: '/score', desc: 'Calculate momentum score' },
  { cmd: '/scan', desc: 'Run proactive intelligence scan' },
  { cmd: '/health', desc: 'Ask Pulse about your health' },
  { cmd: '/email', desc: 'Ask Echo about your emails' },
  { cmd: '/projects', desc: 'Ask Forge about your projects' },
];

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  const filteredCommands = value.startsWith('/')
    ? SLASH_COMMANDS.filter(c => c.cmd.startsWith(value.toLowerCase()))
    : [];

  function submit(content?: string) {
    const text = (content ?? value).trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
    setShowSuggestions(false);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
    if (e.key === 'Escape') setShowSuggestions(false);
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setValue(e.target.value);
    setShowSuggestions(e.target.value.startsWith('/'));
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  async function toggleRecording() {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorder.ondataavailable = e => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        // For now, show a placeholder — voice transcription will be wired in Phase 1B
        setValue(prev => prev + '[Voice input — transcription coming soon]');
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      // Mic not available
    }
  }

  return (
    <div className="p-3 border-t border-[var(--v2-border)]">
      {/* Slash command suggestions */}
      {showSuggestions && filteredCommands.length > 0 && (
        <div className="mb-2 rounded-[10px] border border-[var(--v2-border)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))] overflow-hidden">
          {filteredCommands.map(c => (
            <button
              key={c.cmd}
              onClick={() => { setValue(c.cmd + ' '); setShowSuggestions(false); textareaRef.current?.focus(); }}
              className="w-full flex items-center gap-3 px-3 py-2 hover:bg-[rgba(247,240,255,0.05)] transition-colors text-left"
            >
              <span className="text-[13px] font-mono text-[var(--v2-violet)]">{c.cmd}</span>
              <span className="text-[12px] text-[var(--v2-muted)]">{c.desc}</span>
            </button>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2 bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] rounded-[14px] px-3 py-2 focus-within:border-[var(--v2-border-focus)] transition-colors">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask Chief anything… or type / for commands"
          rows={1}
          disabled={disabled}
          className="flex-1 bg-transparent text-sm text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] resize-none outline-none leading-relaxed"
          style={{ minHeight: '24px', maxHeight: '160px' }}
        />
        <div className="flex items-center gap-1 flex-shrink-0 mb-0.5">
          <button
            onClick={toggleRecording}
            className={cn(
              'w-7 h-7 rounded-[8px] flex items-center justify-center transition-all',
              isRecording
                ? 'bg-[rgba(255,79,109,0.15)] text-[var(--v2-crit)] animate-pulse'
                : 'text-[var(--v2-subtle)] hover:text-[var(--v2-muted)] hover:bg-[rgba(247,240,255,0.06)]'
            )}
            title={isRecording ? 'Stop recording' : 'Voice input'}
          >
            {isRecording ? <MicOff size={13} /> : <Mic size={13} />}
          </button>
          <Button
            variant="solid"
            size="xs"
            onClick={() => submit()}
            disabled={!value.trim() || disabled}
          >
            <SendHorizontal size={12} />
          </Button>
        </div>
      </div>
      <p className="text-[10px] text-[var(--v2-subtle)] mt-1.5 px-1">
        Enter to send · Shift+Enter for newline · / for commands
      </p>
    </div>
  );
}
