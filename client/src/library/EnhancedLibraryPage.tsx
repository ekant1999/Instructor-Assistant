import React, { useState } from 'react';
import { EnhancedPaperList } from './EnhancedPaperList';
import { PdfPreview } from './PdfPreview';
import { UploadPanel } from './UploadPanel';
import { SectionSelector } from './SectionSelector';
import { SummarizePanel, SummarizeConfig } from './SummarizePanel';
import { BatchSummarizePanel } from './BatchSummarizePanel';
import { EnhancedSummaryEditor } from './EnhancedSummaryEditor';
import { SummaryHistory } from './SummaryHistory';
import { SaveSummaryModal } from './SaveSummaryModal';
import { ExportSummaryDialog } from './ExportSummaryDialog';
import { Paper, Summary, Document } from '@/shared/types';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, Layers, Sparkles, BookOpen, History, Save } from 'lucide-react';
import { useChatStore } from '@/chat/store';
import { toast } from 'sonner';

export default function EnhancedLibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([
    {
      id: '1',
      title: 'Attention Is All You Need',
      source: 'ArXiv',
      year: '2017',
      authors: 'Vaswani et al.',
      abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...',
      sections: [
        { id: 'abstract', title: 'Abstract', content: 'The dominant sequence transduction models are based on complex recurrent...' },
        { id: 'intro', title: 'Introduction', content: 'Recurrent neural networks, long short-term memory...' },
        { id: 'methods', title: 'Methods', content: 'The overall architecture follows an encoder-decoder structure...' },
        { id: 'results', title: 'Results', content: 'We achieved state-of-the-art BLEU scores on the WMT 2014...' },
        { id: 'discussion', title: 'Discussion', content: 'The Transformer model demonstrates...' }
      ],
      createdAt: Date.now(),
      updatedAt: Date.now()
    },
    { 
      id: '2', 
      title: 'GPT-4 Technical Report', 
      source: 'OpenAI', 
      year: '2023',
      authors: 'OpenAI',
      createdAt: Date.now(),
      updatedAt: Date.now()
    },
    { 
      id: '3', 
      title: 'Constitutional AI: Harmlessness from AI Feedback', 
      source: 'Anthropic', 
      year: '2022',
      authors: 'Anthropic',
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
  ]);

  const [selectedId, setSelectedId] = useState<string | undefined>('1');
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set());
  const [selectedSections, setSelectedSections] = useState<Set<string>>(new Set());
  const [summaries, setSummaries] = useState<Map<string, Summary[]>>(new Map());
  const [currentSummary, setCurrentSummary] = useState<Summary | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ current?: string; progress?: number; total?: number }>({});
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [existingNotes, setExistingNotes] = useState<Document[]>([]);
  
  const sendMessage = useChatStore(state => state.sendMessage);
  const selectedPaper = papers.find(p => p.id === selectedId) || null;
  const paperSummaries = selectedPaper ? summaries.get(selectedPaper.id) || [] : [];

  const handleAddPapers = (uploads: any[]) => {
    const newPapers = uploads.map(u => ({
      id: Math.random().toString(),
      title: u.title,
      source: u.source === 'file' ? 'Upload' : 'Online',
      year: new Date().getFullYear().toString(),
      abstract: 'Newly uploaded paper',
      createdAt: Date.now(),
      updatedAt: Date.now()
    }));
    setPapers([...newPapers, ...papers]);
  };

  const handleSelectSection = (sectionId: string) => {
    const newSet = new Set(selectedSections);
    if (newSet.has(sectionId)) {
      newSet.delete(sectionId);
    } else {
      newSet.add(sectionId);
    }
    setSelectedSections(newSet);
  };

  const handleSelectAll = () => {
    if (selectedPaper?.sections) {
      if (selectedSections.size === selectedPaper.sections.length) {
        setSelectedSections(new Set());
      } else {
        setSelectedSections(new Set(selectedPaper.sections.map(s => s.id)));
      }
    }
  };

  const generateSummary = async (
    paperId: string,
    config: SummarizeConfig,
    agent: 'Gemini' | 'GPT' | 'Qwen' = 'Qwen'
  ): Promise<string> => {
    const paper = papers.find(p => p.id === paperId);
    if (!paper) return '';

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));

    let mockSummary = '';
    const style = config.style || 'bullet';
    
    if (style === 'bullet') {
      mockSummary = `## Summary: ${paper.title}\n\n- Key point 1\n- Key point 2\n- Key point 3`;
    } else if (style === 'detailed') {
      mockSummary = `## Detailed Summary: ${paper.title}\n\n### Background\n...\n\n### Key Innovation\n...\n\n### Results\n...`;
    } else {
      mockSummary = `## Teaching Summary: ${paper.title}\n\n### Core Concept\n...\n\n### Key Terms\n...\n\n### Exam Questions\n...`;
    }

    if (config.customPrompt) {
      mockSummary += `\n\n---\n\n### Custom Notes\n${config.customPrompt}`;
    }

    return mockSummary;
  };

  const handleSummarize = async (config: SummarizeConfig) => {
    if (!selectedPaper) return;
    
    setIsSummarizing(true);
    const agent = config.method === 'gemini' ? 'Gemini' : config.method === 'gpt' ? 'GPT' : 'Qwen';
    
    try {
      const content = await generateSummary(selectedPaper.id, config, agent);
      const wordCount = content.split(/\s+/).length;
      
      const newSummary: Summary = {
        id: Math.random().toString(),
        paperId: selectedPaper.id,
        title: `Summary: ${selectedPaper.title}`,
        content,
        agent,
        style: config.style,
        wordCount,
        isEdited: false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      };

      const existing = summaries.get(selectedPaper.id) || [];
      setSummaries(new Map(summaries.set(selectedPaper.id, [...existing, newSummary])));
      setCurrentSummary(newSummary);
      toast.success('Summary generated successfully');
    } catch (error) {
      toast.error('Failed to generate summary');
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleBatchSummarize = async (agent: 'Gemini' | 'GPT' | 'Qwen') => {
    if (selectedPaperIds.size === 0) return;
    
    setIsSummarizing(true);
    const selectedPapers = papers.filter(p => selectedPaperIds.has(p.id));
    setBatchProgress({ total: selectedPapers.length, progress: 0 });

    try {
      const combinedSummaries: Summary[] = [];
      
      for (let i = 0; i < selectedPapers.length; i++) {
        const paper = selectedPapers[i];
        setBatchProgress({ 
          total: selectedPapers.length, 
          progress: i + 1, 
          current: paper.title 
        });

        const content = await generateSummary(paper.id, {
          scope: 'multiple',
          method: agent === 'Gemini' ? 'gemini' : agent === 'GPT' ? 'gpt' : 'local',
          style: 'detailed'
        }, agent);

        const wordCount = content.split(/\s+/).length;
        const summary: Summary = {
          id: Math.random().toString(),
          paperId: paper.id,
          title: `Summary: ${paper.title}`,
          content: `## ${paper.title}\n\n${content}`,
          agent,
          style: 'detailed',
          wordCount,
          isEdited: false,
          createdAt: Date.now(),
          updatedAt: Date.now()
        };

        combinedSummaries.push(summary);
        
        // Update individual paper summaries
        const existing = summaries.get(paper.id) || [];
        setSummaries(new Map(summaries.set(paper.id, [...existing, summary])));
      }

      // Create combined summary
      const combinedContent = combinedSummaries
        .map(s => s.content)
        .join('\n\n---\n\n');
      
      const combinedSummary: Summary = {
        id: Math.random().toString(),
        title: `Combined Summary: ${selectedPapers.length} Papers`,
        content: combinedContent,
        agent,
        style: 'detailed',
        wordCount: combinedContent.split(/\s+/).length,
        isEdited: false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      };

      setCurrentSummary(combinedSummary);
      toast.success(`Generated ${selectedPapers.length} summaries`);
    } catch (error) {
      toast.error('Failed to generate batch summaries');
    } finally {
      setIsSummarizing(false);
      setBatchProgress({});
    }
  };

  const handleSaveSummary = (markdown: string) => {
    if (!currentSummary) return;
    
    const updated: Summary = {
      ...currentSummary,
      content: markdown,
      isEdited: true,
      updatedAt: Date.now()
    };
    
    if (updated.paperId) {
      const existing = summaries.get(updated.paperId) || [];
      const updatedList = existing.map(s => s.id === updated.id ? updated : s);
      setSummaries(new Map(summaries.set(updated.paperId, updatedList)));
    }
    
    setCurrentSummary(updated);
    toast.success('Summary saved');
  };

  const handleExport = (format: 'pdf' | 'txt' | 'latex' | 'markdown' | 'docx', content: string, metadata: any) => {
    // In a real app, this would call an API to generate the export
    const ext = format === 'markdown' ? 'md' : format;
    const filename = `${(selectedPaper?.title || 'Summary').replace(/[^a-z0-9]/gi, '_')}_Summary_${new Date().toISOString().split('T')[0]}.${ext}`;
    
    if (format === 'markdown' || format === 'txt') {
      const element = document.createElement('a');
      element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
      element.setAttribute('download', filename);
      element.style.display = 'none';
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } else {
      toast.info(`${format.toUpperCase()} export would be generated server-side`);
    }
  };

  const handleSaveToNotes = (action: 'new' | 'append', noteId?: string, title?: string, tags?: string[]) => {
    if (!currentSummary) return;
    
    if (action === 'append' && noteId) {
      toast.success('Summary appended to note');
    } else {
      toast.success('Summary saved as new note');
      // In real app, would create note in Notes section
    }
  };

  const handleSelectSummary = (summary: Summary) => {
    setCurrentSummary(summary);
  };

  const handleDeleteSummary = (summaryId: string) => {
    if (!selectedPaper) return;
    
    const existing = summaries.get(selectedPaper.id) || [];
    const filtered = existing.filter(s => s.id !== summaryId);
    setSummaries(new Map(summaries.set(selectedPaper.id, filtered)));
    
    if (currentSummary?.id === summaryId) {
      setCurrentSummary(null);
    }
    
    toast.success('Summary deleted');
  };

  return (
    <div className="flex h-full w-full flex-col bg-background">
      {/* Upload Panel */}
      <UploadPanel onUpload={handleAddPapers} />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - Papers List */}
        <div className="w-[320px] border-r bg-muted/5 flex flex-col h-full overflow-hidden">
          <EnhancedPaperList
            papers={papers}
            selectedId={selectedId}
            selectedIds={selectedPaperIds}
            onSelect={(p) => {
              setSelectedId(p.id);
              setSelectedSections(new Set());
              setCurrentSummary(null);
            }}
            onDelete={(id) => {
              setPapers(papers.filter(p => p.id !== id));
              if (selectedId === id) {
                setSelectedId(undefined);
              }
            }}
            onSummarize={(id) => {
              const p = papers.find(x => x.id === id);
              if (p) sendMessage(`Please summarize: "${p.title}"`);
            }}
            onSelectionChange={setSelectedPaperIds}
          />

          {/* Batch Summarize Panel */}
          {selectedPaperIds.size > 0 && (
            <div className="border-t p-4">
              <BatchSummarizePanel
                selectedCount={selectedPaperIds.size}
                onSummarize={handleBatchSummarize}
                isLoading={isSummarizing}
                currentPaper={batchProgress.current}
                progress={batchProgress.progress}
                total={batchProgress.total}
              />
            </div>
          )}
        </div>

        {/* Main Panel */}
        <div className="flex-1 h-full overflow-hidden">
          {selectedPaper ? (
            <Tabs defaultValue="preview" className="h-full flex flex-col">
              <TabsList className="w-full justify-start rounded-none border-b h-auto p-0 bg-transparent">
                <TabsTrigger value="preview">
                  <FileText className="h-4 w-4 mr-2" />
                  Preview
                </TabsTrigger>
                <TabsTrigger value="sections">
                  <Layers className="h-4 w-4 mr-2" />
                  Sections
                </TabsTrigger>
                <TabsTrigger value="summarize">
                  <Sparkles className="h-4 w-4 mr-2" />
                  Summarize
                </TabsTrigger>
                {paperSummaries.length > 0 && (
                  <TabsTrigger value="history">
                    <History className="h-4 w-4 mr-2" />
                    History ({paperSummaries.length})
                  </TabsTrigger>
                )}
                {currentSummary && (
                  <TabsTrigger value="output">
                    <BookOpen className="h-4 w-4 mr-2" />
                    Summary
                  </TabsTrigger>
                )}
              </TabsList>

              <TabsContent value="preview" className="flex-1 overflow-hidden">
                <PdfPreview paper={selectedPaper} />
              </TabsContent>

              <TabsContent value="sections" className="flex-1 overflow-hidden">
                <SectionSelector
                  paper={selectedPaper}
                  selectedSections={selectedSections}
                  onSelectSection={handleSelectSection}
                  onSelectAll={handleSelectAll}
                  onCopy={(text) => navigator.clipboard.writeText(text)}
                />
              </TabsContent>

              <TabsContent value="summarize" className="flex-1 overflow-hidden">
                <SummarizePanel
                  selectedSectionCount={selectedSections.size}
                  onSummarize={handleSummarize}
                  isLoading={isSummarizing}
                />
              </TabsContent>

              {paperSummaries.length > 0 && (
                <TabsContent value="history" className="flex-1 overflow-auto p-6">
                  <SummaryHistory
                    summaries={paperSummaries}
                    onSelect={handleSelectSummary}
                    onEdit={setCurrentSummary}
                    onDelete={handleDeleteSummary}
                    selectedSummaryId={currentSummary?.id}
                  />
                </TabsContent>
              )}

              {currentSummary && (
                <TabsContent value="output" className="flex-1 overflow-hidden">
                  <EnhancedSummaryEditor
                    summary={currentSummary}
                    onSave={handleSaveSummary}
                    onExport={(md) => {
                      setExportDialogOpen(true);
                    }}
                    onSaveToNotes={() => setSaveModalOpen(true)}
                    paperTitle={selectedPaper.title}
                  />
                </TabsContent>
              )}
            </Tabs>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              <p>Select a paper to get started</p>
            </div>
          )}
        </div>
      </div>

      {/* Save to Notes Modal */}
      <SaveSummaryModal
        open={saveModalOpen}
        onOpenChange={setSaveModalOpen}
        onSave={handleSaveToNotes}
        existingNotes={existingNotes}
        paperTitle={selectedPaper?.title}
        paperAuthors={selectedPaper?.authors}
        paperYear={selectedPaper?.year}
        agent={currentSummary?.agent}
      />

      {/* Export Dialog */}
      {currentSummary && (
        <ExportSummaryDialog
          open={exportDialogOpen}
          onOpenChange={setExportDialogOpen}
          onExport={handleExport}
          content={currentSummary.content}
          paperTitle={selectedPaper?.title}
          authors={selectedPaper?.authors}
          year={selectedPaper?.year}
          agent={currentSummary.agent}
          style={currentSummary.style}
        />
      )}
    </div>
  );
}

