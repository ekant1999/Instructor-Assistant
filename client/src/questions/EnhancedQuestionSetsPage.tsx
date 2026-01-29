import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { renderToStaticMarkup } from 'react-dom/server';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, RefreshCw, Save, Plus, Download } from 'lucide-react';
import { QuestionConfigPanel, QuestionTypeConfig } from './QuestionConfigPanel';
import { QuestionEditor } from './QuestionEditor';
import { DocumentSelector, UploadContext } from './DocumentSelector';
import { ExportQuestionSetDialog } from './ExportQuestionSetDialog';
import { Question, QuestionSet, Paper, Document } from '@/shared/types';
import { toast } from 'sonner';
import {
  createNote,
  createQuestionSet,
  generateQuestionSetWithLLM,
  getPaperContext,
  listNotes,
  listPapers,
  uploadQuestionContext,
  pushQuestionSetToCanvas,
  updateQuestionSet
} from '@/lib/api';
import {
  mapApiNote,
  mapApiPaper,
  mapApiQuestion,
  mapApiQuestionSet,
  mapUiQuestionToApi
} from '@/lib/mappers';

export default function EnhancedQuestionSetsPage() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [questionSet, setQuestionSet] = useState<QuestionSet | null>(null);
  const [questionMarkdown, setQuestionMarkdown] = useState<string | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [notes, setNotes] = useState<Document[]>([]);
  const [uploads, setUploads] = useState<UploadContext[]>([]);
  const [selectedUploadIds, setSelectedUploadIds] = useState<Set<string>>(new Set());
  const [paperSearchQuery, setPaperSearchQuery] = useState<string>('');
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set());
  const [selectedNoteIds, setSelectedNoteIds] = useState<Set<string>>(new Set());
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  
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

  const [questionConfigs, setQuestionConfigs] = useState<QuestionTypeConfig[]>([
    { type: 'multiple-choice', enabled: true, count: 5, options: { numOptions: 4 } },
    { type: 'true-false', enabled: true, count: 3, options: { includeExplanation: true } },
    { type: 'short-answer', enabled: false, count: 2, options: { expectedLength: 'sentence' } },
    { type: 'essay', enabled: false, count: 1, options: { wordCountRange: { min: 200, max: 500 } } }
  ]);

  const questionTypeToKind: Record<QuestionTypeConfig['type'], string> = {
    'multiple-choice': 'mcq',
    'true-false': 'true_false',
    'short-answer': 'short_answer',
    essay: 'essay'
  };

  const buildInstructions = (configs: QuestionTypeConfig[]) => {
    const enabled = configs.filter((c) => c.enabled && c.count > 0);
    if (enabled.length === 0) {
      return 'Generate exam-ready questions based on the provided context.';
    }

    const countLine = enabled
      .map((c) => {
        switch (c.type) {
          case 'multiple-choice':
            return `${c.count} multiple choice questions`;
          case 'true-false':
            return `${c.count} true/false questions`;
          case 'short-answer':
            return `${c.count} short answer questions`;
          case 'essay':
            return `${c.count} essay questions`;
          default:
            return `${c.count} questions`;
        }
      })
      .join(', ');

    const detailLines: string[] = [];
    enabled.forEach((c) => {
      if (c.type === 'multiple-choice') {
        const numOptions = c.options?.numOptions || 4;
        detailLines.push(`Multiple choice: use ${numOptions} options per question.`);
        if (c.options?.includeAllOfAbove) {
          detailLines.push('Multiple choice: include an "All of the above" option when appropriate.');
        }
        if (c.options?.includeNoneOfAbove) {
          detailLines.push('Multiple choice: include a "None of the above" option when appropriate.');
        }
      }
      if (c.type === 'true-false') {
        detailLines.push(
          c.options?.includeExplanation
            ? 'True/false: include a brief explanation.'
            : 'True/false: omit explanations unless needed for clarity.'
        );
      }
      if (c.type === 'short-answer') {
        const length = c.options?.expectedLength || 'sentence';
        detailLines.push(`Short answer: target a ${length} response length.`);
        if (c.options?.includeSampleAnswer) {
          detailLines.push('Short answer: include a sample answer.');
        }
      }
      if (c.type === 'essay') {
        const min = c.options?.wordCountRange?.min || 200;
        const max = c.options?.wordCountRange?.max || 500;
        detailLines.push(`Essay: target ${min}-${max} words.`);
        if (c.options?.includeRubric) {
          detailLines.push('Essay: include a brief grading rubric.');
        }
      }
    });

    return [
      `Generate ${countLine} based on the provided context.`,
      'Use the labels mcq, true_false, short_answer, or essay for the question type.',
      ...detailLines
    ]
      .filter(Boolean)
      .join(' ');
  };

  const buildContext = async () => {
    const maxCharsPerPaper = 12000;
    const maxCharsPerUpload = 12000;
    const maxTotalChars = 60000;
    const paperIds = Array.from(selectedPaperIds)
      .map((id) => Number(id))
      .filter((id) => Number.isFinite(id));
    const noteIds = Array.from(selectedNoteIds);
    const uploadIds = Array.from(selectedUploadIds);

    const paperById = new Map(papers.map((p) => [p.id, p]));
    const noteById = new Map(notes.map((n) => [n.id, n]));
    const uploadById = new Map(uploads.map((u) => [u.id, u]));

    const paperParts = await Promise.all(
      paperIds.map(async (id) => {
        try {
          const context = await getPaperContext(id, undefined, maxCharsPerPaper);
          if (!context.trim()) return null;
          const paper = paperById.get(String(id));
          const title = paper?.title || `Paper ${id}`;
          return `Paper: ${title}\n\n${context}`;
        } catch {
          return null;
        }
      })
    );

    const noteParts = noteIds
      .map((id) => noteById.get(id))
      .filter(Boolean)
      .map((note) => `Note: ${note?.title}\n\n${note?.content}`);

    const uploadParts = uploadIds
      .map((id) => uploadById.get(id))
      .filter(Boolean)
      .map((upload) => {
        const text = (upload?.text || '').trim();
        if (!text) return null;
        const clipped = text.slice(0, maxCharsPerUpload);
        return `Upload: ${upload?.filename}\n\n${clipped}`;
      });

    const combined = [...paperParts, ...noteParts, ...uploadParts].filter(Boolean).join('\n\n---\n\n');
    return combined.slice(0, maxTotalChars);
  };

  const buildQuestionMarkdown = (
    items: Question[],
    options?: { includeAnswers?: boolean; includeExplanations?: boolean }
  ) => {
    return items
      .map((q, idx) => {
        let text = `### Question ${idx + 1}\n\n${q.question}\n\n`;
        if (q.options) {
          q.options.forEach((opt, optIdx) => {
            text += `${String.fromCharCode(65 + optIdx)}) ${opt}\n`;
          });
        }
        if (options?.includeAnswers) {
          let answerText: string | number = q.correctAnswer;
          if (q.type === 'multiple-choice' && typeof q.correctAnswer === 'number') {
            const idx = q.correctAnswer;
            const option = q.options?.[idx];
            answerText = option ? `${String.fromCharCode(65 + idx)}) ${option}` : String.fromCharCode(65 + idx);
          }
          text += `\n**Answer:** ${answerText}\n`;
        }
        if (options?.includeExplanations && q.explanation) {
          text += `\n**Explanation:** ${q.explanation}\n`;
        }
        return text.trim();
      })
      .join('\n\n---\n\n');
  };

  const isSupportedUpload = (file: File) => {
    const name = file.name.toLowerCase();
    return name.endsWith('.pdf') || name.endsWith('.ppt') || name.endsWith('.pptx');
  };

  const handleUploadFiles = async (files: FileList | File[]) => {
    const list = Array.from(files || []);
    if (list.length === 0) return;
    setIsUploading(true);
    try {
      for (const file of list) {
        if (!isSupportedUpload(file)) {
          toast.error(`Unsupported file type: ${file.name}`);
          continue;
        }
        try {
          const context = await uploadQuestionContext(file);
          const upload: UploadContext = {
            id: context.context_id,
            filename: context.filename,
            characters: context.characters,
            preview: context.preview,
            text: context.text
          };
          setUploads((prev) => [upload, ...prev]);
          setSelectedUploadIds((prev) => {
            const next = new Set(prev);
            next.add(upload.id);
            return next;
          });
          toast.success(`Uploaded ${upload.filename}`);
        } catch (error) {
          toast.error(error instanceof Error ? error.message : `Failed to upload ${file.name}`);
        }
      }
    } finally {
      setIsUploading(false);
    }
  };

  const stripPromptFromMarkdown = (markdown: string, prompt?: string) => {
    let cleaned = markdown.replace(/<!--\s*Prompt:.*?-->\s*\n?/gis, '').trimStart();
    if (!prompt) {
      return cleaned;
    }
    const normalized = prompt.trim();
    if (!normalized) return cleaned;
    const leadingPromptMatch = cleaned.match(/^Prompt:\s*\n([\s\S]*?)(\n{2,}|$)/i);
    if (leadingPromptMatch) {
      const block = leadingPromptMatch[1].trim();
      if (block === normalized) {
        cleaned = cleaned.slice(leadingPromptMatch[0].length).trimStart();
      }
    }
    return cleaned;
  };

  const escapeHtml = (value: string) =>
    value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const renderMarkdownToHtml = (markdown: string) =>
    renderToStaticMarkup(<ReactMarkdown>{markdown}</ReactMarkdown>);

  const openPdfWindow = (title: string, markdown: string, meta: Array<{ label: string; value?: string | number }>) => {
    const win = window.open('', '_blank');
    if (!win) {
      toast.error('Please allow popups to export a PDF.');
      return false;
    }
    const metaHtml = meta
      .filter((item) => item.value !== undefined && item.value !== null && String(item.value).trim() !== '')
      .map(
        (item) =>
          `<div><strong>${escapeHtml(item.label)}:</strong> ${escapeHtml(String(item.value))}</div>`
      )
      .join('');
    const htmlContent = renderMarkdownToHtml(markdown);
    const body = `
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>${escapeHtml(title)}</title>
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
          <h1>${escapeHtml(title)}</h1>
          ${metaHtml ? `<div class="meta">${metaHtml}</div><hr />` : ''}
          <div class="content">${htmlContent}</div>
        </body>
      </html>
    `;
    win.document.write(body);
    win.document.close();
    win.focus();
    win.print();
    return true;
  };

  const handleGenerate = async () => {
    if (selectedPaperIds.size === 0 && selectedNoteIds.size === 0 && selectedUploadIds.size === 0) {
      toast.error('Please select at least one source document');
      return;
    }

    const enabledConfigs = questionConfigs.filter(c => c.enabled && c.count > 0);
    const totalQuestions = enabledConfigs.reduce((sum, c) => sum + c.count, 0);

    if (totalQuestions === 0) {
      toast.error('Please enable at least one question type');
      return;
    }

    setIsGenerating(true);
    try {
      const selectedSourceIds = [
        ...Array.from(selectedPaperIds),
        ...Array.from(selectedNoteIds),
        ...Array.from(selectedUploadIds)
      ];
      const instructions = buildInstructions(questionConfigs);
      const context = await buildContext();
      const questionTypes = enabledConfigs.map((c) => questionTypeToKind[c.type]);

      const result = await generateQuestionSetWithLLM({
        instructions,
        context: context || undefined,
        question_count: totalQuestions,
        question_types: questionTypes
      });

      const generatedQuestions = result.questions.map(mapApiQuestion);
      setQuestions(generatedQuestions);
      setQuestionMarkdown(result.markdown || null);

      let savedSet: QuestionSet | null = null;
      try {
        const savedPayload = await createQuestionSet({
          prompt: instructions,
          questions: result.questions
        });
        const mapped = mapApiQuestionSet(savedPayload);
        savedSet = {
          ...mapped,
          questions: generatedQuestions,
          sourceDocumentIds: selectedSourceIds,
          prompt: instructions
        };
      } catch (error) {
        toast.error('Generated questions but failed to save the set');
      }

      setQuestionSet(
        savedSet || {
          id: Math.random().toString(),
          title: `Q&A Set: ${Array.from(selectedPaperIds).length} papers, ${Array.from(selectedNoteIds).length} notes, ${Array.from(selectedUploadIds).length} uploads`,
          questions: generatedQuestions,
          sourceDocumentIds: selectedSourceIds,
          agent: 'Qwen',
          createdAt: Date.now(),
          updatedAt: Date.now(),
          prompt: instructions
        }
      );
      toast.success(`Generated ${generatedQuestions.length} questions`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to generate questions');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAddMore = async () => {
    const enabledConfigs = questionConfigs.filter(c => c.enabled && c.count > 0);
    const totalNew = enabledConfigs.reduce((sum, c) => sum + c.count, 0);

    if (totalNew === 0) {
      toast.error('Please configure questions to add');
      return;
    }

    setIsGenerating(true);
    try {
      if (!questionSet) {
        toast.error('Generate a question set first');
        return;
      }
      const nextSourceIds = Array.from(
        new Set([
          ...(questionSet.sourceDocumentIds || []),
          ...Array.from(selectedPaperIds),
          ...Array.from(selectedNoteIds),
          ...Array.from(selectedUploadIds)
        ])
      );
      const instructions = buildInstructions(questionConfigs);
      const context = await buildContext();
      const questionTypes = enabledConfigs.map((c) => questionTypeToKind[c.type]);
      const avoidText = questions.slice(0, 8).map((q) => q.question).join(' | ');
      const prompt = avoidText
        ? `${instructions} Add new questions that do not repeat: ${avoidText}`
        : instructions;

      const result = await generateQuestionSetWithLLM({
        instructions: prompt,
        context: context || undefined,
        question_count: totalNew,
        question_types: questionTypes
      });

      const newQuestions = result.questions.map(mapApiQuestion);
      const combined = [...questions, ...newQuestions];
      setQuestions(combined);
      setQuestionMarkdown(null);

      if (questionSet) {
        const setId = Number(questionSet.id);
        if (!Number.isFinite(setId)) {
          const savedPayload = await createQuestionSet({
            prompt: questionSet.prompt || instructions,
            questions: combined.map(mapUiQuestionToApi)
          });
          const mapped = mapApiQuestionSet(savedPayload);
          setQuestionSet({
            ...mapped,
            questions: combined,
            sourceDocumentIds: nextSourceIds,
            prompt: questionSet.prompt || instructions
          });
        } else {
          const updatedPayload = await updateQuestionSet(setId, {
            prompt: questionSet.prompt || instructions,
            questions: combined.map(mapUiQuestionToApi)
          });
          const mapped = mapApiQuestionSet(updatedPayload);
          setQuestionSet({
            ...mapped,
            questions: combined,
            sourceDocumentIds: nextSourceIds,
            prompt: questionSet.prompt || instructions
          });
        }
      }

      toast.success(`Added ${newQuestions.length} more questions`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to add questions');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveToNotes = async () => {
    if (!questionSet) return;
    try {
      const title = questionSet.title || 'Question Set';
      const rawMarkdown =
        questionMarkdown || buildQuestionMarkdown(questions, { includeAnswers: true, includeExplanations: true });
      const markdown = stripPromptFromMarkdown(rawMarkdown, questionSet.prompt || '');
      const header = questionSet.prompt ? `Prompt:\n${questionSet.prompt}\n\n` : '';
      const body = `${header}${markdown}`.trim();
      const rawPaperId =
        selectedPaperIds.size === 1 ? Number(Array.from(selectedPaperIds)[0]) : null;
      const paperId = rawPaperId !== null && Number.isFinite(rawPaperId) ? rawPaperId : null;
      const created = await createNote({
        title,
        body,
        paper_id: paperId,
        tags: ['qa_set']
      });
      setNotes((prev) => [mapApiNote(created), ...prev]);
      toast.success('Question set saved to Notes');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to save question set');
    }
  };

  const handleUpdateQuestions = async (nextQuestions: Question[]) => {
    setQuestions(nextQuestions);
    setQuestionMarkdown(null);
    if (!questionSet) return;
    try {
      const setId = Number(questionSet.id);
      if (!Number.isFinite(setId)) {
        const savedPayload = await createQuestionSet({
          prompt: questionSet.prompt || buildInstructions(questionConfigs),
          questions: nextQuestions.map(mapUiQuestionToApi)
        });
        const mapped = mapApiQuestionSet(savedPayload);
        setQuestionSet({
          ...mapped,
          questions: nextQuestions,
          sourceDocumentIds: questionSet.sourceDocumentIds,
          prompt: questionSet.prompt || buildInstructions(questionConfigs)
        });
      } else {
        const updatedPayload = await updateQuestionSet(setId, {
          prompt: questionSet.prompt || undefined,
          questions: nextQuestions.map(mapUiQuestionToApi)
        });
        const mapped = mapApiQuestionSet(updatedPayload);
        setQuestionSet({
          ...mapped,
          questions: nextQuestions,
          sourceDocumentIds: questionSet.sourceDocumentIds,
          prompt: questionSet.prompt
        });
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update question set');
    }
  };

  const handleExport = async (format: string, options: any) => {
    if (!questionSet) return;

    if (format === 'canvas') {
      try {
        const setId = Number(questionSet.id);
        if (!Number.isFinite(setId)) {
          toast.error('Save the question set before exporting to Canvas');
          return;
        }
        const result = await pushQuestionSetToCanvas(setId, {
          title: questionSet.title,
          course_id: options?.courseId?.trim() || undefined,
          time_limit: options?.timeLimit ? Number(options.timeLimit) : undefined,
          publish: options?.publish ?? undefined
        });
        toast.success(`Canvas export completed: ${result.quiz_title}`);
        if (result.quiz_url) {
          window.open(result.quiz_url, '_blank');
        }
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Canvas export failed');
      }
      return;
    }

    if (format === 'markdown' || format === 'txt') {
      const content = buildQuestionMarkdown(questions, options);
      const element = document.createElement('a');
      element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
      element.setAttribute(
        'download',
        `QSet_${questionSet.title.replace(/[^a-z0-9]/gi, '_')}.${format === 'markdown' ? 'md' : 'txt'}`
      );
      element.style.display = 'none';
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      toast.success(`Exported as ${format.toUpperCase()}`);
      return;
    }

    if (format === 'pdf') {
      const includeAnswers = Boolean(options?.includeAnswers);
      const includeExplanations = Boolean(options?.includeExplanations);
      const title = questionSet.title || 'Question Set';
      const meta = [
        { label: 'Questions', value: questions.length },
        { label: 'Includes answers', value: includeAnswers ? 'Yes' : 'No' },
        { label: 'Includes explanations', value: includeExplanations ? 'Yes' : 'No' },
        { label: 'Prompt', value: questionSet.prompt || '' }
      ];
      const content = buildQuestionMarkdown(questions, { includeAnswers, includeExplanations });
      const ok = openPdfWindow(`${title} (${includeAnswers ? 'With Answers' : 'Questions'})`, content, meta);

      if (!includeAnswers && options?.separateAnswerKey) {
        const keyContent = buildQuestionMarkdown(questions, { includeAnswers: true, includeExplanations });
        openPdfWindow(`${title} Answer Key`, keyContent, [
          { label: 'Questions', value: questions.length },
          { label: 'Answer key', value: 'Yes' },
          { label: 'Includes explanations', value: includeExplanations ? 'Yes' : 'No' }
        ]);
      }

      if (ok) {
        toast.success('PDF export ready');
      }
      return;
    }

    if (format === 'json') {
      const payload = {
        title: questionSet.title,
        prompt: questionSet.prompt,
        questions: questions
      };
      const element = document.createElement('a');
      element.setAttribute('href', 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(payload, null, 2)));
      element.setAttribute('download', `QSet_${questionSet.title.replace(/[^a-z0-9]/gi, '_')}.json`);
      element.style.display = 'none';
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      toast.success('Exported as JSON');
      return;
    }

    toast.error(`${format.toUpperCase()} export is not available yet`);
  };

  const togglePaper = (id: string) => {
    const newSet = new Set(selectedPaperIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedPaperIds(newSet);
  };

  const toggleNote = (id: string) => {
    const newSet = new Set(selectedNoteIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedNoteIds(newSet);
  };

  const toggleUpload = (id: string) => {
    const newSet = new Set(selectedUploadIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedUploadIds(newSet);
  };

  const clearSelection = () => {
    setSelectedPaperIds(new Set());
    setSelectedNoteIds(new Set());
    setSelectedUploadIds(new Set());
  };

  return (
    <div className="h-full p-3 sm:p-6 max-w-7xl mx-auto space-y-4 sm:space-y-6 flex flex-col overflow-hidden min-h-0 ia-page-root ia-questions-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Question Sets</h1>
        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
          {questionSet && (
            <>
              <Button variant="outline" onClick={handleSaveToNotes} size="sm" className="flex-1 sm:flex-initial">
                <Save className="h-4 w-4 mr-2" /> <span className="hidden sm:inline">Save to Notes</span><span className="sm:hidden">Save</span>
              </Button>
              <Button onClick={() => setExportDialogOpen(true)} size="sm" className="flex-1 sm:flex-initial">
                <Download className="h-4 w-4 mr-2" /> Export
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden ia-questions-scroll-root">
        <Tabs defaultValue="generate" className="flex-1 flex flex-col min-h-0 overflow-hidden ia-questions-tabs">
          <TabsList className="w-full sm:w-auto">
            <TabsTrigger value="generate" className="flex-1 sm:flex-initial">Generate</TabsTrigger>
            <TabsTrigger value="edit" className="flex-1 sm:flex-initial">Edit Questions</TabsTrigger>
          </TabsList>
          
          <TabsContent value="generate" className="flex-1 mt-4 sm:mt-6 border rounded-xl overflow-hidden bg-background shadow-sm flex flex-col lg:flex-row min-h-0 ia-questions-content">
            {/* Left Panel - Controls */}
            <div className="w-full lg:w-[380px] xl:w-[420px] border-r bg-muted/10 p-5 flex flex-col gap-4 overflow-hidden min-h-0 ia-questions-panel">
              {/* Scrollable Content Area */}
              <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 space-y-4 pr-2 ia-questions-scroll">
                {/* Document Selection */}
                <div className="flex-shrink-0">
                  <DocumentSelector
                    papers={papers}
                    notes={notes}
                    uploads={uploads}
                    selectedPaperIds={selectedPaperIds}
                    selectedNoteIds={selectedNoteIds}
                    selectedUploadIds={selectedUploadIds}
                    onPaperToggle={togglePaper}
                    onNoteToggle={toggleNote}
                    onUploadToggle={toggleUpload}
                    onUpload={handleUploadFiles}
                    onClearSelection={clearSelection}
                    onPaperSearchChange={setPaperSearchQuery}
                    isUploading={isUploading}
                  />
                </div>

                {/* Question Configuration */}
                <div className="flex-shrink-0">
                  <QuestionConfigPanel
                    configs={questionConfigs}
                    onChange={setQuestionConfigs}
                  />
                </div>
              </div>

              {/* Fixed Bottom Section - Always Visible */}
              <div className="flex-shrink-0 space-y-3 pt-2 border-t bg-muted/10 -mx-5 px-5 pb-0">
                {/* Model Selection */}
                <div className="space-y-2">
                  <h3 className="font-semibold text-sm">Model</h3>
                  <Button variant="outline" size="sm" className="w-full h-9 text-xs justify-start">
                    ⚡ Qwen (Local) - Recommended
                  </Button>
                </div>
                
                {/* Generate Button */}
                <div className="space-y-2">
                  <Button
                    onClick={handleGenerate}
                    disabled={
                      isGenerating ||
                      (selectedPaperIds.size === 0 &&
                        selectedNoteIds.size === 0 &&
                        selectedUploadIds.size === 0)
                    }
                    className="w-full"
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Generate Questions
                      </>
                    )}
                  </Button>

                  {questions.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs text-muted-foreground text-center">
                        Current Set: {questions.length} questions
                      </div>
                      <Button
                        variant="outline"
                        onClick={handleAddMore}
                        disabled={isGenerating}
                        className="w-full"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Add More Questions
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Right Panel - Preview */}
            <div className="flex-1 bg-background flex flex-col min-h-0">
              <div className="p-3 border-b bg-muted/5 flex justify-between items-center text-xs text-muted-foreground">
                <span>Preview</span>
                <span className="hidden sm:inline">Markdown</span>
              </div>
              <ScrollArea className="flex-1 p-4 sm:p-8">
                {questions.length > 0 ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    {questions.map((q, idx) => (
                      <div key={q.id} className="mb-6">
                        <h3>Question {idx + 1}</h3>
                        <p>{q.question}</p>
                        {q.options && (
                          <ul>
                            {q.options.map((opt, optIdx) => (
                              <li key={optIdx}>
                                {String.fromCharCode(65 + optIdx)}) {opt}
                                {optIdx === q.correctAnswer && ' ✓'}
                              </li>
                            ))}
                          </ul>
                        )}
                        {q.explanation && (
                          <div className="bg-muted/50 p-2 rounded text-sm">
                            <strong>Explanation:</strong> {q.explanation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50">
                    <p>Select source materials and configure questions, then click generate</p>
                  </div>
                )}
              </ScrollArea>
            </div>
          </TabsContent>

          <TabsContent value="edit" className="flex-1 mt-4 sm:mt-6 min-h-0 overflow-auto">
            {questions.length > 0 ? (
              <QuestionEditor questions={questions} onUpdate={handleUpdateQuestions} />
            ) : (
              <Card className="h-full flex items-center justify-center min-h-[400px]">
                <p className="text-muted-foreground text-sm sm:text-base">Generate questions first to edit them</p>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>

      <ExportQuestionSetDialog
        open={exportDialogOpen}
        onOpenChange={setExportDialogOpen}
        onExport={handleExport}
        questionSet={questionSet}
      />
    </div>
  );
}
