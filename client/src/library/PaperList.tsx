import React from 'react';
import { Paper } from '@/shared/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileText, Trash2, Eye, Sparkles } from 'lucide-react';

interface PaperListProps {
  papers: Paper[];
  onSelect: (paper: Paper) => void;
  onDelete: (id: string) => void;
  onSummarize: (id: string) => void;
  selectedId?: string;
}

export function PaperList({ papers, onSelect, onDelete, onSummarize, selectedId }: PaperListProps) {
  return (
    <div className="space-y-3 p-4">
      {papers.map((paper) => (
        <Card 
          key={paper.id}
          className={`p-4 cursor-pointer transition-all hover:shadow-md ${selectedId === paper.id ? 'border-primary ring-1 ring-primary' : 'hover:border-primary/50'}`}
          onClick={() => onSelect(paper)}
        >
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded bg-secondary flex items-center justify-center shrink-0">
              <FileText className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-sm truncate" title={paper.title}>{paper.title}</h3>
              <p className="text-xs text-muted-foreground mt-1">{paper.source} • {paper.year}</p>
            </div>
          </div>
          
          <div className="flex justify-end items-center gap-1 mt-3 pt-3 border-t border-border/50">
             <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={(e) => { e.stopPropagation(); onSelect(paper); }}>
               <Eye className="h-3 w-3 mr-1" /> Preview
             </Button>
             <Button variant="ghost" size="sm" className="h-7 text-xs text-blue-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950" onClick={(e) => { e.stopPropagation(); onSummarize(paper.id); }}>
               <Sparkles className="h-3 w-3 mr-1" /> Summarize
             </Button>
             <Button variant="ghost" size="sm" className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10" onClick={(e) => { e.stopPropagation(); onDelete(paper.id); }}>
               <Trash2 className="h-3 w-3" />
             </Button>
          </div>
        </Card>
      ))}
      
      {papers.length === 0 && (
        <div className="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-lg">
           No papers in library.
        </div>
      )}
    </div>
  );
}
