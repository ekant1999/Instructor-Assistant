import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Paper, Document } from '@/shared/types';
import { BookOpen, FileText, Search, X, Save, FolderOpen, Trash2 } from 'lucide-react';
import { ContextTemplate } from '@/shared/types';

interface DocumentIngestionPanelProps {
  papers: Paper[];
  notes: Document[];
  selectedPaperIds: Set<string>;
  selectedNoteIds: Set<string>;
  onPaperToggle: (id: string) => void;
  onNoteToggle: (id: string) => void;
  onSelectAll: (type: 'papers' | 'notes') => void;
  onClearSelection: () => void;
  contextTemplates?: ContextTemplate[];
  onSaveTemplate?: (name: string, paperIds: string[], noteIds: string[]) => void;
  onLoadTemplate?: (template: ContextTemplate) => void;
  onDeleteTemplate?: (id: string) => void;
}

export function DocumentIngestionPanel({
  papers,
  notes,
  selectedPaperIds,
  selectedNoteIds,
  onPaperToggle,
  onNoteToggle,
  onSelectAll,
  onClearSelection,
  contextTemplates = [],
  onSaveTemplate,
  onLoadTemplate,
  onDeleteTemplate
}: DocumentIngestionPanelProps) {
  const [paperSearch, setPaperSearch] = useState('');
  const [noteSearch, setNoteSearch] = useState('');
  const [noteTypeFilter, setNoteTypeFilter] = useState<string>('all');
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [templateName, setTemplateName] = useState('');

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
  const estimatedTokens = totalSelected * 1000; // Rough estimate

  const handleSaveTemplate = () => {
    if (!templateName.trim() || !onSaveTemplate) return;
    onSaveTemplate(
      templateName,
      Array.from(selectedPaperIds),
      Array.from(selectedNoteIds)
    );
    setTemplateName('');
    setShowTemplateDialog(false);
  };

  return (
    <Card className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <BookOpen className="h-4 w-4" />
          Document Selection
        </h3>
        <div className="flex items-center gap-2">
          {totalSelected > 0 && (
            <Badge variant="outline" className="text-xs">
              {totalSelected} selected
            </Badge>
          )}
          {totalSelected > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearSelection}
              className="h-7 text-xs"
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Context Templates */}
      {contextTemplates.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium">Context Templates</label>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowTemplateDialog(true)}
              className="h-7 text-xs"
            >
              <Save className="h-3 w-3 mr-1" />
              Save Current
            </Button>
          </div>
          <Select
            onValueChange={(id) => {
              const template = contextTemplates.find(t => t.id === id);
              if (template && onLoadTemplate) {
                onLoadTemplate(template);
              }
            }}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Load template..." />
            </SelectTrigger>
            <SelectContent>
              {contextTemplates.map(template => (
                <SelectItem key={template.id} value={template.id}>
                  <div className="flex items-center justify-between w-full">
                    <span>{template.name}</span>
                    {onDeleteTemplate && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-5 w-5"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteTemplate(template.id);
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Quick Actions */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onSelectAll('papers')}
          className="flex-1 h-7 text-xs"
        >
          All Papers
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onSelectAll('notes')}
          className="flex-1 h-7 text-xs"
        >
          All Notes
        </Button>
        {totalSelected === 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              onSelectAll('papers');
              onSelectAll('notes');
            }}
            className="flex-1 h-7 text-xs"
          >
            Select All
          </Button>
        )}
      </div>

      <Tabs defaultValue="papers" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="papers" className="text-xs">
            Papers ({papers.length})
          </TabsTrigger>
          <TabsTrigger value="notes" className="text-xs">
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

          <div className="space-y-2 max-h-[250px] overflow-auto">
            {filteredPapers.map(paper => (
              <div
                key={paper.id}
                className={`p-2 border rounded-lg cursor-pointer transition-colors ${
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
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{paper.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {paper.source} • {paper.year}
                    </p>
                  </div>
                </div>
              </div>
            ))}
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

          <div className="space-y-2 max-h-[250px] overflow-auto">
            {filteredNotes.map(note => (
              <div
                key={note.id}
                className={`p-2 border rounded-lg cursor-pointer transition-colors ${
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
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-medium truncate">{note.title}</p>
                      <Badge className="text-[10px] px-1.5 py-0">
                        {note.type.replace('_', ' ')}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {note.content.substring(0, 50)}...
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Token Estimate */}
      {totalSelected > 0 && (
        <div className="pt-2 border-t text-xs text-muted-foreground">
          <div className="flex justify-between">
            <span>Estimated tokens:</span>
            <span className={estimatedTokens > 10000 ? 'text-yellow-600' : ''}>
              ~{estimatedTokens.toLocaleString()}
            </span>
          </div>
          {estimatedTokens > 10000 && (
            <p className="text-yellow-600 mt-1">
              ⚠️ Selection may be too large. Consider reducing.
            </p>
          )}
        </div>
      )}

      {/* Save Template Dialog */}
      <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Save Context Template</DialogTitle>
            <DialogDescription>
              Save your current document selection as a reusable template
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Template Name</label>
              <Input
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="e.g., Transformer Papers Only"
              />
            </div>
            <div className="text-xs text-muted-foreground">
              Selected: {selectedPaperIds.size} papers, {selectedNoteIds.size} notes
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTemplateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveTemplate} disabled={!templateName.trim()}>
              Save Template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

