import React from 'react';
import { Summary } from '@/shared/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Clock, Edit, Trash2, FileText, Eye } from 'lucide-react';
import { format } from 'date-fns';

interface SummaryHistoryProps {
  summaries: Summary[];
  onSelect: (summary: Summary) => void;
  onEdit: (summary: Summary) => void;
  onDelete: (summaryId: string) => void;
  onCompare?: (summaryIds: string[]) => void;
  selectedSummaryId?: string;
}

export function SummaryHistory({
  summaries,
  onSelect,
  onEdit,
  onDelete,
  selectedSummaryId
}: SummaryHistoryProps) {
  if (summaries.length === 0) {
    return (
      <Card className="p-6 border-dashed">
        <div className="text-center text-muted-foreground">
          <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No summaries yet</p>
        </div>
      </Card>
    );
  }

  const getAgentBadgeColor = (agent: string) => {
    switch (agent) {
      case 'Gemini': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'GPT': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'Qwen': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getStyleBadgeColor = (style?: string) => {
    switch (style) {
      case 'brief': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'detailed': return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200';
      case 'teaching': return 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm">Summary History</h3>
        <span className="text-xs text-muted-foreground">
          {summaries.length} {summaries.length === 1 ? 'summary' : 'summaries'}
        </span>
      </div>

      <div className="space-y-2 max-h-[400px] overflow-auto">
        {summaries.map((summary, index) => (
          <Card
            key={summary.id}
            className={`p-3 cursor-pointer transition-all hover:shadow-md ${
              selectedSummaryId === summary.id ? 'border-primary ring-1 ring-primary' : ''
            }`}
            onClick={() => onSelect(summary)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    Summary {index + 1}
                  </span>
                  <Badge className={`text-[10px] px-1.5 py-0 ${getAgentBadgeColor(summary.agent)}`}>
                    {summary.agent}
                  </Badge>
                  {summary.style && (
                    <Badge className={`text-[10px] px-1.5 py-0 ${getStyleBadgeColor(summary.style)}`}>
                      {summary.style}
                    </Badge>
                  )}
                  {summary.isEdited && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                      Edited
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                  {summary.content.substring(0, 100)}...
                </p>
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {format(new Date(summary.createdAt), 'MMM d, yyyy')}
                  </span>
                  {summary.wordCount && (
                    <span>{summary.wordCount} words</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit(summary);
                  }}
                >
                  <Edit className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-destructive hover:text-destructive"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(summary.id);
                  }}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

