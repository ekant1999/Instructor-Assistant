import React, { useRef, useEffect, useState } from 'react';
import { Send, Paperclip, Mic, X } from 'lucide-react';
import { ChatAttachment, useChatStore } from './store';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { uploadQuestionContext } from '@/lib/api';
import { toast } from 'sonner';

export function ChatInput({ className }: { className?: string }) {
  const { input, setInput, sendMessage, isStreaming, attachments, addAttachments, removeAttachment } = useChatStore();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const isSupportedUpload = (file: File) => {
    const name = file.name.toLowerCase();
    return name.endsWith('.pdf') || name.endsWith('.ppt') || name.endsWith('.pptx');
  };

  const handleAttachClick = () => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  };

  const handleUploadFiles = async (files: FileList | File[]) => {
    const list = Array.from(files || []);
    if (list.length === 0) return;
    setIsUploading(true);
    try {
      const uploaded: ChatAttachment[] = [];
      for (const file of list) {
        if (!isSupportedUpload(file)) {
          toast.error(`Unsupported file type: ${file.name}`);
          continue;
        }
        try {
          const context = await uploadQuestionContext(file);
          uploaded.push({
            id: context.context_id,
            filename: context.filename,
            characters: context.characters,
            preview: context.preview
          });
        } catch (error) {
          toast.error(error instanceof Error ? error.message : `Failed to upload ${file.name}`);
        }
      }
      if (uploaded.length) {
        addAttachments(uploaded);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      handleUploadFiles(files);
    }
    event.target.value = '';
  };

  const canSend = !!(input.trim() || attachments.length > 0) && !isStreaming && !isUploading;

  const handleSend = () => {
    if (!canSend) return;
    sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canSend) handleSend();
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
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.ppt,.pptx"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />
      {attachments.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1 text-xs text-foreground"
              title={attachment.preview}
            >
              <span className="max-w-[220px] truncate">{attachment.filename}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5 rounded-full text-muted-foreground hover:text-foreground"
                onClick={() => removeAttachment(attachment.id)}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
      {isUploading && (
        <div className="mb-2 text-xs text-muted-foreground">Uploading attachments...</div>
      )}
      <div className="relative flex items-end gap-3 bg-secondary/50 p-3 rounded-2xl border border-border shadow-sm focus-within:ring-1 focus-within:ring-ring transition-all">
        <Button
          variant="ghost"
          size="icon"
          onClick={handleAttachClick}
          disabled={isStreaming || isUploading}
          className="h-12 w-12 rounded-full text-muted-foreground hover:text-foreground shrink-0 mb-1"
        >
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
           {input.length === 0 && attachments.length === 0 ? (
             <Button variant="ghost" size="icon" className="h-12 w-12 rounded-full text-muted-foreground hover:text-foreground">
               <Mic className="h-6 w-6" />
             </Button>
           ) : (
             <Button 
                onClick={handleSend}
                disabled={!canSend}
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
