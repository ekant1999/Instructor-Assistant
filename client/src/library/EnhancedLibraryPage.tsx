import React, { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { renderToStaticMarkup } from 'react-dom/server';
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
  deleteSummary,
  createPaperSummary,
  downloadPaper,
  listNotes,
  listPaperSections,
  listPapers,
  listPaperSummaries,
  updateSummary,
  updateNote,
  createNote,
} from '@/lib/api';
import { mapApiNote, mapApiPaper, mapApiSection, mapApiSummary } from '@/lib/mappers';

const countWords = (text: string) => text.split(/\s+/).filter(Boolean).length;

const normalizeSummaryStyle = (
  style?: SummarizeConfig['style'] | Summary['style']
): Summary['style'] | undefined => {
  if (!style) return undefined;
  if (style === 'bullet') return 'brief';
  return style as Summary['style'];
};

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

  const upsertSummaryForPaper = (paperId: string, summary: Summary, replaceId?: string) => {
    setSummaries((prev) => {
      const next = new Map(prev);
      const existing = next.get(paperId) || [];
      const filtered = existing.filter((item) => item.id !== summary.id && item.id !== replaceId);
      const sorted = [...filtered, summary].sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
      next.set(paperId, sorted);
      return next;
    });
  };

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

  useEffect(() => {
    if (!selectedId || summaries.get(selectedId)) return;
    void ensureSummaries(selectedId);
  }, [selectedId, summaries]);

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

  async function ensureSummaries(paperId: string): Promise<Summary[]> {
    const cached = summaries.get(paperId);
    if (cached) return cached;
    try {
      const apiSummaries = await listPaperSummaries(Number(paperId));
      const mapped = apiSummaries.map(mapApiSummary);
      setSummaries((prev) => {
        const next = new Map(prev);
        next.set(paperId, mapped);
        return next;
      });
      return mapped;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load summary history');
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
      bullet:
        'Summarize the paper as concise Markdown bullet points. Use "-" for each bullet and keep each bullet to 1-2 sentences.',
      detailed:
        'Provide a detailed Markdown summary with headings: "## Background", "## Methodology", "## Results", and "## Implications". Use bullets where appropriate.',
      teaching:
        'Create a teaching-focused Markdown summary with headings: "## Key Concepts", "## Definitions", and "## Exam Questions". Use numbered questions under "## Exam Questions".'
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

    const formatNote = 'Return only Markdown (no code fences, no preamble).';
    return `${styleInstructions[style as keyof typeof styleInstructions] || styleInstructions.bullet}\n${formatNote}\n${focusBlock}${custom}`;
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
      const summaryStyle = normalizeSummaryStyle(config.style);

      const created = await createPaperSummary(Number(selectedPaper.id), {
        title: `Summary: ${selectedPaper.title}`,
        content,
        agent,
        style: summaryStyle,
        word_count: wordCount,
        is_edited: false,
        metadata: { scope: config.scope, method: config.method }
      });
      const mapped = mapApiSummary(created);
      upsertSummaryForPaper(selectedPaper.id, mapped);
      setCurrentSummary(mapped);
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
        const summaryStyle = normalizeSummaryStyle('detailed');
        const created = await createPaperSummary(Number(paper.id), {
          title: `Summary: ${paper.title}`,
          content: `## ${paper.title}\n\n${content}`,
          agent,
          style: summaryStyle,
          word_count: wordCount,
          is_edited: false,
          metadata: { scope: 'multiple', method: agent.toLowerCase() }
        });
        const mapped = mapApiSummary(created);
        upsertSummaryForPaper(paper.id, mapped);
        combinedSummaries.push(mapped);
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
        updatedAt: Date.now(),
        metadata: { source: 'local' }
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

  const handleUpdateSummary = async (markdown: string) => {
    if (!currentSummary) return;
    const updatedSummary: Summary = {
      ...currentSummary,
      content: markdown,
      isEdited: true,
      updatedAt: Date.now(),
      wordCount: countWords(markdown)
    };
    setCurrentSummary(updatedSummary);
    if (updatedSummary.paperId) {
      upsertSummaryForPaper(updatedSummary.paperId, updatedSummary);
    }

    const summaryId = Number(updatedSummary.id);
    if (Number.isNaN(summaryId)) {
      return;
    }
    try {
      const updated = await updateSummary(summaryId, {
        title: updatedSummary.title,
        content: markdown,
        agent: updatedSummary.agent,
        style: updatedSummary.style,
        word_count: updatedSummary.wordCount,
        is_edited: true,
        metadata: updatedSummary.metadata
      });
      const mapped = mapApiSummary(updated);
      if (mapped.paperId) {
        upsertSummaryForPaper(mapped.paperId, mapped, updatedSummary.id);
      }
      setCurrentSummary(mapped);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update summary history');
    }
  };

  const removeSummaryFromState = (paperId: string, summaryId: string) => {
    setSummaries((prev) => {
      const next = new Map(prev);
      const existing = next.get(paperId) || [];
      const filtered = existing.filter((s) => s.id !== summaryId);
      if (filtered.length > 0) {
        next.set(paperId, filtered);
      } else {
        next.delete(paperId);
      }
      return next;
    });
    if (currentSummary?.id === summaryId) {
      setCurrentSummary(null);
    }
  };

  const handleDeleteSummary = async (summary: Summary) => {
    if (!summary.paperId) return;
    const summaryId = Number(summary.id);
    try {
      if (!Number.isNaN(summaryId)) {
        await deleteSummary(summaryId);
      }
      removeSummaryFromState(summary.paperId, summary.id);
      toast.success('Summary deleted');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete summary');
    }
  };

  const escapeHtml = (value: string) =>
    value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const escapeLatex = (value: string) =>
    value.replace(/[\\{}$#%&_^\~]/g, (match) => {
      switch (match) {
        case '\\':
          return '\\textbackslash{}';
        case '~':
          return '\\textasciitilde{}';
        case '^':
          return '\\textasciicircum{}';
        default:
          return `\\${match}`;
      }
    });

  const downloadTextFile = (content: string, filename: string) => {
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', filename);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const renderMarkdownToHtml = (markdown: string) =>
    renderToStaticMarkup(<ReactMarkdown>{markdown}</ReactMarkdown>);

  const exportAsPdf = (content: string, metadata: any) => {
    const title = metadata?.paperTitle || 'Summary';
    const win = window.open('', '_blank');
    if (!win) {
      toast.error('Please allow popups to export a PDF.');
      return;
    }
    const metaItems = [
      { label: 'Authors', value: metadata?.authors },
      { label: 'Year', value: metadata?.year },
      { label: 'Agent', value: metadata?.agent },
      { label: 'Style', value: metadata?.style }
    ].filter((item) => item.value);
    const metaHtml = metaItems
      .map(
        (item) =>
          `<div><strong>${escapeHtml(item.label)}:</strong> ${escapeHtml(String(item.value))}</div>`
      )
      .join('');
    const htmlContent = renderMarkdownToHtml(content);
    const body = `
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>${escapeHtml(title)} Summary</title>
          <style>
            body { font-family: "Georgia", "Times New Roman", serif; padding: 48px; color: #111; }
            h1, h2, h3, h4 { font-family: "Helvetica Neue", Arial, sans-serif; }
            h1 { font-size: 22px; margin-bottom: 8px; }
            h2 { font-size: 18px; margin-top: 24px; }
            h3 { font-size: 16px; margin-top: 20px; }
            p { line-height: 1.6; margin: 12px 0; }
            ul, ol { margin: 12px 0 12px 24px; }
            li { margin: 6px 0; }
            strong { font-weight: 600; }
            code { font-family: "SFMono-Regular", Menlo, monospace; background: #f4f4f4; padding: 2px 4px; border-radius: 4px; }
            pre code { display: block; padding: 12px; }
            .meta { font-size: 12px; color: #555; margin-bottom: 20px; }
            hr { border: none; border-top: 1px solid #e5e5e5; margin: 20px 0; }
            @page { margin: 1in; }
          </style>
        </head>
        <body>
          <h1>${escapeHtml(title)} Summary</h1>
          ${metaHtml ? `<div class="meta">${metaHtml}</div><hr />` : ''}
          <div class="content">${htmlContent}</div>
        </body>
      </html>
    `;
    win.document.write(body);
    win.document.close();
    win.focus();
    win.print();
  };

  const handleExportSummary = async (
    format: 'pdf' | 'txt' | 'latex' | 'markdown' | 'docx',
    content: string,
    metadata: any
  ) => {
    if (!content || !content.trim()) {
      toast.error('No summary content to export');
      return;
    }
    const filename = metadata?.filename || `Summary_${Date.now()}.${format === 'markdown' ? 'md' : format}`;

    if (format === 'pdf') {
      exportAsPdf(content, metadata);
      return;
    }

    if (format === 'docx') {
      try {
        const { Document: DocxDocument, Paragraph, TextRun, HeadingLevel, Packer } = await import('docx');
        const title = metadata?.paperTitle || 'Summary';
        const lines = content.split(/\r?\n/);
        const paragraphs: any[] = [];

        const metaItems = [
          { label: 'Authors', value: metadata?.authors },
          { label: 'Year', value: metadata?.year },
          { label: 'Agent', value: metadata?.agent },
          { label: 'Style', value: metadata?.style }
        ].filter((item) => item.value);

        const parseInlineMarkdown = (text: string) => {
          const runs: any[] = [];
          const regex = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
          let lastIndex = 0;
          let match;
          while ((match = regex.exec(text)) !== null) {
            if (match.index > lastIndex) {
              runs.push(new TextRun(text.slice(lastIndex, match.index)));
            }
            const token = match[0];
            if (token.startsWith('**')) {
              runs.push(new TextRun({ text: token.slice(2, -2), bold: true }));
            } else {
              runs.push(new TextRun({ text: token.slice(1, -1), italics: true }));
            }
            lastIndex = match.index + token.length;
          }
          if (lastIndex < text.length) {
            runs.push(new TextRun(text.slice(lastIndex)));
          }
          return runs.length ? runs : [new TextRun(text)];
        };

        paragraphs.push(
          new Paragraph({
            text: `${title} Summary`,
            heading: HeadingLevel.HEADING_1
          })
        );

        metaItems.forEach((item) => {
          paragraphs.push(
            new Paragraph({
              children: [
                new TextRun({ text: `${item.label}: `, bold: true }),
                new TextRun(String(item.value))
              ]
            })
          );
        });

        if (metaItems.length > 0) {
          paragraphs.push(new Paragraph(''));
        }

        const headingMap: Record<number, any> = {
          1: HeadingLevel.HEADING_1,
          2: HeadingLevel.HEADING_2,
          3: HeadingLevel.HEADING_3,
          4: HeadingLevel.HEADING_4,
          5: HeadingLevel.HEADING_5,
          6: HeadingLevel.HEADING_6
        };

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            paragraphs.push(new Paragraph(''));
            continue;
          }
          const headingMatch = /^(#{1,6})\s+(.*)/.exec(trimmed);
          if (headingMatch) {
            const level = headingMatch[1].length;
            paragraphs.push(
              new Paragraph({
                text: headingMatch[2],
                heading: headingMap[level] || HeadingLevel.HEADING_2
              })
            );
            continue;
          }
          if (/^[-*+]\s+/.test(trimmed)) {
            paragraphs.push(
              new Paragraph({
                children: parseInlineMarkdown(trimmed.replace(/^[-*+]\s+/, '')),
                bullet: { level: 0 }
              })
            );
            continue;
          }
          if (/^\d+\.\s+/.test(trimmed)) {
            paragraphs.push(
              new Paragraph({
                children: parseInlineMarkdown(trimmed.replace(/^\d+\.\s+/, '')),
                bullet: { level: 0 }
              })
            );
            continue;
          }
          paragraphs.push(new Paragraph({ children: parseInlineMarkdown(trimmed) }));
        }

        const doc = new DocxDocument({
          sections: [
            {
              children: paragraphs
            }
          ]
        });

        const blob = await Packer.toBlob(doc);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename.endsWith('.docx') ? filename : `${filename}.docx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'DOCX export failed');
      }
      return;
    }

    if (format === 'latex') {
      const title = metadata?.paperTitle || 'Summary';
      const latex = [
        '\\documentclass{article}',
        '\\usepackage[margin=1in]{geometry}',
        '\\begin{document}',
        `\\section*{${escapeLatex(title)} Summary}`,
        escapeLatex(content),
        '\\end{document}'
      ].join('\n');
      downloadTextFile(latex, filename);
      return;
    }

    downloadTextFile(content, filename);
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
      setSummaries((prev) => {
        const next = new Map(prev);
        next.delete(id);
        return next;
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
    <div className="flex h-full w-full flex-col bg-background min-h-0">
      <UploadPanel onUpload={handleAddPapers} onDownload={downloadPaper} />

      <div className="flex flex-1 overflow-hidden min-h-0">
        <div className="w-[360px] border-r bg-muted/5 flex flex-col h-full overflow-hidden min-h-0 ia-library-panel">
          <div className="p-4 border-b sticky top-0 bg-background z-10">
            <h2 className="font-semibold text-sm flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Papers
            </h2>
            <p className="text-xs text-muted-foreground mt-1">{papers.length} papers in library</p>
          </div>

          <div className="flex-1 overflow-auto min-h-0 ia-library-panel-body">
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

        <div className="flex-1 h-full overflow-hidden min-h-0">
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
                  onEdit={(summary) => {
                    setCurrentSummary(summary);
                    setActiveTab('output');
                  }}
                  onDelete={(id) => {
                    const summary = paperSummaries.find((item) => item.id === id);
                    if (summary) {
                      void handleDeleteSummary(summary);
                    }
                  }}
                />
              </TabsContent>

              {currentSummary && (
                <TabsContent value="output" className="flex-1 overflow-hidden">
                  <EnhancedSummaryEditor
                    summary={currentSummary}
                    paperTitle={selectedPaper.title}
                    onSave={handleUpdateSummary}
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
        onExport={handleExportSummary}
        content={currentSummary?.content || ''}
        paperTitle={selectedPaper?.title}
        authors={selectedPaper?.authors}
        year={selectedPaper?.year}
        agent={currentSummary?.agent}
        style={currentSummary?.style}
      />
    </div>
  );
}
