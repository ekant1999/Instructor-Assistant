import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  API_BASE,
  chatPaperIngestionSection,
  getPaperIngestionInfo,
  getPaperIngestionSectionDetail,
  withNgrokSkipParam,
} from '@/lib/api';
import {
  ApiPaperEquationInfo,
  ApiPaperFigureInfo,
  ApiPaperIngestionInfo,
  ApiPaperIngestionSectionDetail,
  ApiPaperTableInfo,
} from '@/lib/api-types';
import { Loader2 } from 'lucide-react';

interface SearchResultContextPanelProps {
  paperId: number;
  paperTitle: string;
  query: string;
  matchPageNo?: number;
  matchBlockIndex?: number;
  matchSectionCanonical?: string;
  matchText?: string;
}

interface QaTurn {
  id: string;
  question: string;
  answer: string;
  error?: string;
  contextChars?: number;
  sourceBlockCount?: number;
  chunkCount?: number;
  pages?: number[];
}

function normalizeCanonical(value?: string | null): string {
  const normalized = String(value || '').trim().toLowerCase();
  return normalized || 'other';
}

function tokenize(value: string): string[] {
  return Array.from(
    new Set(
      value
        .toLowerCase()
        .split(/[^a-z0-9]+/g)
        .map((token) => token.trim())
        .filter((token) => token.length >= 3),
    ),
  );
}

function overlapScore(tokens: string[], text: string): number {
  if (!tokens.length || !text) return 0;
  const haystack = text.toLowerCase();
  return tokens.reduce((score, token) => score + (haystack.includes(token) ? 1 : 0), 0);
}

