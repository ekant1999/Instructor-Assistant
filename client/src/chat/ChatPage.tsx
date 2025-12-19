import React, { useEffect, useRef } from 'react';
import { useChatStore } from './store';
import { ChatMessage } from './ChatMessage';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2 } from 'lucide-react';

export default function ChatPage() {
  const { messages, status } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  return (
    <div className="flex flex-col h-full w-full bg-background relative">
      <ScrollArea className="flex-1 w-full">
        <div className="flex flex-col min-h-full pb-32"> {/* Padding for fixed input */}
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground p-8">
              <div className="w-16 h-16 bg-secondary/50 rounded-2xl flex items-center justify-center mb-4">
                <span className="text-4xl">👋</span>
              </div>
              <h2 className="text-2xl font-semibold mb-2 text-foreground">Instructor Assistant</h2>
              <p>Ready to help with research, notes, and curriculum.</p>
            </div>
          )}
          
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {status && (
            <div className="max-w-3xl mx-auto px-14 py-4 flex items-center gap-3 text-sm text-muted-foreground animate-in fade-in slide-in-from-bottom-2">
               <Loader2 className="h-4 w-4 animate-spin" />
               <span>{status}</span>
            </div>
          )}
          
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
