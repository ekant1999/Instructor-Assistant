import React from 'react';
import { RagQuery } from '@/shared/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Clock, Star, Trash2, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';

interface QueryHistoryProps {
  queries: RagQuery[];
  onSelect: (query: RagQuery) => void;
  onDelete: (id: string) => void;
  starredIds?: Set<string>;
  onToggleStar?: (id: string) => void;
}

export function QueryHistory({
  queries,
  onSelect,
  onDelete,
  starredIds = new Set(),
  onToggleStar
}: QueryHistoryProps) {
  if (queries.length === 0) {
    return (
      <Card className="p-4 border-dashed">
        <div className="text-center text-muted-foreground">
          <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No query history</p>
        </div>
      </Card>
    );
  }

  const getAgentBadgeColor = (agent: string) => {
    switch (agent) {
      case 'GPT Web': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'Gemini Web': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'Qwen Local': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm">Recent Queries</h3>
        <span className="text-xs text-muted-foreground">
          {queries.length} {queries.length === 1 ? 'query' : 'queries'}
        </span>
      </div>

      <ScrollArea className="max-h-[400px]">
        <div className="space-y-2">
          {queries.map((query) => (
            <Card
              key={query.id}
              className="p-3 cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => onSelect(query)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={`text-[10px] px-1.5 py-0 ${getAgentBadgeColor(query.agent)}`}>
                      {query.agent}
                    </Badge>
                    {starredIds.has(query.id) && (
                      <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                    )}
                  </div>
                  <p className="text-sm font-medium line-clamp-2 mb-1">
                    {query.query}
                  </p>
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {query.response.substring(0, 80)}...
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {format(new Date(query.createdAt), 'MMM d, HH:mm')}
                    </span>
                    {query.selectedDocumentIds && (
                      <span>{query.selectedDocumentIds.length} docs</span>
                    )}
                    {query.citations && (
                      <span>{query.citations.length} citations</span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  {onToggleStar && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleStar(query.id);
                      }}
                    >
                      <Star
                        className={`h-3 w-3 ${
                          starredIds.has(query.id)
                            ? 'fill-yellow-400 text-yellow-400'
                            : ''
                        }`}
                      />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelect(query);
                    }}
                    title="Reload query"
                  >
                    <RefreshCw className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-destructive hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(query.id);
                    }}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
}

