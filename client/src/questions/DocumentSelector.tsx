import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Paper, Document } from '@/shared/types';
import { BookOpen, FileText, Search, X } from 'lucide-react';

interface DocumentSelectorProps {
  papers: Paper[];
  notes: Document[];
  selectedPaperIds: Set<string>;
  selectedNoteIds: Set<string>;
  onPaperToggle: (id: string) => void;
  onNoteToggle: (id: string) => void;
  onClearSelection: () => void;
}

export function DocumentSelector({
  papers,
  notes,
  selectedPaperIds,
  selectedNoteIds,
  onPaperToggle,
  onNoteToggle,
  onClearSelection
}: DocumentSelectorProps) {
  const [paperSearch, setPaperSearch] = useState('');
  const [noteSearch, setNoteSearch] = useState('');
  const [noteTypeFilter, setNoteTypeFilter] = useState<string>('all');

  const filteredPapers = papers.filter(p =>
    p.title.toLowerCase().includes(paperSearch.toLowerCase()) ||
    p.authors?.toLowerCase().includes(paperSearch.toLowerCase())
  );

  const filteredNotes = notes.filter(n => {
    const matchesSearch = !noteSearch ||
      n.title.toLowerCase().includes(noteSearch.toLowerCase()) ||
      n.content.toLowerCase().includes(noteSearch.toLowerCase());
    
    const matchesType = noteTypeFilter === 'all' || n.type === noteTypeFilter;
    
    return matchesSearch && matchesType;
  });

  const totalSelected = selectedPaperIds.size + selectedNoteIds.size;

  return (
    <Card className="p-5 space-y-4 overflow-hidden">
      <div className="flex items-center justify-between gap-3 shrink-0">
        <h3 className="font-semibold text-sm flex items-center gap-2 flex-1 min-w-0">
          <BookOpen className="h-4 w-4 shrink-0" />
          <span className="whitespace-nowrap">Source Documents</span>
        </h3>
        {totalSelected > 0 && (
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {totalSelected} selected
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearSelection}
              className="h-7 text-xs px-2 shrink-0"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>

      <Tabs defaultValue="papers" className="w-full">
        <TabsList className="grid w-full grid-cols-2 h-auto">
          <TabsTrigger value="papers" className="text-xs py-2">
            Papers ({papers.length})
          </TabsTrigger>
          <TabsTrigger value="notes" className="text-xs py-2">
            Notes ({notes.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="papers" className="space-y-3 mt-4">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search papers..."
              value={paperSearch}
              onChange={(e) => setPaperSearch(e.target.value)}
              className="pl-8 h-8 text-xs"
            />
          </div>

          <div className="space-y-2 max-h-[250px] overflow-y-auto pr-2">
            {filteredPapers.map(paper => (
              <div
                key={paper.id}
                className={`p-2 sm:p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedPaperIds.has(paper.id)
                    ? 'bg-primary/10 border-primary'
                    : 'hover:bg-muted/50'
                }`}
                onClick={() => onPaperToggle(paper.id)}
              >
                <div className="flex items-start gap-2">
                  <Checkbox
                    checked={selectedPaperIds.has(paper.id)}
                    onCheckedChange={() => onPaperToggle(paper.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{paper.title}</p>
                    <p className="text-xs text-muted-foreground line-clamp-1">
                      {paper.source} • {paper.year}
                      {paper.authors && ` • ${paper.authors.split(',')[0]}`}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {filteredPapers.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">
                No papers found
              </p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="notes" className="space-y-3 mt-4">
          <div className="space-y-2">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search notes..."
                value={noteSearch}
                onChange={(e) => setNoteSearch(e.target.value)}
                className="pl-8 h-8 text-xs"
              />
            </div>

            <select
              value={noteTypeFilter}
              onChange={(e) => setNoteTypeFilter(e.target.value)}
              className="w-full h-8 text-xs border rounded-md px-2 bg-background"
            >
              <option value="all">All Types</option>
              <option value="summary">Summaries</option>
              <option value="qa_set">Q&A Sets</option>
              <option value="rag_response">RAG Responses</option>
              <option value="manual">Manual Notes</option>
            </select>
          </div>

          <div className="space-y-2 max-h-[250px] overflow-y-auto pr-2">
            {filteredNotes.map(note => (
              <div
                key={note.id}
                className={`p-2 sm:p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedNoteIds.has(note.id)
                    ? 'bg-primary/10 border-primary'
                    : 'hover:bg-muted/50'
                }`}
                onClick={() => onNoteToggle(note.id)}
              >
                <div className="flex items-start gap-2">
                  <Checkbox
                    checked={selectedNoteIds.has(note.id)}
                    onCheckedChange={() => onNoteToggle(note.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-1 sm:gap-2 mb-1">
                      <p className="text-sm font-medium truncate flex-1 min-w-0">{note.title}</p>
                      <Badge className="text-[10px] px-1.5 py-0 shrink-0">
                        {note.type.replace('_', ' ')}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {note.content.substring(0, 60)}...
                    </p>
                    {note.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {note.tags.slice(0, 2).map(tag => (
                          <span
                            key={tag}
                            className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {filteredNotes.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">
                No notes found
              </p>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </Card>
  );
}

