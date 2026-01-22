import React, { useState } from 'react';
import { Bot, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { MiniChatWidget } from '@/chat/MiniChatWidget';

export default function QwenAgent() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {isOpen && (
        <div className="animate-in slide-in-from-bottom-5 fade-in">
          <MiniChatWidget onClose={() => setIsOpen(false)} />
        </div>
      )}

      <Button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "h-12 w-12 rounded-full shadow-lg transition-all duration-300",
          isOpen ? "bg-secondary text-secondary-foreground" : "bg-primary text-primary-foreground hover:scale-105"
        )}
      >
        {isOpen ? <ChevronDown className="h-6 w-6" /> : <Bot className="h-6 w-6" />}
      </Button>
    </div>
  );
}
