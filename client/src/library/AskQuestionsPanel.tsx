import React, { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Loader2, MessageSquare, Trash2 } from 'lucide-react';
import { clearPaperRagQna, createPaperRagQna, deletePaperRagQna, listPaperRagQna, ragQuery } from '@/lib/api';
import { ApiRagContextInfo, ApiRagQnaItem } from '@/lib/api-types';
import { Paper } from '@/shared/types';
import { toast } from 'sonner';

interface AskQuestionsPanelProps {
  selectedPaper: Paper;
  papers: Paper[];
}

interface AskEntry {
  id: string;
  question: string;
  answer: string;
  sources: ApiRagContextInfo[];
  scope?: string;
  provider?: string;
  createdAt: number;
}

const statusCopy: Record<string, { label: string; variant: "default" | "secondary" | "outline" | "destructive" }> = {
  done: { label: "Indexed", variant: "secondary" },
  processing: { label: "Indexing", variant: "outline" },
  queued: { label: "Queued", variant: "outline" },
  error: { label: "Error", variant: "destructive" },
};

export function AskQuestionsPanel({ selectedPaper, papers }: AskQuestionsPanelProps) {
  const [question, setQuestion] = useState('');
  const [useAllPapers, setUseAllPapers] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<AskEntry[]>([]);

  const indexedPapers = useMemo(
    () => papers.filter((paper) => paper.ragStatus === 'done'),
    [papers]
  );

  const selectedStatus = statusCopy[selectedPaper.ragStatus || ''] ?? { label: "Unknown", variant: "outline" };
  const hasIndexed = useAllPapers ? indexedPapers.length > 0 : selectedPaper.ragStatus === 'done';
  const showPartialWarning = useAllPapers && indexedPapers.length > 0 && indexedPapers.length < papers.length;

  const mapRagQnaEntry = (item: ApiRagQnaItem): AskEntry => {
    const createdAt = item.created_at ? Date.parse(item.created_at) : Date.now();
    return {
      id: String(item.id),
      question: item.question,
      answer: item.answer,
      sources: item.sources || [],
      scope: item.scope || 'selected',
      provider: item.provider || 'local',
      createdAt: Number.isNaN(createdAt) ? Date.now() : createdAt,
    };
  };

  useEffect(() => {
    let cancelled = false;
    async function loadHistory() {
      try {
        const entries = await listPaperRagQna(Number(selectedPaper.id));
        if (!cancelled) {
          setHistory(entries.map(mapRagQnaEntry));
        }
      } catch (error) {
        if (!cancelled) {
          toast.error(error instanceof Error ? error.message : 'Failed to load Q&A history');
        }
      }
    }
    setQuestion('');
    setUseAllPapers(false);
    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [selectedPaper.id]);

  const handleAsk = async () => {
    if (!question.trim()) {
      toast.error('Please enter a question');
      return;
    }
    if (!hasIndexed) {
      toast.error('Indexing is not complete yet. Please wait for ingestion to finish.');
      return;
    }
    setIsLoading(true);
    try {
      const payload = {
        question,
        k: 8,
        provider: 'local',
        paper_ids: useAllPapers ? undefined : [Number(selectedPaper.id)],
      };
      const result = await ragQuery(payload);
      const scope = useAllPapers ? 'all' : 'selected';
      try {
        const stored = await createPaperRagQna(Number(selectedPaper.id), {
          question,
          answer: result.answer,
          sources: result.context || [],
          scope,
          provider: 'local',
        });
        setHistory((prev) => [mapRagQnaEntry(stored), ...prev]);
      } catch (error) {
        const entry: AskEntry = {
          id: `${Date.now()}`,
          question,
          answer: result.answer,
          sources: result.context || [],
          scope,
          provider: 'local',
          createdAt: Date.now(),
        };
        setHistory((prev) => [entry, ...prev]);
        toast.error(error instanceof Error ? error.message : 'Failed to save Q&A history');
      } finally {
        setQuestion('');
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to answer question');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteEntry = async (entryId: string) => {
    try {
      await deletePaperRagQna(Number(selectedPaper.id), Number(entryId));
      setHistory((prev) => prev.filter((item) => item.id !== entryId));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete Q&A entry');
    }
  };

  const handleClearHistory = async () => {
    if (history.length === 0) return;
    const confirmed = window.confirm('Clear all Q&A history for this paper?');
    if (!confirmed) return;
    try {
      await clearPaperRagQna(Number(selectedPaper.id));
      setHistory([]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to clear Q&A history');
    }
  };

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-5 max-w-3xl">
        <Card className="p-4 space-y-4">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Scope</Label>
              <div className="flex items-center gap-2">
                <Label className="text-xs text-muted-foreground">All papers</Label>
                <Switch checked={useAllPapers} onCheckedChange={setUseAllPapers} />
              </div>
            </div>
            {!useAllPapers && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">Selected paper:</span>
                <span className="font-medium">{selectedPaper.title || 'Untitled paper'}</span>
                <Badge variant={selectedStatus.variant}>{selectedStatus.label}</Badge>
              </div>
            )}
            {useAllPapers && (
              <div className="text-xs text-muted-foreground">
                Using {indexedPapers.length} indexed paper(s) out of {papers.length}.
              </div>
            )}
            {showPartialWarning && (
              <div className="text-xs text-amber-500">
                Some papers are still indexing. Answers will use only indexed papers.
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium">Ask a question</Label>
            <Textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about methods, results, or any details from the paper..."
              className="min-h-[110px]"
            />
          </div>

          <Button onClick={handleAsk} disabled={isLoading || !hasIndexed} className="w-full h-10">
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Answering...
              </>
            ) : (
              <>
                <MessageSquare className="h-4 w-4 mr-2" />
                Ask question
              </>
            )}
          </Button>
        </Card>

        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">Q&A History</div>
          <Button variant="ghost" size="sm" onClick={handleClearHistory} disabled={history.length === 0}>
            Clear history
          </Button>
        </div>

        {history.length === 0 && (
          <Card className="p-4 text-sm text-muted-foreground">
            Ask a question to see an answer grounded in the indexed paper chunks.
          </Card>
        )}

        {history.map((entry) => (
          <Card key={entry.id} className="p-4 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="text-sm font-medium">Q: {entry.question}</div>
              <Button variant="ghost" size="icon" onClick={() => handleDeleteEntry(entry.id)}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {entry.scope === 'all' && <Badge variant="outline">All papers</Badge>}
              {entry.provider && <Badge variant="secondary">{entry.provider}</Badge>}
            </div>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown>{entry.answer}</ReactMarkdown>
            </div>
            {entry.sources.length > 0 && (
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="font-medium text-foreground">Sources</div>
                {entry.sources.map((source) => (
                  <div key={`${entry.id}-${source.index}`} className="flex flex-col">
                    <span>
                      [{source.index}]{' '}
                      {source.kind === 'figure'
                        ? `${source.figure_number ? `Figure ${source.figure_number}` : 'Figure'} — ${source.paper_title || source.paper || 'Unknown paper'}`
                        : source.paper_title || source.paper || 'Unknown paper'}
                    </span>
                    {source.caption && source.kind === 'figure' && (
                      <span className="truncate">{source.caption}</span>
                    )}
                    {source.source && source.kind !== 'figure' && (
                      <span className="truncate">{source.source}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </ScrollArea>
  );
}
