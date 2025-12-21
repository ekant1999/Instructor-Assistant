import React, { useRef, useEffect } from 'react';
import { Send, Sparkles, Paperclip, Mic } from 'lucide-react';
import { useChatStore } from './store';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function ChatInput({ className }: { className?: string }) {
  const { input, setInput, sendMessage, isStreaming } = useChatStore();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim() && !isStreaming) {
        sendMessage(input);
      }
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <div className={cn("relative w-full max-w-4xl mx-auto p-6", className)}>
      <div className="relative flex items-end gap-3 bg-secondary/50 p-3 rounded-2xl border border-border shadow-sm focus-within:ring-1 focus-within:ring-ring transition-all">
        <Button variant="ghost" size="icon" className="h-12 w-12 rounded-full text-muted-foreground hover:text-foreground shrink-0 mb-1">
          <Paperclip className="h-6 w-6" />
        </Button>
        
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything..."
          className="min-h-[52px] max-h-[240px] w-full resize-none border-0 bg-transparent py-4 px-3 focus-visible:ring-0 shadow-none text-lg"
          rows={1}
        />

        <div className="flex gap-2 shrink-0 mb-1">
           {input.length === 0 ? (
             <Button variant="ghost" size="icon" className="h-12 w-12 rounded-full text-muted-foreground hover:text-foreground">
               <Mic className="h-6 w-6" />
             </Button>
           ) : (
             <Button 
                onClick={() => sendMessage(input)} 
                disabled={isStreaming || !input.trim()}
                size="icon"
                className="h-12 w-12 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 transition-all"
              >
                <Send className="h-5 w-5" />
             </Button>
           )}
        </div>
      </div>
      <div className="text-center text-sm text-muted-foreground mt-3">
        AI can make mistakes. Check important info.
      </div>
    </div>
  );
}
