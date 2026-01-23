import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useLocation } from 'wouter';
import { Paperclip, Send, X } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { useChatStore } from './store';
import { uploadQuestionContext } from '@/lib/api';
import { toast } from 'sonner';

export function MiniChatWidget({ onClose }: { onClose?: () => void }) {
  const {
    messages,
    status,
    input,
    setInput,
    sendMessage,
    isStreaming,
    attachments,
    addAttachments,
    removeAttachment
  } = useChatStore();
  const [, setLocation] = useLocation();
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const visibleMessages = messages;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [visibleMessages, status]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

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
      const uploaded = [];
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

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (canSend) handleSend();
    }
  };

  return (
    <Card className="w-[320px] sm:w-[360px] p-3 shadow-xl border-primary/20 bg-background/95 backdrop-blur flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div className="font-semibold text-sm">Assistant Chat</div>
        {onClose && (
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <ScrollArea className="h-60 pr-2">
        <div className="space-y-3">
          {visibleMessages.map((message) => {
            const isUser = message.role === 'user';
            return (
              <div key={message.id} className={cn("flex flex-col gap-2", isUser ? "items-end" : "items-start")}>
                <div
                  className={cn(
                    "max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed",
                    isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
                  )}
                >
                  <div className="prose prose-sm dark:prose-invert max-w-none text-xs">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                </div>

                {!isUser && message.actions && message.actions.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {message.actions.map((action, idx) => (
                      <Button
                        key={`${message.id}-action-${idx}`}
                        size="sm"
                        variant="outline"
                        className="h-7 text-xs"
                        onClick={() => {
                          if (action.type === 'link') setLocation(action.payload);
                        }}
                      >
                        {action.label}
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          {status && (
            <div className="text-xs text-muted-foreground">{status}</div>
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="flex items-center gap-2 rounded-full border border-border bg-background px-2 py-1 text-[10px]"
              title={attachment.preview}
            >
              <span className="max-w-[160px] truncate">{attachment.filename}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-4 w-4 rounded-full text-muted-foreground hover:text-foreground"
                onClick={() => removeAttachment(attachment.id)}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2 rounded-xl border border-border bg-secondary/50 p-2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.ppt,.pptx"
          multiple
          className="hidden"
          onChange={handleFileChange}
        />
        <Button
          variant="ghost"
          size="icon"
          onClick={handleAttachClick}
          disabled={isStreaming || isUploading}
          className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground"
        >
          <Paperclip className="h-4 w-4" />
        </Button>
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isUploading ? "Uploading…" : "Ask anything..."}
          className="min-h-[36px] max-h-[120px] w-full resize-none border-0 bg-transparent px-2 py-1 text-sm focus-visible:ring-0"
          rows={1}
        />
        <Button
          onClick={handleSend}
          disabled={!canSend}
          size="icon"
          className="h-8 w-8 shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </Card>
  );
}
