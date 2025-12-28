import React, { useEffect, useMemo, useState } from 'react';
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
import { Paper, Summary, Document, Section } from '@/shared/types';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, Layers, Sparkles, BookOpen, History } from 'lucide-react';
import { toast } from 'sonner';
import {
  chatPaper,
  deletePaper,
  downloadPaper,
  listNotes,
  listPaperSections,
  listPapers,
  updateNote,
  createNote,
} from '@/lib/api';
import { mapApiNote, mapApiPaper, mapApiSection } from '@/lib/mappers';

export default function EnhancedLibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set());
  const [selectedSections, setSelectedSections] = useState<Set<string>>(new Set());
  const [sectionsByPaperId, setSectionsByPaperId] = useState<Record<string, Section[]>>({});
  const [summaries, setSummaries] = useState<Map<string, Summary[]>>(new Map());
  const [currentSummary, setCurrentSummary] = useState<Summary | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ current?: string; progress?: number; total?: number }>({});
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [existingNotes, setExistingNotes] = useState<Document[]>([]);
  const [activeTab, setActiveTab] = useState<string>('preview');
  const [isLoading, setIsLoading] = useState(false);

  const selectedPaper = useMemo(() => {
    if (!selectedId) return null;
    const base = papers.find((p) => p.id === selectedId);
    if (!base) return null;
    const sections = sectionsByPaperId[selectedId];
    if (sections) {
      return { ...base, sections };
    }
    return base;
  }, [papers, selectedId, sectionsByPaperId]);

  const paperSummaries = selectedPaper ? summaries.get(selectedPaper.id) || [] : [];

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      setIsLoading(true);
      try {
        const [paperRows, noteRows] = await Promise.all([listPapers(), listNotes()]);
        if (!isMounted) return;
        const mappedPapers = paperRows.map(mapApiPaper);
        setPapers(mappedPapers);
        setExistingNotes(noteRows.map(mapApiNote));
        if (mappedPapers.length > 0) {
          setSelectedId(mappedPapers[0].id);
        }
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Failed to load library data');
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedId || sectionsByPaperId[selectedId]) return;
    void ensureSections(selectedId);
  }, [selectedId, sectionsByPaperId]);

  async function ensureSections(paperId: string): Promise<Section[]> {
    const cached = sectionsByPaperId[paperId];
    if (cached) return cached;
    try {
      const apiSections = await listPaperSections(Number(paperId), true, 2000);
      const mapped = apiSections.map(mapApiSection);
      setSectionsByPaperId((prev) => ({ ...prev, [paperId]: mapped }));
      return mapped;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load paper sections');
      return [];
    }
  }

  const handleAddPapers = (newPapers: Paper[]) => {
    if (newPapers.length === 0) return;
    setPapers((prev) => [...newPapers, ...prev]);
    setSelectedId(newPapers[0].id);
    setSelectedSections(new Set());
    setCurrentSummary(null);
    setActiveTab('preview');
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
        setSelectedSections(new Set(selectedPaper.sections.map((s) => s.id)));
      }
    }
  };

  const buildSummaryPrompt = (config: SummarizeConfig, sections: Section[]) => {
    const style = config.style || 'bullet';
    const styleInstructions = {
      bullet: 'Summarize the paper in concise bullet points.',
      detailed: 'Provide a detailed summary with sections for background, methodology, and results.',
      teaching: 'Create a teaching-focused summary with key concepts, definitions, and potential exam questions.'
    };

    const selectedContent = sections
      .filter((s) => selectedSections.has(s.id))
      .map((s) => `### ${s.title}\n${s.content}`)
      .join('\n\n')
      .slice(0, 12000);

    const focusBlock = selectedContent
      ? `Focus on the following excerpts:\n${selectedContent}`
      : 'Summarize the full paper content.';

    const custom = config.customPrompt ? `\n\nAdditional instructions:\n${config.customPrompt}` : '';

    return `${styleInstructions[style as keyof typeof styleInstructions] || styleInstructions.bullet}\n${focusBlock}${custom}`;
  };

  const generateSummary = async (
    paperId: string,
    config: SummarizeConfig,
    agent: 'Gemini' | 'GPT' | 'Qwen' = 'Qwen'
  ): Promise<string> => {
    const sections = await ensureSections(paperId);
    const prompt = buildSummaryPrompt(config, sections);
    const response = await chatPaper(Number(paperId), [{ role: 'user', content: prompt }]);
    return response.message || '';
  };

  const handleSummarize = async (config: SummarizeConfig) => {
    if (!selectedPaper) return;

    setIsSummarizing(true);
    const agent = config.method === 'gpt' ? 'GPT' : config.method === 'gemini' ? 'Gemini' : 'Qwen';

    try {
      const content = await generateSummary(selectedPaper.id, config, agent);
      const wordCount = content.split(/\s+/).filter(Boolean).length;

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
      setActiveTab('output');
      toast.success('Summary generated successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to generate summary');
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleBatchSummarize = async (agent: 'Gemini' | 'GPT' | 'Qwen') => {
    if (selectedPaperIds.size === 0) return;

    setIsSummarizing(true);
    const selectedPapers = papers.filter((p) => selectedPaperIds.has(p.id));
    setBatchProgress({ total: selectedPapers.length, progress: 0 });

    try {
      const combinedSummaries: Summary[] = [];

      for (let i = 0; i < selectedPapers.length; i++) {
        const paper = selectedPapers[i];
        setBatchProgress({ total: selectedPapers.length, progress: i + 1, current: paper.title });

        const content = await generateSummary(
          paper.id,
          {
            scope: 'multiple',
            method: agent === 'Gemini' ? 'gemini' : agent === 'GPT' ? 'gpt' : 'local',
            style: 'detailed'
          },
          agent
        );

        const wordCount = content.split(/\s+/).filter(Boolean).length;
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

        const existing = summaries.get(paper.id) || [];
        setSummaries(new Map(summaries.set(paper.id, [...existing, summary])));
      }

      const combinedContent = combinedSummaries.map((s) => s.content).join('\n\n---\n\n');
      const combinedSummary: Summary = {
        id: Math.random().toString(),
        title: `Combined Summary: ${selectedPapers.length} Papers`,
        content: combinedContent,
        agent,
        style: 'detailed',
        wordCount: combinedContent.split(/\s+/).filter(Boolean).length,
        isEdited: false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      };

      setCurrentSummary(combinedSummary);
      setActiveTab('output');
      toast.success(`Generated ${selectedPapers.length} summaries`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to generate batch summaries');
    } finally {
      setIsSummarizing(false);
      setBatchProgress({});
    }
  };

  const handleSaveSummary = async (
    action: 'new' | 'append',
    noteId?: string,
    title?: string,
    tags?: string[]
  ) => {
    if (!currentSummary) return;

    try {
      if (action === 'new') {
        const nextTags = tags && tags.length > 0 ? tags : ['summary'];
        const created = await createNote({
          title: title || currentSummary.title,
          body: currentSummary.content,
          paper_id: selectedPaper ? Number(selectedPaper.id) : null,
          tags: nextTags
        });
        setExistingNotes((prev) => [mapApiNote(created), ...prev]);
      } else if (action === 'append' && noteId) {
        const target = existingNotes.find((note) => note.id === noteId);
        const nextBody = `${target?.content || ''}\n\n---\n\n${currentSummary.content}`.trim();
        const updated = await updateNote(Number(noteId), { body: nextBody, tags: tags ?? target?.tags });
        setExistingNotes((prev) => prev.map((note) => (note.id === noteId ? mapApiNote(updated) : note)));
      }
      toast.success('Summary saved to notes');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to save summary');
    }
  };

  const handleDeletePaper = async (id: string) => {
    try {
      await deletePaper(Number(id));
      setPapers((prev) => prev.filter((p) => p.id !== id));
      setSelectedPaperIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      setSectionsByPaperId((prev) => {
        const { [id]: _, ...rest } = prev;
        return rest;
      });
      if (selectedId === id) {
        const nextPaper = papers.find((p) => p.id !== id);
        setSelectedId(nextPaper?.id);
        setSelectedSections(new Set());
      }
      toast.success('Paper deleted');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete paper');
    }
  };

  return (
    <div className="flex h-full w-full flex-col bg-background">
      <UploadPanel onUpload={handleAddPapers} onDownload={downloadPaper} />

      <div className="flex flex-1 overflow-hidden">
        <div className="w-[360px] border-r bg-muted/5 flex flex-col h-full overflow-hidden">
          <div className="p-4 border-b sticky top-0 bg-background z-10">
            <h2 className="font-semibold text-sm flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Papers
            </h2>
            <p className="text-xs text-muted-foreground mt-1">{papers.length} papers in library</p>
          </div>

          <div className="flex-1 overflow-auto">
            <EnhancedPaperList
              papers={papers}
              selectedId={selectedId}
              selectedIds={selectedPaperIds}
              onSelectionChange={setSelectedPaperIds}
              onSelect={(paper) => {
                setSelectedId(paper.id);
                setSelectedSections(new Set());
                setCurrentSummary(null);
                setActiveTab('preview');
              }}
              onDelete={handleDeletePaper}
              onSummarize={(id) => {
                setSelectedId(id);
                setSelectedSections(new Set());
                setActiveTab('summarize');
              }}
            />
          </div>
        </div>

        <div className="flex-1 h-full overflow-hidden">
          {isLoading && (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              Loading library...
            </div>
          )}

          {!isLoading && selectedPaper ? (
            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
              <TabsList className="w-full justify-start rounded-none border-b h-auto p-0 bg-transparent">
                <TabsTrigger value="preview" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
                  <FileText className="h-4 w-4 mr-2" />
                  Preview
                </TabsTrigger>
                <TabsTrigger value="sections" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
                  <Layers className="h-4 w-4 mr-2" />
                  Sections
                </TabsTrigger>
                <TabsTrigger value="summarize" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
                  <Sparkles className="h-4 w-4 mr-2" />
                  Summarize
                </TabsTrigger>
                <TabsTrigger value="history" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
                  <History className="h-4 w-4 mr-2" />
                  History
                </TabsTrigger>
                {currentSummary && (
                  <TabsTrigger value="output" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
                    <BookOpen className="h-4 w-4 mr-2" />
                    Output
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
                <div className="p-4 space-y-4">
                  <SummarizePanel
                    selectedSectionCount={selectedSections.size}
                    onSummarize={handleSummarize}
                    isLoading={isSummarizing}
                  />
                  <BatchSummarizePanel
                    selectedPaperIds={selectedPaperIds}
                    papers={papers}
                    onSummarize={handleBatchSummarize}
                    isLoading={isSummarizing}
                    progress={batchProgress}
                  />
                </div>
              </TabsContent>

              <TabsContent value="history" className="flex-1 overflow-hidden">
                <SummaryHistory
                  summaries={paperSummaries}
                  onSelect={(summary) => {
                    setCurrentSummary(summary);
                    setActiveTab('output');
                  }}
                  onDelete={(id) => {
                    const existing = summaries.get(selectedPaper.id) || [];
                    setSummaries(new Map(summaries.set(selectedPaper.id, existing.filter((s) => s.id !== id))));
                    if (currentSummary?.id === id) {
                      setCurrentSummary(null);
                    }
                  }}
                />
              </TabsContent>

              {currentSummary && (
                <TabsContent value="output" className="flex-1 overflow-hidden">
                  <EnhancedSummaryEditor
                    summary={currentSummary}
                    paperTitle={selectedPaper.title}
                    onSave={(markdown: string) => {
                      setCurrentSummary({
                        ...currentSummary,
                        content: markdown,
                        isEdited: true,
                        updatedAt: Date.now()
                      });
                    }}
                    onExport={() => setExportDialogOpen(true)}
                    onSaveToNotes={() => setSaveModalOpen(true)}
                  />
                </TabsContent>
              )}
            </Tabs>
          ) : (
            !isLoading && (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                No papers available. Upload a paper to get started.
              </div>
            )
          )}
        </div>
      </div>

      <SaveSummaryModal
        open={saveModalOpen}
        onOpenChange={setSaveModalOpen}
        onSave={handleSaveSummary}
        existingNotes={existingNotes}
        paperTitle={selectedPaper?.title}
        paperAuthors={selectedPaper?.authors}
        paperYear={selectedPaper?.year}
        agent={currentSummary?.agent}
      />

      <ExportSummaryDialog
        open={exportDialogOpen}
        onOpenChange={setExportDialogOpen}
        summary={currentSummary}
      />
    </div>
  );
}
