import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Message } from '@/shared/types';
import { cn } from '@/lib/utils';
import { Bot, User, Copy, Bookmark, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useLocation } from 'wouter';

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  const [, setLocation] = useLocation();

  return (
    <div className={cn(
      "group w-full py-8 px-4 border-b border-transparent hover:bg-muted/30 transition-colors",
      isUser ? "bg-transparent" : "bg-transparent"
    )}>
      <div className="max-w-3xl mx-auto flex gap-6">
        <div className={cn(
          "h-8 w-8 rounded-sm flex items-center justify-center shrink-0 shadow-sm",
          isUser ? "bg-secondary text-secondary-foreground" : "bg-primary text-primary-foreground"
        )}>
          {isUser ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
        </div>
        
        <div className="flex-1 space-y-4 overflow-hidden">
          <div className="prose prose-neutral dark:prose-invert max-w-none text-base leading-relaxed break-words">
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {message.isLoading && (
              <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse" />
            )}
          </div>

          {/* Message Actions */}
          {!isUser && !message.isLoading && (
            <div className="flex items-center gap-2 pt-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" title="Copy">
                <Copy className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" title="Save to Notes">
                <Bookmark className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" title="Regenerate">
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          )}

          {/* Interactive Actions / Suggestions */}
          {message.actions && (
            <div className="flex flex-wrap gap-2 mt-4">
              {message.actions.map((action, idx) => (
                <Button 
                  key={idx} 
                  variant="outline" 
                  size="sm"
                  onClick={() => {
                    if (action.type === 'link') setLocation(action.payload);
                  }}
                  className="bg-background hover:bg-secondary/50"
                >
                  {action.label}
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