function normalizeLooseText(value: string): string {
  return value
    .toLowerCase()
    .replace(/[‐-―]/g, '-')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function buildFigureUrl(image: ApiPaperFigureInfo): string {
  const apiRoot = API_BASE.replace(/\/api\/?$/, '');
  return withNgrokSkipParam(`${apiRoot}${image.url}`);
}

function buildEquationUrl(equation: ApiPaperEquationInfo): string | null {
  if (!equation.url) return null;
  const apiRoot = API_BASE.replace(/\/api\/?$/, '');
  return withNgrokSkipParam(`${apiRoot}${equation.url}`);
}

function resolveCanonicalFromMatch(
  data: ApiPaperIngestionInfo,
  query: string,
  matchText?: string,
  pageNo?: number,
  blockIndex?: number,
  matchSectionCanonical?: string,
): { canonical: string | null; reason: string } {
  const directCanonical = normalizeCanonical(matchSectionCanonical);
  const hasDirectCanonical = Boolean(directCanonical && directCanonical !== 'other');
  const candidateTokens = tokenize(matchText || query);
  const scoreTokens = candidateTokens.length ? candidateTokens : tokenize(query);

  // If backend already resolved the exact matched source block's section, trust it first.
  if (hasDirectCanonical) {
    return { canonical: directCanonical, reason: 'match_section' };
  }

  if (pageNo) {
    const chunksOnPage = data.chunks.filter((chunk) => chunk.page_no === pageNo);

    if (typeof blockIndex === 'number') {
      for (const chunk of chunksOnPage) {
        const metadata = chunk.metadata && typeof chunk.metadata === 'object' ? chunk.metadata : {};
        const sourceBlocks = Array.isArray((metadata as Record<string, unknown>).blocks)
          ? ((metadata as Record<string, unknown>).blocks as Record<string, unknown>[])
          : [];
        for (const sourceBlock of sourceBlocks) {
          const sourcePageRaw = sourceBlock['page_no'] as number | string | undefined;
          const sourceBlockIndexRaw = sourceBlock['block_index'] as number | string | undefined;
          const sourcePageNo: number = Number(sourcePageRaw ?? pageNo);
          const sourceBlockIndex: number = Number(sourceBlockIndexRaw ?? -1);
          if (sourcePageNo !== pageNo || sourceBlockIndex !== blockIndex) {
            continue;
          }
          const sourceMeta = sourceBlock['metadata'];
          const blockMeta = sourceMeta && typeof sourceMeta === 'object'
            ? (sourceMeta as Record<string, unknown>)
            : {};
          const blockCanonical = normalizeCanonical(
            String(
              blockMeta.section_canonical ??
              blockMeta.section_primary ??
              chunk.section_primary ??
              'other',
            ),
          );
          return { canonical: blockCanonical, reason: 'matched_block' };
        }
      }
    }

    const normalizedNeedle = normalizeLooseText(matchText || query);
    if (normalizedNeedle) {
      let bestFromText: { canonical: string; score: number } | null = null;
      for (const chunk of chunksOnPage) {
        const metadata = chunk.metadata && typeof chunk.metadata === 'object' ? chunk.metadata : {};
        const sourceBlocks = Array.isArray((metadata as Record<string, unknown>).blocks)
          ? ((metadata as Record<string, unknown>).blocks as Record<string, unknown>[])
          : [];
        for (const sourceBlock of sourceBlocks) {
          const sourcePageRaw = sourceBlock['page_no'] as number | string | undefined;
          const sourcePageNo: number = Number(sourcePageRaw ?? pageNo);
          if (sourcePageNo !== pageNo) continue;

          const sourceText = String(sourceBlock['text'] || '');
          if (!sourceText) continue;
          const looseSourceText = normalizeLooseText(sourceText);
          const tokenScore = overlapScore(scoreTokens, looseSourceText);

          if (looseSourceText.includes(normalizedNeedle)) {
            const sourceMeta = sourceBlock['metadata'];
            const blockMeta = sourceMeta && typeof sourceMeta === 'object'
              ? (sourceMeta as Record<string, unknown>)
              : {};
            const blockCanonical = normalizeCanonical(
              String(
                blockMeta.section_canonical ??
                blockMeta.section_primary ??
                chunk.section_primary ??
                'other',
              ),
            );
            return { canonical: blockCanonical, reason: 'matched_text_block' };
          }

          if (tokenScore > 0) {
            const sourceMeta = sourceBlock['metadata'];
            const blockMeta = sourceMeta && typeof sourceMeta === 'object'
              ? (sourceMeta as Record<string, unknown>)
              : {};
            const blockCanonical = normalizeCanonical(
              String(
                blockMeta.section_canonical ??
                blockMeta.section_primary ??
                chunk.section_primary ??
                'other',
              ),
            );
            if (!bestFromText || tokenScore > bestFromText.score) {
              bestFromText = { canonical: blockCanonical, score: tokenScore };
            }
          }
        }
      }
      if (bestFromText) {
        return { canonical: bestFromText.canonical, reason: 'matched_text_overlap' };
      }
    }

    if (chunksOnPage.length > 0) {
      let bestCanonical: string | null = null;
      let bestScore = -1;
      for (const chunk of chunksOnPage) {
        const canonical = normalizeCanonical(chunk.section_primary);
        const haystack = [
          chunk.text_preview || '',
          canonical,
          ...(Array.isArray(chunk.section_titles) ? chunk.section_titles : []),
        ].join(' ');
        const score = overlapScore(scoreTokens, haystack) + (chunk.section_primary ? 1 : 0);
        if (score > bestScore) {
          bestScore = score;
          bestCanonical = canonical;
        }
      }
      if (bestCanonical) {
        return { canonical: bestCanonical, reason: 'matched_chunk' };
      }
    }

    const sectionOnPage = data.sections.find((section) => section.pages.includes(pageNo));
    if (sectionOnPage) {
      return { canonical: normalizeCanonical(sectionOnPage.canonical), reason: 'page_bucket' };
    }
  }

  if (data.sections.length > 0 && scoreTokens.length > 0) {
    const scored = data.sections
      .map((section) => {
        const haystack = `${section.canonical} ${section.title_samples.join(' ')}`;
        return {
          canonical: normalizeCanonical(section.canonical),
          score: overlapScore(scoreTokens, haystack),
        };
      })
      .sort((a, b) => b.score - a.score);
    if (scored[0]?.score > 0) {
      return { canonical: scored[0].canonical, reason: 'title_overlap' };
    }
  }

  if (data.sections.length > 0) {
    return { canonical: normalizeCanonical(data.sections[0].canonical), reason: 'first_section' };
  }
  return { canonical: null, reason: 'none' };
}

function normalizeTablePreview(table: ApiPaperTableInfo): {
  headers: string[];
  rows: string[][];
} {
  const previewHeaders = Array.isArray(table.headers_preview) ? table.headers_preview : [];
  const previewRows = Array.isArray(table.rows_preview) ? table.rows_preview : [];
  const colCount = Math.max(
    table.n_cols || 0,
    previewHeaders.length,
    ...previewRows.map((row) => row.length),
  );
  const headers = Array.from({ length: colCount }, (_, idx) => {
    const value = previewHeaders[idx] || '';
    return value.trim() || `col_${idx + 1}`;
  });
  const rows = previewRows.map((row) => {
    if (row.length >= colCount) return row.slice(0, colCount);
    return [...row, ...Array(colCount - row.length).fill('')];
  });
  return { headers, rows };
}

function canonicalLabel(canonical: string): string {
  return canonical.replace(/_/g, ' ');
}

export function SearchResultContextPanel({
  paperId,
  paperTitle,
  query,
  matchPageNo,
  matchBlockIndex,
  matchSectionCanonical,
  matchText,
}: SearchResultContextPanelProps) {
  const [activeTab, setActiveTab] = React.useState<'results' | 'ask'>('results');
  const [ingestionInfo, setIngestionInfo] = React.useState<ApiPaperIngestionInfo | null>(null);
  const [loadingInfo, setLoadingInfo] = React.useState(false);
  const [infoError, setInfoError] = React.useState<string | null>(null);
  const [selectedCanonical, setSelectedCanonical] = React.useState<string | null>(null);
  const [detailsByCanonical, setDetailsByCanonical] = React.useState<
    Record<string, ApiPaperIngestionSectionDetail>
  >({});
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [detailError, setDetailError] = React.useState<string | null>(null);
  const [questionDraft, setQuestionDraft] = React.useState('');
  const [asking, setAsking] = React.useState(false);
  const [qaByCanonical, setQaByCanonical] = React.useState<Record<string, QaTurn[]>>({});

  React.useEffect(() => {
    let cancelled = false;
    setLoadingInfo(true);
    setInfoError(null);
    setIngestionInfo(null);
    setSelectedCanonical(null);
    setDetailsByCanonical({});
    setDetailError(null);
    async function loadIngestionInfo() {
      try {
        const data = await getPaperIngestionInfo(paperId, 1000);
        if (!cancelled) {
          setIngestionInfo(data);
        }
      } catch (error) {
        if (!cancelled) {
          setInfoError(error instanceof Error ? error.message : 'Failed to load search context');
        }
      } finally {
        if (!cancelled) {
          setLoadingInfo(false);
        }
      }
    }
    loadIngestionInfo();
    return () => {
      cancelled = true;
    };
  }, [paperId]);

  const resolved = React.useMemo(() => {
    if (!ingestionInfo) {
      return { canonical: null as string | null, reason: 'none' };
    }
    return resolveCanonicalFromMatch(
      ingestionInfo,
      query,
      matchText,
      matchPageNo,
      matchBlockIndex,
      matchSectionCanonical,
    );
  }, [ingestionInfo, query, matchText, matchPageNo, matchBlockIndex, matchSectionCanonical]);

  React.useEffect(() => {
    if (!ingestionInfo) return;
    const knownCanonicals = new Set(ingestionInfo.sections.map((section) => normalizeCanonical(section.canonical)));
    setSelectedCanonical((current) => {
      if (current && knownCanonicals.has(current)) return current;
      return resolved.canonical;
    });
  }, [ingestionInfo, resolved.canonical]);

  const activeDetail = selectedCanonical ? detailsByCanonical[selectedCanonical] : undefined;
  React.useEffect(() => {
    if (!selectedCanonical) return;
    if (activeDetail) return;
    const canonical = selectedCanonical;
    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    async function loadSectionDetail() {
      try {
        const detail = await getPaperIngestionSectionDetail(paperId, canonical, 350000);
        if (!cancelled) {
          setDetailsByCanonical((prev) => ({ ...prev, [canonical]: detail }));
        }
      } catch (error) {
        if (!cancelled) {
          setDetailError(error instanceof Error ? error.message : 'Failed to load section detail');
        }
      } finally {
        if (!cancelled) {
          setDetailLoading(false);
        }
      }
    }
    loadSectionDetail();
    return () => {
      cancelled = true;
    };
  }, [paperId, selectedCanonical, activeDetail]);

  const pageCandidateSections = React.useMemo(() => {
    if (!ingestionInfo || !matchPageNo) return [];
    return ingestionInfo.sections.filter((section) => section.pages.includes(matchPageNo));
  }, [ingestionInfo, matchPageNo]);

  const tablesInSection = React.useMemo(() => {
    if (!ingestionInfo || !selectedCanonical) return [];
    return (ingestionInfo.tables || [])
      .filter((table) => normalizeCanonical(table.section_canonical) === selectedCanonical)
      .sort((a, b) => {
        const pageDiff = a.page_no - b.page_no;
        if (pageDiff !== 0) return pageDiff;
        return a.id - b.id;
      });
  }, [ingestionInfo, selectedCanonical]);

  const equationsInSection = React.useMemo(() => {
    if (!selectedCanonical) return [];
    const fromDetail = Array.isArray(activeDetail?.equations) ? activeDetail.equations : [];
    if (fromDetail.length > 0) {
      return [...fromDetail].sort((a, b) => {
        const pageDiff = (a.page_no || 0) - (b.page_no || 0);
        if (pageDiff !== 0) return pageDiff;
        return (a.id || 0) - (b.id || 0);
      });
    }
    if (!ingestionInfo) return [];
    return (ingestionInfo.equations || [])
      .filter((equation) => normalizeCanonical(equation.section_canonical) === selectedCanonical)
      .sort((a, b) => {
        const pageDiff = (a.page_no || 0) - (b.page_no || 0);
        if (pageDiff !== 0) return pageDiff;
        return (a.id || 0) - (b.id || 0);
      });
  }, [activeDetail, ingestionInfo, selectedCanonical]);

  const qaTurns = React.useMemo(() => {
    if (!selectedCanonical) return [];
    return qaByCanonical[selectedCanonical] || [];
  }, [qaByCanonical, selectedCanonical]);

  const handleAskQuestion = React.useCallback(async () => {
    if (!selectedCanonical) return;
    const question = questionDraft.trim();
    if (!question || asking) return;

    const turnId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const optimisticTurn: QaTurn = {
      id: turnId,
      question,
      answer: '',
    };
    setQuestionDraft('');
    setAsking(true);
    setQaByCanonical((prev) => {
      const existing = prev[selectedCanonical] || [];
      return {
        ...prev,
        [selectedCanonical]: [...existing, optimisticTurn],
      };
    });

    try {
      const response = await chatPaperIngestionSection(paperId, selectedCanonical, question);
      setQaByCanonical((prev) => {
        const existing = prev[selectedCanonical] || [];
        return {
          ...prev,
          [selectedCanonical]: existing.map((turn) =>
            turn.id !== turnId
              ? turn
              : {
                  ...turn,
                  answer: response.answer || 'No answer generated.',
                  contextChars: response.context_chars,
                  sourceBlockCount: response.source_block_count,
                  chunkCount: response.chunk_count,
                  pages: response.pages,
                },
          ),
        };
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to get an answer for this section.';
      setQaByCanonical((prev) => {
        const existing = prev[selectedCanonical] || [];
        return {
          ...prev,
          [selectedCanonical]: existing.map((turn) =>
            turn.id !== turnId
              ? turn
              : {
                  ...turn,
                  answer: '',
                  error: message,
                },
          ),
        };
      });
    } finally {
      setAsking(false);
    }
  }, [asking, paperId, questionDraft, selectedCanonical]);

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="border-b px-4 py-3 bg-muted/10">
        <div className="text-sm font-semibold">Search Context</div>
        <div className="text-xs text-muted-foreground mt-1 line-clamp-2">{paperTitle}</div>
        <div className="text-xs text-muted-foreground mt-1">Query: {query || 'n/a'}</div>
      </div>

      {loadingInfo && (
        <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
          Loading search context...
        </div>
      )}

      {!loadingInfo && infoError && (
        <div className="flex-1 flex items-center justify-center text-sm text-destructive px-4 text-center">
          {infoError}
        </div>
      )}

      {!loadingInfo && !infoError && !ingestionInfo && (
        <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
          No ingestion context available.
        </div>
      )}

      {!loadingInfo && !infoError && ingestionInfo && (
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value === 'ask' ? 'ask' : 'results')}
          className="flex-1 min-h-0 flex flex-col"
        >
          <div className="px-3 pt-3">
            <TabsList className="w-full h-auto grid grid-cols-2 gap-1">
              <TabsTrigger value="results" className="text-xs">
                Search Results
              </TabsTrigger>
              <TabsTrigger value="ask" className="text-xs">
                Ask Questions
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="results" className="mt-2 flex-1 min-h-0 px-3 pb-3 overflow-hidden">
            <ScrollArea className="h-full pr-2">
              <div className="space-y-3">
                <Card className="p-3 bg-muted/10">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">
                      Section: {selectedCanonical ? canonicalLabel(selectedCanonical) : 'unresolved'}
                    </Badge>
                    {matchPageNo ? <Badge variant="outline">Page {matchPageNo}</Badge> : null}
                  </div>

                  {pageCandidateSections.length > 1 && (
                    <div className="mt-3">
                      <div className="text-[11px] text-muted-foreground mb-1">Sections on this page</div>
                      <div className="flex flex-wrap gap-2">
                        {pageCandidateSections.map((section) => {
                          const canonical = normalizeCanonical(section.canonical);
                          const active = selectedCanonical === canonical;
                          return (
                            <button
                              key={`candidate-${canonical}`}
                              type="button"
                              className={`rounded-full border px-2 py-1 text-xs transition-colors ${
                                active ? 'bg-primary text-primary-foreground border-primary' : 'hover:bg-muted'
                              }`}
                              onClick={() => setSelectedCanonical(canonical)}
                            >
                              {canonicalLabel(canonical)}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </Card>

                <div className="grid grid-cols-3 gap-2">
                  <Card className="p-3">
                    <div className="text-[11px] text-muted-foreground">Tables in section</div>
                    <div className="text-lg font-semibold">{tablesInSection.length}</div>
                  </Card>
                  <Card className="p-3">
                    <div className="text-[11px] text-muted-foreground">Equations in section</div>
                    <div className="text-lg font-semibold">{equationsInSection.length}</div>
                  </Card>
                  <Card className="p-3">
                    <div className="text-[11px] text-muted-foreground">Figures in section</div>
                    <div className="text-lg font-semibold">{activeDetail?.images.length ?? 0}</div>
                  </Card>
                </div>

                <Card className="p-3 bg-muted/10">
                  <div className="text-sm font-medium mb-2">Section text</div>
                  {!selectedCanonical && (
                    <div className="text-sm text-muted-foreground">No section could be resolved for this match.</div>
                  )}
                  {selectedCanonical && detailLoading && (
                    <div className="text-sm text-muted-foreground">Loading section text...</div>
                  )}
                  {selectedCanonical && !detailLoading && detailError && (
                    <div className="text-sm text-destructive">{detailError}</div>
                  )}
                  {selectedCanonical && !detailLoading && !detailError && activeDetail && (
                    <>
                      <div className="text-xs text-muted-foreground mb-2">
                        Pages: {activeDetail.pages.join(', ') || 'n/a'} • Source blocks: {activeDetail.source_block_count}
                      </div>
                      <div className="max-h-[30vh] overflow-auto rounded-md border bg-background p-2 text-xs leading-5 whitespace-pre-wrap">
                        {activeDetail.full_text || 'No text found for this section.'}
                      </div>
                      {activeDetail.truncated && (
                        <div className="text-[11px] text-muted-foreground mt-2">
                          Section text truncated for display.
                        </div>
                      )}
                    </>
                  )}
                </Card>

                <Card className="p-3 bg-muted/10">
                  <div className="text-sm font-medium mb-2">Equations ({equationsInSection.length})</div>
                  {equationsInSection.length === 0 && (
                    <div className="text-sm text-muted-foreground">No extracted equations mapped to this section.</div>
                  )}
                  {equationsInSection.length > 0 && (
                    <div className="space-y-2">
                      {equationsInSection.map((equation) => {
                        const equationUrl = buildEquationUrl(equation);
                        return (
                          <Card key={`search-eq-${equation.id}`} className="p-2 bg-background">
                            <div className="flex items-center gap-2 flex-wrap mb-1">
                              <Badge variant="outline">eq {equation.equation_number || equation.id}</Badge>
                              <Badge variant="outline">p{equation.page_no}</Badge>
                            </div>
                            {(equation.text_preview || equation.text) && (
                              <div className="text-xs text-muted-foreground whitespace-pre-wrap mb-2">
                                {equation.text_preview || equation.text}
                              </div>
                            )}
                            {equationUrl && (
                              <a href={equationUrl} target="_blank" rel="noreferrer">
                                <img
                                  src={equationUrl}
                                  alt={`eq-${equation.id}`}
                                  className="w-full rounded border object-contain max-h-40 bg-muted/10"
                                  loading="lazy"
                                />
                              </a>
                            )}
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </Card>

                <Card className="p-3 bg-muted/10">
                  <div className="text-sm font-medium mb-2">Tables ({tablesInSection.length})</div>
                  {tablesInSection.length === 0 && (
                    <div className="text-sm text-muted-foreground">No structured tables mapped to this section.</div>
                  )}
                  {tablesInSection.length > 0 && (
                    <div className="space-y-2">
                      {tablesInSection.map((table) => {
                        const normalized = normalizeTablePreview(table);
                        const hasStructuredPreview =
                          normalized.headers.length > 0 && normalized.rows.length > 0;
                        return (
                          <Card key={`search-table-${table.id}`} className="p-2 bg-background">
                            <div className="flex items-center gap-2 flex-wrap mb-1">
                              <Badge variant="outline">table {table.id}</Badge>
                              <Badge variant="outline">p{table.page_no}</Badge>
                              <Badge variant="secondary">
                                {table.n_rows}x{table.n_cols}
                              </Badge>
                            </div>
                            {table.caption ? (
                              <div className="text-xs text-muted-foreground mb-2">{table.caption}</div>
                            ) : null}
                            {hasStructuredPreview ? (
                              <div className="border rounded-md bg-background overflow-hidden">
                                <div className="max-h-64 overflow-auto">
                                  <table className="min-w-full text-[11px] leading-5 border-collapse">
                                    <thead className="bg-muted/50 sticky top-0 z-10">
                                      <tr>
                                        <th className="text-left align-top p-2 border-b border-r w-10">#</th>
                                        {normalized.headers.map((header, idx) => (
                                          <th
                                            key={`table-${table.id}-header-${idx}`}
                                            className="text-left align-top p-2 border-b border-r whitespace-pre-wrap"
                                          >
                                            {header}
                                          </th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {normalized.rows.map((row, rowIdx) => (
                                        <tr
                                          key={`table-${table.id}-row-${rowIdx}`}
                                          className="odd:bg-background even:bg-muted/20"
                                        >
                                          <td className="align-top p-2 border-b border-r text-muted-foreground">
                                            {rowIdx + 1}
                                          </td>
                                          {row.map((cell, cellIdx) => (
                                            <td
                                              key={`table-${table.id}-row-${rowIdx}-cell-${cellIdx}`}
                                              className="align-top p-2 border-b border-r whitespace-pre-wrap break-words min-w-[120px]"
                                            >
                                              {cell || '—'}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                                {table.preview_truncated && (
                                  <div className="px-2 py-1 text-[11px] text-muted-foreground border-t">
                                    Showing first {normalized.rows.length} rows in preview.
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div className="text-xs text-muted-foreground">
                                Structured preview not available for this table.
                              </div>
                            )}
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </Card>

                <Card className="p-3 bg-muted/10">
                  <div className="text-sm font-medium mb-2">Figures ({activeDetail?.images.length ?? 0})</div>
                  {!activeDetail && !detailLoading && !detailError && (
                    <div className="text-sm text-muted-foreground">Select a resolved section to load figures.</div>
                  )}
                  {activeDetail && activeDetail.images.length === 0 && (
                    <div className="text-sm text-muted-foreground">
                      No extracted figures mapped to this section.
                    </div>
                  )}
                  {activeDetail && activeDetail.images.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {activeDetail.images.map((image) => (
                        <Card key={`${image.id}-${image.file_name}`} className="p-2 bg-background">
                          <a href={buildFigureUrl(image)} target="_blank" rel="noreferrer">
                            <img
                              src={buildFigureUrl(image)}
                              alt={`${activeDetail.section_canonical} p${image.page_no}`}
                              className="w-full rounded border object-contain max-h-44 bg-muted/10"
                              loading="lazy"
                            />
                          </a>
                          <div className="text-[11px] text-muted-foreground mt-1">Page {image.page_no}</div>
                        </Card>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="ask" className="mt-2 flex-1 min-h-0 px-3 pb-3 overflow-hidden">
            <div className="h-full min-h-0 flex flex-col gap-3">
              <Card className="p-3 bg-muted/10">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">
                    Section: {selectedCanonical ? canonicalLabel(selectedCanonical) : 'unresolved'}
                  </Badge>
                  {activeDetail ? <Badge variant="outline">{activeDetail.pages.length} pages</Badge> : null}
                  <Badge variant="secondary">Local Ollama</Badge>
                </div>
                <div className="text-xs text-muted-foreground mt-2">
                  Questions are answered only from the selected section context.
                </div>
              </Card>

              <Card className="flex-1 min-h-0 p-3 bg-muted/10 overflow-hidden flex flex-col">
                <div className="text-sm font-medium mb-2">Section Q&A</div>
                <ScrollArea className="flex-1 pr-2">
                  <div className="space-y-3">
                    {qaTurns.length === 0 && (
                      <div className="text-sm text-muted-foreground">
                        Ask a question to start a section-focused conversation.
                      </div>
                    )}
                    {qaTurns.map((turn) => (
                      <Card key={turn.id} className="p-3 bg-background">
                        <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Question</div>
                        <div className="text-sm whitespace-pre-wrap">{turn.question}</div>
                        <div className="text-xs uppercase tracking-wide text-muted-foreground mt-3 mb-1">Answer</div>
                        {turn.error ? (
                          <div className="text-sm text-destructive">{turn.error}</div>
                        ) : turn.answer ? (
                          <div className="text-sm whitespace-pre-wrap leading-relaxed">{turn.answer}</div>
                        ) : (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Generating answer...
                          </div>
                        )}
                        {(turn.contextChars || turn.sourceBlockCount || turn.chunkCount) && (
                          <div className="text-[11px] text-muted-foreground mt-2">
                            Context chars: {turn.contextChars ?? 0} • Source blocks: {turn.sourceBlockCount ?? 0} •
                            Chunks: {turn.chunkCount ?? 0}
                          </div>
                        )}
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </Card>

              <Card className="p-3">
                <Textarea
                  value={questionDraft}
                  onChange={(event) => setQuestionDraft(event.target.value)}
                  placeholder={
                    selectedCanonical
                      ? `Ask anything about ${canonicalLabel(selectedCanonical)}...`
                      : 'Resolve a section first, then ask a question.'
                  }
                  className="min-h-[92px]"
                  disabled={!selectedCanonical || asking}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey) && !event.shiftKey) {
                      event.preventDefault();
                      void handleAskQuestion();
                    }
                  }}
                />
                <div className="mt-2 flex items-center justify-between">
                  <div className="text-[11px] text-muted-foreground">Use Ctrl/Cmd + Enter to ask</div>
                  <Button
                    size="sm"
                    onClick={() => void handleAskQuestion()}
                    disabled={!selectedCanonical || asking || !questionDraft.trim()}
                  >
                    {asking && <Loader2 className="h-4 w-4 animate-spin" />}
                    Ask
                  </Button>
                </div>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
