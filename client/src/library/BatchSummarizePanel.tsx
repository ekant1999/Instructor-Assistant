import React from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Loader2, Sparkles, ChevronDown } from 'lucide-react';
import { Summary } from '@/shared/types';

interface BatchSummarizePanelProps {
  selectedCount: number;
  onSummarize: (agent: 'Gemini' | 'GPT' | 'Qwen') => void;
  isLoading: boolean;
  currentPaper?: string;
  progress?: number;
  total?: number;
}

export function BatchSummarizePanel({
  selectedCount,
  onSummarize,
  isLoading,
  currentPaper,
  progress,
  total
}: BatchSummarizePanelProps) {
  if (selectedCount === 0) {
    return (
      <Card className="p-4 bg-muted/50 border-dashed">
        <p className="text-sm text-muted-foreground text-center">
          Select papers to enable batch summarization
        </p>
      </Card>
    );
  }

  return (
    <Card className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm">Batch Summarization</h3>
          <p className="text-xs text-muted-foreground mt-1">
            {selectedCount} {selectedCount === 1 ? 'paper' : 'papers'} selected
          </p>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Processing...</span>
            {progress !== undefined && total !== undefined && (
              <span className="text-muted-foreground">
                {progress} of {total}
              </span>
            )}
          </div>
          {currentPaper && (
            <div className="text-xs text-muted-foreground italic">
              Currently processing: {currentPaper}
            </div>
          )}
          <div className="w-full bg-secondary rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{
                width: progress && total ? `${(progress / total) * 100}%` : '0%'
              }}
            />
          </div>
        </div>
      )}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            className="w-full"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                Summarize Selected
                <ChevronDown className="h-4 w-4 ml-2" />
              </>
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem onClick={() => onSummarize('Gemini')}>
            <span className="mr-2">✨</span>
            Gemini
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onSummarize('GPT')}>
            <span className="mr-2">🔗</span>
            ChatGPT Web
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onSummarize('Qwen')}>
            <span className="mr-2">🏠</span>
            Qwen Local
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </Card>
  );
}

