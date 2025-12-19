import React, { useRef, useEffect } from 'react';
import { Textarea } from '@/components/ui/textarea';

export function NotesEditor({ content, onChange }: { content: string, onChange: (val: string) => void }) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="flex-1 relative">
        <Textarea 
          ref={textareaRef}
          value={content}
          onChange={(e) => onChange(e.target.value)}
          className="absolute inset-0 w-full h-full resize-none border-0 p-8 text-lg font-mono leading-relaxed focus-visible:ring-0 bg-transparent"
          placeholder="# Start typing your note..."
        />
      </div>
      <div className="h-8 border-t bg-muted/20 flex items-center justify-between px-4 text-xs text-muted-foreground">
         <span>Markdown Supported</span>
         <span>{content.length} characters</span>
      </div>
    </div>
  );
}
