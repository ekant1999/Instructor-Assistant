import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, RefreshCw, Save, Plus, Download } from 'lucide-react';
import { QuestionConfigPanel, QuestionTypeConfig } from './QuestionConfigPanel';
import { QuestionEditor } from './QuestionEditor';
import { DocumentSelector } from './DocumentSelector';
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
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set());
  const [selectedNoteIds, setSelectedNoteIds] = useState<Set<string>>(new Set());
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  
  useEffect(() => {
    let isMounted = true;
    async function loadDocs() {
      setIsLoadingDocs(true);
      try {
        const [paperRows, noteRows] = await Promise.all([listPapers(), listNotes()]);
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
  }, []);

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
    const maxTotalChars = 60000;
    const paperIds = Array.from(selectedPaperIds)
      .map((id) => Number(id))
      .filter((id) => Number.isFinite(id));
    const noteIds = Array.from(selectedNoteIds);

    const paperById = new Map(papers.map((p) => [p.id, p]));
    const noteById = new Map(notes.map((n) => [n.id, n]));

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

    const combined = [...paperParts, ...noteParts].filter(Boolean).join('\n\n---\n\n');
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

  const handleGenerate = async () => {
    if (selectedPaperIds.size === 0 && selectedNoteIds.size === 0) {
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
          sourceDocumentIds: [...Array.from(selectedPaperIds), ...Array.from(selectedNoteIds)],
          prompt: instructions
        };
      } catch (error) {
        toast.error('Generated questions but failed to save the set');
      }

      setQuestionSet(
        savedSet || {
          id: Math.random().toString(),
          title: `Q&A Set: ${Array.from(selectedPaperIds).length} papers, ${Array.from(selectedNoteIds).length} notes`,
          questions: generatedQuestions,
          sourceDocumentIds: [...Array.from(selectedPaperIds), ...Array.from(selectedNoteIds)],
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
            sourceDocumentIds: questionSet.sourceDocumentIds,
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
            sourceDocumentIds: questionSet.sourceDocumentIds,
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
      const markdown = questionMarkdown || buildQuestionMarkdown(questions, { includeAnswers: true, includeExplanations: true });
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

  const clearSelection = () => {
    setSelectedPaperIds(new Set());
    setSelectedNoteIds(new Set());
  };

  return (
    <div className="h-full p-3 sm:p-6 max-w-7xl mx-auto space-y-4 sm:space-y-6 flex flex-col overflow-hidden">
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

      <Tabs defaultValue="generate" className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <TabsList className="w-full sm:w-auto">
          <TabsTrigger value="generate" className="flex-1 sm:flex-initial">Generate</TabsTrigger>
          <TabsTrigger value="edit" className="flex-1 sm:flex-initial">Edit Questions</TabsTrigger>
        </TabsList>
        
        <TabsContent value="generate" className="flex-1 mt-4 sm:mt-6 border rounded-xl overflow-hidden bg-background shadow-sm flex flex-col lg:flex-row min-h-0">
          {/* Left Panel - Controls */}
          <div className="w-full lg:w-[380px] xl:w-[420px] border-r bg-muted/10 p-5 flex flex-col gap-4 overflow-hidden min-h-0">
            {/* Scrollable Content Area */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 space-y-4 pr-2">
              {/* Document Selection */}
              <div className="flex-shrink-0">
                <DocumentSelector
                  papers={papers}
                  notes={notes}
                  selectedPaperIds={selectedPaperIds}
                  selectedNoteIds={selectedNoteIds}
                  onPaperToggle={togglePaper}
                  onNoteToggle={toggleNote}
                  onClearSelection={clearSelection}
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
                  disabled={isGenerating || (selectedPaperIds.size === 0 && selectedNoteIds.size === 0)}
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

      <ExportQuestionSetDialog
        open={exportDialogOpen}
        onOpenChange={setExportDialogOpen}
        onExport={handleExport}
        questionSet={questionSet}
      />
    </div>
  );
}
