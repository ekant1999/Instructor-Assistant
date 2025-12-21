import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, RefreshCw, Save, Plus, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { QuestionConfigPanel, QuestionTypeConfig } from './QuestionConfigPanel';
import { QuestionEditor } from './QuestionEditor';
import { DocumentSelector } from './DocumentSelector';
import { ExportQuestionSetDialog } from './ExportQuestionSetDialog';
import { Question, QuestionSet, Paper, Document } from '@/shared/types';
import { toast } from 'sonner';

export default function EnhancedQuestionSetsPage() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [questionSet, setQuestionSet] = useState<QuestionSet | null>(null);
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set(['1']));
  const [selectedNoteIds, setSelectedNoteIds] = useState<Set<string>>(new Set());
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  
  // Mock data
  const papers: Paper[] = [
    { id: '1', title: 'Attention Is All You Need', year: '2017', source: 'ArXiv', authors: 'Vaswani et al.' },
    { id: '2', title: 'BERT: Pre-training of Deep Bidirectional...', year: '2018', source: 'ArXiv' },
    { id: '3', title: 'GPT-4 Technical Report', year: '2023', source: 'OpenAI' }
  ];

  const notes: Document[] = [
    {
      id: '1',
      type: 'summary',
      title: 'Summary: Transformers',
      content: 'Key points about transformers...',
      tags: ['transformer'],
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
  ];

  const [questionConfigs, setQuestionConfigs] = useState<QuestionTypeConfig[]>([
    { type: 'multiple-choice', enabled: true, count: 5, options: { numOptions: 4 } },
    { type: 'true-false', enabled: true, count: 3, options: { includeExplanation: true } },
    { type: 'short-answer', enabled: false, count: 2, options: { expectedLength: 'sentence' } },
    { type: 'essay', enabled: false, count: 1, options: { wordCountRange: { min: 200, max: 500 } } }
  ]);

  const handleGenerate = async () => {
    if (selectedPaperIds.size === 0 && selectedNoteIds.size === 0) {
      toast.error('Please select at least one source document');
      return;
    }

    const enabledConfigs = questionConfigs.filter(c => c.enabled);
    const totalQuestions = enabledConfigs.reduce((sum, c) => sum + c.count, 0);

    if (totalQuestions === 0) {
      toast.error('Please enable at least one question type');
      return;
    }

    setIsGenerating(true);
    
    // Simulate generation
    const generatedQuestions: Question[] = [];
    let questionNum = 1;

    for (const config of enabledConfigs) {
      for (let i = 0; i < config.count; i++) {
        await new Promise(r => setTimeout(r, 500));
        
        const question: Question = {
          id: Math.random().toString(),
          type: config.type,
          question: `${config.type} question ${questionNum}: What is the primary mechanism?`,
          correctAnswer: config.type === 'multiple-choice' ? 1 : 'Answer',
          options: config.type === 'multiple-choice' 
            ? ['Option A', 'Option B (Correct)', 'Option C', 'Option D']
            : undefined,
          explanation: config.options?.includeExplanation ? 'This is the explanation.' : undefined,
          difficulty: 'medium'
        };
        
        generatedQuestions.push(question);
        questionNum++;
        setQuestions([...generatedQuestions]);
      }
    }

    const newQuestionSet: QuestionSet = {
      id: Math.random().toString(),
      title: `Q&A Set: ${Array.from(selectedPaperIds).length} papers, ${Array.from(selectedNoteIds).length} notes`,
      questions: generatedQuestions,
      sourceDocumentIds: [...Array.from(selectedPaperIds), ...Array.from(selectedNoteIds)],
      agent: 'Qwen',
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    setQuestionSet(newQuestionSet);
    setIsGenerating(false);
    toast.success(`Generated ${generatedQuestions.length} questions`);
  };

  const handleAddMore = async () => {
    const enabledConfigs = questionConfigs.filter(c => c.enabled);
    const totalNew = enabledConfigs.reduce((sum, c) => sum + c.count, 0);

    if (totalNew === 0) {
      toast.error('Please configure questions to add');
      return;
    }

    setIsGenerating(true);
    const newQuestions: Question[] = [];
    let questionNum = questions.length + 1;

    for (const config of enabledConfigs) {
      for (let i = 0; i < config.count; i++) {
        await new Promise(r => setTimeout(r, 500));
        
        const question: Question = {
          id: Math.random().toString(),
          type: config.type,
          question: `Additional ${config.type} question ${questionNum}`,
          correctAnswer: config.type === 'multiple-choice' ? 0 : 'Answer',
          options: config.type === 'multiple-choice' 
            ? ['Option A (Correct)', 'Option B', 'Option C', 'Option D']
            : undefined,
          explanation: config.options?.includeExplanation ? 'Explanation for new question.' : undefined,
          difficulty: 'medium'
        };
        
        newQuestions.push(question);
        questionNum++;
      }
    }

    setQuestions([...questions, ...newQuestions]);
    if (questionSet) {
      setQuestionSet({
        ...questionSet,
        questions: [...questions, ...newQuestions],
        updatedAt: Date.now()
      });
    }
    setIsGenerating(false);
    toast.success(`Added ${newQuestions.length} more questions`);
  };

  const handleSaveToNotes = () => {
    if (!questionSet) return;
    toast.success('Question set saved to Notes');
    // In real app, would save to Notes section
  };

  const handleExport = (format: string, options: any) => {
    if (!questionSet) return;
    
    // In real app, would call API to generate export
    toast.success(`Exporting as ${format.toUpperCase()}...`);
    
    if (format === 'markdown' || format === 'txt') {
      const content = questions.map((q, idx) => {
        let text = `### Question ${idx + 1}\n\n${q.question}\n\n`;
        if (q.options) {
          q.options.forEach((opt, optIdx) => {
            text += `${String.fromCharCode(65 + optIdx)}) ${opt}\n`;
          });
        }
        if (options.includeAnswers) {
          text += `\n**Answer:** ${q.correctAnswer}\n`;
        }
        if (options.includeExplanations && q.explanation) {
          text += `\n**Explanation:** ${q.explanation}\n`;
        }
        return text;
      }).join('\n\n---\n\n');

      const element = document.createElement('a');
      element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
      element.setAttribute('download', `QSet_${questionSet.title.replace(/[^a-z0-9]/gi, '_')}.${format === 'markdown' ? 'md' : 'txt'}`);
      element.style.display = 'none';
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    }
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
            <QuestionEditor questions={questions} onUpdate={setQuestions} />
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

