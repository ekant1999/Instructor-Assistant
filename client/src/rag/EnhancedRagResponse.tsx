import React, { useState } from 'react';
import { RagQuery } from '@/shared/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { BookOpen, ExternalLink, Copy, CheckCircle2, MessageSquare, Save, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { format } from 'date-fns';

interface EnhancedRagResponseProps {
  query: RagQuery | null;
  onCopy?: () => void;
  onSaveToNotes?: () => void;
  onSendToChat?: () => void;
}

export function EnhancedRagResponse({
  query,
  onCopy,
  onSaveToNotes,
  onSendToChat
}: EnhancedRagResponseProps) {
  const [copied, setCopied] = useState(false);

  if (!query) {
    return (
      <Card className="p-8 border-dashed">
        <div className="text-center text-muted-foreground">
          <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Enter a query to get started</p>
        </div>
      </Card>
    );
  }

  const handleCopy = () => {
    if (onCopy) {
      onCopy();
    } else {
      navigator.clipboard.writeText(query.response);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getAgentBadgeColor = (agent: string) => {
    switch (agent) {
      case 'GPT Web': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'Gemini Web': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'Qwen Local': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Answer Card */}
      <Card className="p-6 border-primary/20 bg-primary/5 shadow-sm">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-primary" />
            <h3 className="font-semibold text-primary">Synthesized Answer</h3>
            <Badge className={`text-[10px] px-1.5 py-0 ${getAgentBadgeColor(query.agent)}`}>
              {query.agent}
            </Badge>
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-8 text-xs"
            >
              {copied ? (
                <>
                  <CheckCircle2 className="h-3 w-3 mr-2 text-green-500" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3 mr-2" />
                  Copy
                </>
              )}
            </Button>
          </div>
        </div>

        <ScrollArea className="max-h-[400px]">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{query.response}</ReactMarkdown>
          </div>
        </ScrollArea>

        <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={onSendToChat}
            className="h-8 text-xs"
          >
            <MessageSquare className="h-3 w-3 mr-2" />
            Send to Chat
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onSaveToNotes}
            className="h-8 text-xs"
          >
            <Save className="h-3 w-3 mr-2" />
            Save as Note
          </Button>
        </div>
      </Card>

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4 text-xs text-muted-foreground">
        <div>
          <strong>Documents Queried:</strong> {query.selectedDocumentIds?.length || 0}
        </div>
        <div>
          <strong>Citations:</strong> {query.citations?.length || 0}
        </div>
        <div>
          <strong>Query Time:</strong> {format(new Date(query.createdAt), 'MMM d, yyyy HH:mm')}
        </div>
        <div>
          <strong>Agent:</strong> {query.agent}
        </div>
      </div>

      {/* Citations */}
      {query.citations && query.citations.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider">
            Sources
          </h3>
          <div className="grid gap-3">
            {query.citations.map((citation, idx) => (
              <Card
                key={idx}
                className="p-4 hover:bg-muted/50 transition-colors cursor-pointer group"
                onClick={() => {
                  // Navigate to source document
                  if (citation.documentId) {
                    window.location.href = `/library?paper=${citation.documentId}`;
                  }
                }}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm group-hover:text-primary transition-colors">
                      {citation.documentTitle}
                    </h4>
                    {citation.page && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Page {citation.page}
                      </p>
                    )}
                  </div>
                  <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                </div>
                <p className="text-xs mt-3 text-muted-foreground border-l-2 border-primary/30 pl-2 italic">
                  "{citation.excerpt}"
                </p>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

