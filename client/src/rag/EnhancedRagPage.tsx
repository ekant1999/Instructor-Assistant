import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Network, Loader2, Globe, Database, Send, Bot, User, ChevronDown, ChevronUp, Settings } from 'lucide-react';
import { DocumentIngestionPanel } from './DocumentIngestionPanel';
import { QueryHistory } from './QueryHistory';
import { RagQuery, Paper, Document, ContextTemplate } from '@/shared/types';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';
import { createNote, listNotes, listPapers, ragQuery } from '@/lib/api';
import { mapApiNote, mapApiPaper } from '@/lib/mappers';

export default function EnhancedRagPage() {
  const [query, setQuery] = useState('');
  const [agent, setAgent] = useState<'GPT Web' | 'Gemini Web' | 'Qwen Local'>('Qwen Local');
  const [includeCitations, setIncludeCitations] = useState(true);
  const [verboseMode, setVerboseMode] = useState(false);
  const [compareSources, setCompareSources] = useState(false);
  const [maxChunks, setMaxChunks] = useState(5);
  const [temperature, setTemperature] = useState(0.7);
  const [isQuerying, setIsQuerying] = useState(false);
  const [currentQuery, setCurrentQuery] = useState<RagQuery | null>(null);
  const [queryHistory, setQueryHistory] = useState<RagQuery[]>([]);
  const [starredQueries, setStarredQueries] = useState<Set<string>>(new Set());
  const [showAdvanced, setShowAdvanced] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  
  const [papers, setPapers] = useState<Paper[]>([]);
  const [notes, setNotes] = useState<Document[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [indexDirectory, setIndexDirectory] = useState('index');
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set());
  const [selectedNoteIds, setSelectedNoteIds] = useState<Set<string>>(new Set());
  const [contextTemplates, setContextTemplates] = useState<ContextTemplate[]>([]);
  const [paperSearchQuery, setPaperSearchQuery] = useState<string>('');

  useEffect(() => {
    let isMounted = true;
    async function loadDocs() {
      setIsLoadingDocs(true);
      try {
        const [paperRows, noteRows] = await Promise.all([
          listPapers(paperSearchQuery || undefined, 'keyword'),
          listNotes()
        ]);
        if (!isMounted) return;
        setPapers(paperRows.map(mapApiPaper));
        setNotes(noteRows.map(mapApiNote));
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Failed to load documents');
      } finally {
        if (isMounted) setIsLoadingDocs(false);
      }
    }
    loadDocs();
    return () => {
      isMounted = false;
    };
  }, [paperSearchQuery]); // Re-fetch when search query changes

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      toast.error('Please enter a query');
      return;
    }

    if (selectedPaperIds.size === 0 && selectedNoteIds.size === 0) {
      toast.error('Please select at least one document');
      return;
    }

    setIsQuerying(true);

    try {
      const result = await ragQuery({
        question: query,
        index_dir: indexDirectory || undefined,
        k: maxChunks || undefined
      });

      const citations = includeCitations
        ? result.context.map((ctx, idx) => ({
            documentId: `${ctx.paper || 'source'}-${idx}`,
            documentTitle: ctx.paper || 'Unknown source',
            excerpt: ctx.source || ''
          }))
        : [];

      const newQuery: RagQuery = {
        id: Math.random().toString(),
        query,
        response: result.answer,
        agent,
        selectedDocumentIds: [...Array.from(selectedPaperIds), ...Array.from(selectedNoteIds)],
        citations,
        settings: {
          includeCitations,
          verboseMode,
          compareSources,
          maxChunks,
          temperature
        },
        createdAt: Date.now()
      };

      setCurrentQuery(newQuery);
      setQueryHistory((prev) => [newQuery, ...prev]);
      setQuery('');
      toast.success('Query completed');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Query failed');
    } finally {
      setIsQuerying(false);
    }
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [queryHistory, isQuerying]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (query.trim() && !isQuerying) {
        handleQuery(e as any);
      }
    }
  };

  const handleSelectPaper = (id: string) => {
    const newSet = new Set(selectedPaperIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedPaperIds(newSet);
  };

  const handleSelectNote = (id: string) => {
    const newSet = new Set(selectedNoteIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedNoteIds(newSet);
  };

  const handleSelectAll = (type: 'papers' | 'notes') => {
    if (type === 'papers') {
      setSelectedPaperIds(new Set(papers.map(p => p.id)));
    } else {
      setSelectedNoteIds(new Set(notes.map(n => n.id)));
    }
  };

  const handleClearSelection = () => {
    setSelectedPaperIds(new Set());
    setSelectedNoteIds(new Set());
  };

  const handleSaveTemplate = (name: string, paperIds: string[], noteIds: string[]) => {
    const template: ContextTemplate = {
      id: Math.random().toString(),
      name,
      selectedDocumentIds: [...paperIds, ...noteIds],
      createdAt: Date.now(),
      updatedAt: Date.now()
    };
    setContextTemplates([...contextTemplates, template]);
    toast.success('Template saved');
  };

  const handleLoadTemplate = (template: ContextTemplate) => {
    const paperIds = template.selectedDocumentIds.filter(id =>
      papers.some(p => p.id === id)
    );
    const noteIds = template.selectedDocumentIds.filter(id =>
      notes.some(n => n.id === id)
    );
    setSelectedPaperIds(new Set(paperIds));
    setSelectedNoteIds(new Set(noteIds));
    toast.success(`Loaded template: ${template.name}`);
  };

  const handleDeleteTemplate = (id: string) => {
    setContextTemplates(contextTemplates.filter(t => t.id !== id));
    toast.success('Template deleted');
  };

  const handleToggleStar = (id: string) => {
    const newSet = new Set(starredQueries);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setStarredQueries(newSet);
  };

  const handleSaveToNotes = async () => {
    if (!currentQuery) return;
    try {
      const title = `RAG: ${currentQuery.query.slice(0, 60)}`.trim();
      const sources = currentQuery.citations?.length
        ? `\n\nSources:\n${currentQuery.citations
            .map((c) => `- ${c.documentTitle}${c.excerpt ? ` (${c.excerpt})` : ''}`)
            .join('\n')}`
        : '';
      const body = `Question:\n${currentQuery.query}\n\nAnswer:\n${currentQuery.response}${sources}`;
      const rawPaperId =
        selectedPaperIds.size === 1 ? Number(Array.from(selectedPaperIds)[0]) : null;
      const paperId = rawPaperId !== null && Number.isFinite(rawPaperId) ? rawPaperId : null;
      const created = await createNote({
        title,
        body,
        paper_id: paperId,
        tags: ['rag_response']
      });
      setNotes((prev) => [mapApiNote(created), ...prev]);
      toast.success('Response saved to Notes');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to save response');
    }
  };

  const handleSendToChat = () => {
    if (currentQuery) {
      toast.success('Response sent to Chat');
      // In real app, would send to chat
    }
  };

  return (
    <div className="flex flex-col h-full max-w-7xl mx-auto w-full p-4 space-y-4 min-h-0 ia-page-root">
      <div className="text-center mb-4">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 mb-3">
          <Network className="h-6 w-6 text-primary" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight mb-2">Knowledge Retrieval</h1>
        <p className="text-muted-foreground text-sm">Search across all your papers, notes, and external sources.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1 overflow-hidden">
        {/* Left Sidebar - Document Selection & PDF Ingestion */}
        <div className="lg:col-span-1 space-y-4 overflow-auto">
          <DocumentIngestionPanel
            papers={papers}
            notes={notes}
            selectedPaperIds={selectedPaperIds}
            selectedNoteIds={selectedNoteIds}
            onPaperToggle={handleSelectPaper}
            onNoteToggle={handleSelectNote}
            onSelectAll={handleSelectAll}
            onClearSelection={handleClearSelection}
            onPaperSearchChange={setPaperSearchQuery}
            indexDirectory={indexDirectory}
            onIndexDirectoryChange={setIndexDirectory}
            contextTemplates={contextTemplates}
            onSaveTemplate={handleSaveTemplate}
            onLoadTemplate={handleLoadTemplate}
            onDeleteTemplate={handleDeleteTemplate}
          />

          {queryHistory.length > 0 && (
            <QueryHistory
              queries={queryHistory}
              onSelect={setCurrentQuery}
              onDelete={(id) => {
                setQueryHistory(queryHistory.filter(q => q.id !== id));
                if (currentQuery?.id === id) {
                  setCurrentQuery(null);
                }
              }}
              starredIds={starredQueries}
              onToggleStar={handleToggleStar}
            />
          )}
        </div>

        {/* Main Content - Chat Interface */}
        <div className="lg:col-span-2 flex flex-col h-full overflow-hidden">
          {/* Advanced Options - Collapsible Above Chat */}
          <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced} className="mb-2">
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full justify-between text-xs">
                <div className="flex items-center gap-2">
                  <Settings className="h-3.5 w-3.5" />
                  <span>Advanced Options</span>
                </div>
                {showAdvanced ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <Card className="p-3 bg-muted/5 mb-2">
                <div className="space-y-3">
                  {/* Agent Selection */}
                  <div>
                    <Label className="text-xs font-medium mb-2 block">Query Using:</Label>
                    <div className="flex gap-2">
                      <Button
                        variant={agent === 'GPT Web' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setAgent('GPT Web')}
                        className="flex-1 text-xs"
                      >
                        <Globe className="h-3 w-3 mr-1" />
                        GPT Web
                      </Button>
                      <Button
                        variant={agent === 'Gemini Web' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setAgent('Gemini Web')}
                        className="flex-1 text-xs"
                      >
                        <Globe className="h-3 w-3 mr-1" />
                        Gemini Web
                      </Button>
                      <Button
                        variant={agent === 'Qwen Local' ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setAgent('Qwen Local')}
                        className="flex-1 text-xs"
                      >
                        <Database className="h-3 w-3 mr-1" />
                        Qwen Local
                      </Button>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id="citations"
                        checked={includeCitations}
                        onCheckedChange={(checked) => setIncludeCitations(checked as boolean)}
                      />
                      <Label htmlFor="citations" className="text-xs cursor-pointer">Include citations</Label>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id="verbose"
                        checked={verboseMode}
                        onCheckedChange={(checked) => setVerboseMode(checked as boolean)}
                      />
                      <Label htmlFor="verbose" className="text-xs cursor-pointer">Verbose mode</Label>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Checkbox
                        id="compare"
                        checked={compareSources}
                        onCheckedChange={(checked) => setCompareSources(checked as boolean)}
                      />
                      <Label htmlFor="compare" className="text-xs cursor-pointer">Compare sources</Label>
                    </div>
                    
                    <div className="space-y-1">
                      <Label htmlFor="chunks" className="text-xs">Max chunks: {maxChunks}</Label>
                      <Input
                        id="chunks"
                        type="number"
                        min="1"
                        max="20"
                        value={maxChunks}
                        onChange={(e) => setMaxChunks(parseInt(e.target.value) || 5)}
                        className="h-7 text-xs"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs">Temperature: {temperature.toFixed(1)}</Label>
                    <Slider
                      value={[temperature]}
                      onValueChange={(values) => setTemperature(values[0])}
                      min={0}
                      max={1}
                      step={0.1}
                    />
                  </div>
                </div>
              </Card>
            </CollapsibleContent>
          </Collapsible>

          {/* Chat Messages Area */}
          <ScrollArea className="flex-1 mb-4">
            <div className="space-y-4 pr-4">
              {queryHistory.length === 0 && !isQuerying && (
                <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
                  <Network className="h-12 w-12 mb-4 opacity-50" />
                  <p className="text-sm">Ask a question about your knowledge base to get started</p>
                </div>
              )}

              {queryHistory.map((q) => (
                <div key={q.id} className="space-y-4">
                  {/* User Query */}
                  <div className="flex gap-3 max-w-4xl">
                    <div className="h-8 w-8 rounded-sm flex items-center justify-center shrink-0 bg-secondary text-secondary-foreground shadow-sm">
                      <User className="h-4 w-4" />
                    </div>
                    <div className="flex-1">
                      <div className="prose prose-sm dark:prose-invert max-w-none text-sm">
                        {q.query}
                      </div>
                    </div>
                  </div>

                  {/* Bot Response */}
                  <div className="flex gap-3 max-w-4xl">
                    <div className="h-8 w-8 rounded-sm flex items-center justify-center shrink-0 bg-primary text-primary-foreground shadow-sm">
                      <Bot className="h-4 w-4" />
                    </div>
                    <div className="flex-1 space-y-2">
                      <div className="prose prose-sm dark:prose-invert max-w-none text-sm">
                        <ReactMarkdown>{q.response}</ReactMarkdown>
                      </div>
                      {q.citations && q.citations.length > 0 && (
                        <div className="text-xs text-muted-foreground pt-2 border-t">
                          <strong>Sources:</strong> {q.citations.map((c, i) => (
                            <span key={i}>
                              {i > 0 && ', '}
                              {c.documentTitle}
                              {c.page && ` (p.${c.page})`}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Loading Indicator */}
              {isQuerying && (
                <div className="flex gap-3 max-w-4xl">
                  <div className="h-8 w-8 rounded-sm flex items-center justify-center shrink-0 bg-primary text-primary-foreground shadow-sm">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Searching knowledge base...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </ScrollArea>

          {/* Chat Input */}
          <form onSubmit={handleQuery} className="relative">
            <div className="relative flex items-end gap-2 bg-secondary/50 p-2 rounded-xl border border-border shadow-sm focus-within:ring-1 focus-within:ring-ring transition-all">
              <Textarea
                ref={textareaRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your knowledge base..."
                className="min-h-[44px] max-h-[150px] w-full resize-none border-0 bg-transparent py-2 px-3 focus-visible:ring-0 shadow-none text-sm"
                rows={1}
              />
              <Button
                type="submit"
                disabled={isQuerying || !query.trim()}
                size="icon"
                className="h-9 w-9 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 shrink-0 mb-1"
              >
                {isQuerying ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
