import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Search, Network, Loader2, Globe, Monitor, Database } from 'lucide-react';
import { DocumentIngestionPanel } from './DocumentIngestionPanel';
import { QueryHistory } from './QueryHistory';
import { EnhancedRagResponse } from './EnhancedRagResponse';
import { RagQuery, Paper, Document, ContextTemplate } from '@/shared/types';
import { toast } from 'sonner';

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
  
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set(['1']));
  const [selectedNoteIds, setSelectedNoteIds] = useState<Set<string>>(new Set());
  const [contextTemplates, setContextTemplates] = useState<ContextTemplate[]>([]);

  // Mock data
  const papers: Paper[] = [
    { id: '1', title: 'Attention Is All You Need', year: '2017', source: 'ArXiv', authors: 'Vaswani et al.' },
    { id: '2', title: 'BERT Paper', year: '2018', source: 'ArXiv' }
  ];

  const notes: Document[] = [
    {
      id: '1',
      type: 'summary',
      title: 'Summary: Transformers',
      content: 'Key points...',
      tags: ['transformer'],
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
  ];

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

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));

    const response = `Based on the selected documents, ${query} is addressed through several key mechanisms. The primary approach involves self-attention mechanisms that allow the model to weigh the importance of different parts of the input sequence.`;

    const newQuery: RagQuery = {
      id: Math.random().toString(),
      query,
      response,
      agent,
      selectedDocumentIds: [...Array.from(selectedPaperIds), ...Array.from(selectedNoteIds)],
      citations: [
        {
          documentId: '1',
          documentTitle: 'Attention Is All You Need',
          page: 3,
          excerpt: 'Self-attention mechanisms allow...'
        }
      ],
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
    setQueryHistory([newQuery, ...queryHistory]);
    setIsQuerying(false);
    toast.success('Query completed');
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

  const handleSaveToNotes = () => {
    if (!currentQuery) {
      toast.success('Response saved to Notes');
      // In real app, would save to Notes section
    }
  };

  const handleSendToChat = () => {
    if (currentQuery) {
      toast.success('Response sent to Chat');
      // In real app, would send to chat
    }
  };

  return (
    <div className="flex flex-col h-full max-w-7xl mx-auto w-full p-6 space-y-6">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-primary/10 mb-5">
          <Network className="h-8 w-8 text-primary" />
        </div>
        <h1 className="text-4xl font-bold tracking-tight mb-3">Knowledge Retrieval</h1>
        <p className="text-muted-foreground text-lg">Search across all your papers, notes, and external sources.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-hidden">
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
            contextTemplates={contextTemplates}
            onSaveTemplate={handleSaveTemplate}
            onLoadTemplate={handleLoadTemplate}
            onDeleteTemplate={handleDeleteTemplate}
            onIngestionComplete={() => {
              toast.success('PDFs ingested successfully');
              // Refresh papers list or update state after ingestion
            }}
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

        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6 overflow-auto">
          {/* Agent Selection */}
          <Card className="p-4">
            <div className="flex items-center gap-4">
              <Label className="text-base font-medium">Query Using:</Label>
              <div className="flex gap-2 flex-1">
                <Button
                  variant={agent === 'GPT Web' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setAgent('GPT Web')}
                  className="flex-1"
                >
                  <Globe className="h-4 w-4 mr-2" />
                  GPT Web
                </Button>
                <Button
                  variant={agent === 'Gemini Web' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setAgent('Gemini Web')}
                  className="flex-1"
                >
                  <Globe className="h-4 w-4 mr-2" />
                  Gemini Web
                </Button>
                <Button
                  variant={agent === 'Qwen Local' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setAgent('Qwen Local')}
                  className="flex-1"
                >
                  <Database className="h-4 w-4 mr-2" />
                  Qwen Local
                </Button>
              </div>
            </div>
          </Card>

          {/* Query Input */}
          <form onSubmit={handleQuery} className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
              <Input
                className="pl-10 h-11 text-lg shadow-sm"
                placeholder="Ask a question about your knowledge base..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            {/* Advanced Options */}
            <Card className="p-4 bg-muted/5">
              <div className="space-y-4">
                <p className="text-xs font-semibold uppercase text-muted-foreground">Advanced Options</p>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="citations"
                      checked={includeCitations}
                      onCheckedChange={(checked) => setIncludeCitations(checked as boolean)}
                    />
                    <Label htmlFor="citations" className="text-sm cursor-pointer">Include citations</Label>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="verbose"
                      checked={verboseMode}
                      onCheckedChange={(checked) => setVerboseMode(checked as boolean)}
                    />
                    <Label htmlFor="verbose" className="text-sm cursor-pointer">Verbose mode</Label>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="compare"
                      checked={compareSources}
                      onCheckedChange={(checked) => setCompareSources(checked as boolean)}
                    />
                    <Label htmlFor="compare" className="text-sm cursor-pointer">Compare across sources</Label>
                  </div>
                  
                  <div className="space-y-1">
                    <Label htmlFor="chunks" className="text-sm">Max chunks: {maxChunks}</Label>
                    <Input
                      id="chunks"
                      type="number"
                      min="1"
                      max="20"
                      value={maxChunks}
                      onChange={(e) => setMaxChunks(parseInt(e.target.value) || 5)}
                      className="h-8 text-sm"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-sm">Temperature: {temperature.toFixed(1)}</Label>
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

            <Button type="submit" size="lg" className="w-full" disabled={isQuerying}>
              {isQuerying ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Querying...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </>
              )}
            </Button>
          </form>

          {/* Response */}
          {currentQuery && (
            <EnhancedRagResponse
              query={currentQuery}
              onSaveToNotes={handleSaveToNotes}
              onSendToChat={handleSendToChat}
            />
          )}
        </div>
      </div>
    </div>
  );
}

