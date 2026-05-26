import { TopBar } from '@/components/layout/TopBar';
import { ChatPanel } from '@/components/chat/ChatPanel';

export default function ChatPage() {
  return (
    <>
      <TopBar title="Chat" />
      <div className="flex-1 overflow-hidden">
        <ChatPanel />
      </div>
    </>
  );
}
