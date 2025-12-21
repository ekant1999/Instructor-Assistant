import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Paper, Document } from '@/shared/types';
import { BookOpen, FileText, Search, X, Save, FolderOpen, Trash2, Loader2, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { ContextTemplate } from '@/shared/types';
import { toast } from 'sonner';

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
  onIngestionComplete?: () => void;
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
  onDeleteTemplate,
  onIngestionComplete
}: DocumentIngestionPanelProps) {
  const [paperSearch, setPaperSearch] = useState('');
  const [noteSearch, setNoteSearch] = useState('');
  const [noteTypeFilter, setNoteTypeFilter] = useState<string>('all');
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [templateName, setTemplateName] = useState('');
  
  // PDF Ingestion state
  const [indexDirectory, setIndexDirectory] = useState('index');
  const [chunkSize, setChunkSize] = useState('1200');
  const [chunkOverlap, setChunkOverlap] = useState('200');
  const [isIngesting, setIsIngesting] = useState(false);
  const [indexStatus, setIndexStatus] = useState<'ready' | 'not_ready' | 'checking'>('checking');
  const [indexPath, setIndexPath] = useState('');

  // Check index status on mount
  useEffect(() => {
    checkIndexStatus();
  }, []);

  const checkIndexStatus = async () => {
    setIndexStatus('checking');
    try {
      // In a real app, this would call an API endpoint
      // const response = await fetch('/api/rag/index-status');
      // const data = await response.json();
      
      // Mock for now - in real app, get from API
      const mockPath = '/Documents/PersonalWork/chatgpt-instructor-assistant/index';
      setIndexPath(mockPath);
      setIndexStatus('ready');
    } catch (error) {
      setIndexStatus('not_ready');
      toast.error('Failed to check index status');
    }
  };

  const handleStartIngestion = async () => {
    if (selectedPaperIds.size === 0) {
      toast.error('Please select at least one PDF to ingest');
      return;
    }

    setIsIngesting(true);
    try {
      // In a real app, this would call an API endpoint with selected paper IDs
      // const response = await fetch('/api/rag/ingest', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({
      //     paperIds: Array.from(selectedPaperIds),
      //     indexDirectory,
      //     chunkSize: parseInt(chunkSize),
      //     chunkOverlap: parseInt(chunkOverlap)
      //   })
      // });

      // Simulate ingestion process
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      toast.success(`Successfully ingested ${selectedPaperIds.size} PDF(s)`);
      setIndexStatus('ready');
      onIngestionComplete?.();
    } catch (error) {
      toast.error('Failed to ingest PDFs');
    } finally {
      setIsIngesting(false);
    }
  };

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
    <Card className="p-3 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-xs flex items-center gap-1.5">
          <BookOpen className="h-3.5 w-3.5" />
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
                    <p className="text-xs font-medium truncate">{paper.title}</p>
                    <p className="text-[10px] text-muted-foreground">
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
                      <p className="text-xs font-medium truncate">{note.title}</p>
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

      {/* PDF Ingestion Section */}
      <div className="pt-3 border-t space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-xs flex items-center gap-1.5">
            <FileText className="h-3.5 w-3.5" />
            PDF Ingestion
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={checkIndexStatus}
            className="h-7 text-xs"
            disabled={indexStatus === 'checking'}
          >
            <RefreshCw className={`h-3 w-3 ${indexStatus === 'checking' ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Index Status */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <Label className="text-xs font-medium">Index Status:</Label>
            {indexStatus === 'checking' && (
              <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
            )}
            {indexStatus === 'ready' && (
              <div className="flex items-center gap-1 text-green-600">
                <CheckCircle2 className="h-3 w-3" />
                <span className="text-xs">Index is ready</span>
              </div>
            )}
            {indexStatus === 'not_ready' && (
              <div className="flex items-center gap-1 text-yellow-600">
                <AlertCircle className="h-3 w-3" />
                <span className="text-xs">Index not found</span>
              </div>
            )}
          </div>
          {indexPath && (
            <p className="text-[10px] text-muted-foreground font-mono break-all">
              ({indexPath})
            </p>
          )}
        </div>

        {/* Ingestion Info */}
        {selectedPaperIds.size > 0 && (
          <div className="text-xs text-muted-foreground bg-muted/30 p-1.5 rounded">
            {selectedPaperIds.size} PDF{selectedPaperIds.size > 1 ? 's' : ''} selected for ingestion
          </div>
        )}

        {/* PDF Ingestion Form */}
        <div className="space-y-2">
          <div>
            <Label htmlFor="index-dir" className="text-xs font-medium mb-1 block">
              Index Directory
            </Label>
            <Input
              id="index-dir"
              value={indexDirectory}
              onChange={(e) => setIndexDirectory(e.target.value)}
              placeholder="index"
              className="text-sm h-8"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label htmlFor="chunk-size" className="text-xs font-medium mb-1 block">
                Chunk Size
              </Label>
              <Input
                id="chunk-size"
                type="number"
                value={chunkSize}
                onChange={(e) => setChunkSize(e.target.value)}
                placeholder="1200"
                className="text-sm h-8"
              />
            </div>

            <div>
              <Label htmlFor="chunk-overlap" className="text-xs font-medium mb-1 block">
                Chunk Overlap
              </Label>
              <Input
                id="chunk-overlap"
                type="number"
                value={chunkOverlap}
                onChange={(e) => setChunkOverlap(e.target.value)}
                placeholder="200"
                className="text-sm h-8"
              />
            </div>
          </div>

          <p className="text-[10px] text-muted-foreground">
            Extract text from selected PDFs, split into chunks, create embeddings, and build a FAISS index.
          </p>

          <Button
            onClick={handleStartIngestion}
            disabled={isIngesting || selectedPaperIds.size === 0}
            className="w-full"
            size="default"
          >
            {isIngesting ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
                Ingesting {selectedPaperIds.size} PDF{selectedPaperIds.size > 1 ? 's' : ''}...
              </>
            ) : (
              <>
                <FileText className="h-3.5 w-3.5 mr-2" />
                Start Ingestion
              </>
            )}
          </Button>
        </div>
      </div>

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

