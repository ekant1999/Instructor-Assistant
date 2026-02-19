import React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { API_BASE, getPaperIngestionSectionDetail, withNgrokSkipParam } from '@/lib/api';
import { ApiPaperFigureInfo, ApiPaperIngestionInfo, ApiPaperIngestionSectionDetail } from '@/lib/api-types';

const MIN_TOP_PANELS_HEIGHT = 72;
const MIN_SECTION_DETAIL_HEIGHT = 140;
const DEFAULT_TOP_PANELS_HEIGHT = 320;

interface PaperIngestionInfoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: ApiPaperIngestionInfo | null;
  loading: boolean;
  error: string | null;
}

function sectionButtonClasses(active: boolean): string {
  if (active) {
    return 'w-full text-left p-3 bg-muted/30 ring-1 ring-primary rounded-md';
  }
  return 'w-full text-left p-3 bg-muted/20 hover:bg-muted/30 rounded-md transition-colors';
}

function buildFigureUrl(image: ApiPaperFigureInfo): string {
  const apiRoot = API_BASE.replace(/\/api\/?$/, '');
  return withNgrokSkipParam(`${apiRoot}${image.url}`);
}

export function PaperIngestionInfoDialog({
  open,
  onOpenChange,
  data,
  loading,
  error,
}: PaperIngestionInfoDialogProps) {
  const [selectedCanonical, setSelectedCanonical] = React.useState<string | null>(null);
  const [sectionDetail, setSectionDetail] = React.useState<ApiPaperIngestionSectionDetail | null>(null);
  const [sectionLoading, setSectionLoading] = React.useState(false);
  const [sectionError, setSectionError] = React.useState<string | null>(null);
  const [topPanelsHeight, setTopPanelsHeight] = React.useState(DEFAULT_TOP_PANELS_HEIGHT);
  const [isResizing, setIsResizing] = React.useState(false);
  const splitContainerRef = React.useRef<HTMLDivElement | null>(null);
  const resizeStateRef = React.useRef<{
    startY: number;
    startHeight: number;
    containerHeight: number;
  } | null>(null);

  const clampTopPanelsHeight = React.useCallback((next: number, explicitContainerHeight?: number) => {
    const containerHeight = explicitContainerHeight ?? splitContainerRef.current?.clientHeight ?? 640;
    const maxTop = Math.max(MIN_TOP_PANELS_HEIGHT, containerHeight - MIN_SECTION_DETAIL_HEIGHT);
    return Math.max(MIN_TOP_PANELS_HEIGHT, Math.min(maxTop, next));
  }, []);

  const beginResize = React.useCallback((clientY: number) => {
    const containerHeight = splitContainerRef.current?.clientHeight ?? 0;
    if (containerHeight <= 0) return;
    resizeStateRef.current = {
      startY: clientY,
      startHeight: topPanelsHeight,
      containerHeight,
    };
    setIsResizing(true);
  }, [topPanelsHeight]);

  const updateTopPanelsHeight = React.useCallback((clientY: number) => {
    const state = resizeStateRef.current;
    if (!state) return;
    const deltaY = clientY - state.startY;
    setTopPanelsHeight(clampTopPanelsHeight(state.startHeight + deltaY, state.containerHeight));
  }, [clampTopPanelsHeight]);

  React.useEffect(() => {
    function onPointerMove(event: PointerEvent) {
      if (!resizeStateRef.current) return;
      event.preventDefault();
      updateTopPanelsHeight(event.clientY);
    }

    function stopResize() {
      if (!resizeStateRef.current) return;
      resizeStateRef.current = null;
      setIsResizing(false);
    }

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', stopResize);
    window.addEventListener('pointercancel', stopResize);
    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', stopResize);
      window.removeEventListener('pointercancel', stopResize);
    };
  }, [updateTopPanelsHeight]);

  React.useEffect(() => {
    if (!isResizing) return;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
    return () => {
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    };
  }, [isResizing]);

  React.useEffect(() => {
    const container = splitContainerRef.current;
    if (!container || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver((entries) => {
      const nextHeight = entries[0]?.contentRect.height ?? 0;
      if (nextHeight > 0) {
        setTopPanelsHeight((prev) => clampTopPanelsHeight(prev, nextHeight));
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [clampTopPanelsHeight, open]);

  React.useEffect(() => {
    if (!open) return;
    setTopPanelsHeight((prev) => clampTopPanelsHeight(prev));
  }, [open, clampTopPanelsHeight]);

  React.useEffect(() => {
    if (!open) {
      setSelectedCanonical(null);
      setSectionDetail(null);
      setSectionLoading(false);
      setSectionError(null);
    }
  }, [open]);

  React.useEffect(() => {
    if (!data) {
      setSelectedCanonical(null);
      setSectionDetail(null);
      setSectionLoading(false);
      setSectionError(null);
      return;
    }
    setSectionDetail(null);
    setSectionLoading(false);
    setSectionError(null);
    setSelectedCanonical((prev) => {
      if (prev && data.sections.some((item) => item.canonical === prev)) {
        return prev;
      }
      return data.sections[0]?.canonical || null;
    });
  }, [data]);

  React.useEffect(() => {
    if (!open || !data || !selectedCanonical) return;
    if (
      sectionDetail &&
      sectionDetail.paper_id === data.paper_id &&
      sectionDetail.section_canonical === selectedCanonical
    ) {
      return;
    }

    let cancelled = false;
    async function loadSectionDetail() {
      setSectionLoading(true);
      setSectionError(null);
      try {
        const detail = await getPaperIngestionSectionDetail(data.paper_id, selectedCanonical, 350000);
        if (!cancelled) {
          setSectionDetail(detail);
        }
      } catch (fetchError) {
        if (!cancelled) {
          setSectionDetail(null);
          setSectionError(fetchError instanceof Error ? fetchError.message : 'Failed to load section detail');
        }
      } finally {
        if (!cancelled) {
          setSectionLoading(false);
        }
      }
    }
    loadSectionDetail();
    return () => {
      cancelled = true;
    };
  }, [open, data, selectedCanonical]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl w-[94vw] h-[88vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle>PDF Ingestion Info (Temporary)</DialogTitle>
          <DialogDescription>
            {data?.paper_title || 'Selected paper'}: section extraction, produced chunks, and chunk metadata.
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            Loading ingestion info...
          </div>
        )}

        {!loading && error && (
          <div className="flex-1 flex items-center justify-center text-sm text-destructive">
            {error}
          </div>
        )}

        {!loading && !error && data && (
          <div className="flex-1 min-h-0 flex flex-col gap-4 overflow-hidden">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <Card className="p-3">
                <div className="text-xs text-muted-foreground">Total Chunks</div>
                <div className="text-lg font-semibold">{data.total_chunks}</div>
              </Card>
              <Card className="p-3">
                <div className="text-xs text-muted-foreground">Returned Chunks</div>
                <div className="text-lg font-semibold">{data.returned_chunks}</div>
              </Card>
              <Card className="p-3">
                <div className="text-xs text-muted-foreground">Section Buckets</div>
                <div className="text-lg font-semibold">{data.sections.length}</div>
              </Card>
              <Card className="p-3">
                <div className="text-xs text-muted-foreground">Strategy</div>
                <div className="text-sm font-medium">{data.section_strategy || 'unknown'}</div>
              </Card>
              <Card className="p-3">
                <div className="text-xs text-muted-foreground">Structured Tables</div>
                <div className="text-lg font-semibold">{data.num_tables ?? data.tables?.length ?? 0}</div>
              </Card>
            </div>

            {data.message && (
              <div className="text-xs text-muted-foreground px-1">{data.message}</div>
            )}

            <Card className="p-3 min-h-0 flex flex-col shrink-0 max-h-[24vh]">
              <div className="font-medium text-sm mb-2">
                Extracted Tables ({data.tables?.length ?? 0})
              </div>
              {(!data.tables || data.tables.length === 0) && (
                <div className="text-sm text-muted-foreground">No structured tables detected for this paper.</div>
              )}
              {data.tables && data.tables.length > 0 && (
                <ScrollArea className="flex-1 pr-2">
                  <div className="space-y-2">
                    {data.tables.map((table) => (
                      <Card key={`table-${table.id}`} className="p-3 bg-muted/20">
                        {(() => {
                          const previewHeaders = Array.isArray(table.headers_preview) ? table.headers_preview : [];
                          const previewRows = Array.isArray(table.rows_preview) ? table.rows_preview : [];
                          const previewColCount = Math.max(
                            table.n_cols || 0,
                            previewHeaders.length,
                            ...previewRows.map((row) => row.length),
                          );
                          const normalizedHeaders = Array.from({ length: previewColCount }, (_, idx) => {
                            const value = previewHeaders[idx] || '';
                            return value.trim() || `col_${idx + 1}`;
                          });
                          const normalizedRows = previewRows.map((row) => {
                            if (row.length >= previewColCount) return row.slice(0, previewColCount);
                            return [...row, ...Array(previewColCount - row.length).fill('')];
                          });
                          const hasStructuredPreview = normalizedHeaders.length > 0 && normalizedRows.length > 0;

                          return (
                            <>
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <Badge variant="outline">table {table.id}</Badge>
                          <Badge variant="outline">p{table.page_no}</Badge>
                          <Badge variant="secondary">
                            {table.n_rows}x{table.n_cols}
                          </Badge>
                          {table.section_canonical && <Badge variant="outline">{table.section_canonical}</Badge>}
                          {table.section_source && <Badge variant="outline">{table.section_source}</Badge>}
                          {typeof table.section_confidence === 'number' && (
                            <Badge variant="outline">conf {table.section_confidence.toFixed(2)}</Badge>
                          )}
                        </div>
                        {table.caption && (
                          <div className="text-xs text-muted-foreground mb-2">{table.caption}</div>
                        )}
                        {(hasStructuredPreview || table.markdown_preview) && (
                          <details>
                            <summary className="text-xs cursor-pointer text-muted-foreground">
                              Show table preview
                            </summary>
                            {hasStructuredPreview && (
                              <div className="mt-2 border rounded-md bg-background overflow-hidden">
                                <div className="max-h-64 overflow-auto">
                                  <table className="min-w-full text-[11px] leading-5 border-collapse">
                                    <thead className="bg-muted/50 sticky top-0 z-10">
                                      <tr>
                                        <th className="text-left align-top p-2 border-b border-r w-10">#</th>
                                        {normalizedHeaders.map((header, idx) => (
                                          <th key={`table-${table.id}-header-${idx}`} className="text-left align-top p-2 border-b border-r whitespace-pre-wrap">
                                            {header}
                                          </th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {normalizedRows.map((row, rowIdx) => (
                                        <tr key={`table-${table.id}-row-${rowIdx}`} className="odd:bg-background even:bg-muted/20">
                                          <td className="align-top p-2 border-b border-r text-muted-foreground">{rowIdx + 1}</td>
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
                                    Showing first {normalizedRows.length} rows in preview.
                                  </div>
                                )}
                              </div>
                            )}
                            {!hasStructuredPreview && table.markdown_preview && (
                              <pre className="mt-2 text-[11px] leading-5 whitespace-pre-wrap break-words bg-background border rounded-md p-2">
                                {table.markdown_preview}
                              </pre>
                            )}
                          </details>
                        )}
                            </>
                          );
                        })()}
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </Card>

            <div ref={splitContainerRef} className="flex-1 min-h-0 flex flex-col overflow-hidden">
              <div
                className="grid grid-cols-1 lg:grid-cols-2 gap-4 shrink-0 min-h-[72px]"
                style={{ height: `${topPanelsHeight}px` }}
              >
                <Card className="p-3 min-h-0 flex flex-col">
                  <div className="font-medium text-sm mb-2">Extracted Sections</div>
                  <ScrollArea className="flex-1 pr-2">
                    <div className="space-y-2">
                      {data.sections.map((section) => (
                        <button
                          key={section.canonical}
                          type="button"
                          className={sectionButtonClasses(selectedCanonical === section.canonical)}
                          onClick={() => setSelectedCanonical(section.canonical)}
                        >
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <Badge variant="outline">{section.canonical}</Badge>
                            <Badge variant="secondary">{section.chunk_count} chunks</Badge>
                            <Badge variant="outline">{section.primary_source}</Badge>
                            {typeof section.avg_confidence === 'number' && (
                              <Badge variant="outline">conf {section.avg_confidence.toFixed(2)}</Badge>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Pages: {section.pages.join(', ') || 'n/a'}
                          </div>
                          {section.title_samples.length > 0 && (
                            <div className="text-xs mt-1">
                              Titles: {section.title_samples.join(' | ')}
                            </div>
                          )}
                          <div className="text-[11px] mt-2 text-muted-foreground">
                            Click to view full section text and related figures
                          </div>
                        </button>
                      ))}
                      {data.sections.length === 0 && (
                        <div className="text-sm text-muted-foreground">No section metadata found.</div>
                      )}
                    </div>
                  </ScrollArea>
                </Card>

                <Card className="p-3 min-h-0 flex flex-col">
                  <div className="font-medium text-sm mb-2 flex items-center gap-2">
                    Chunks
                    {data.truncated && <Badge variant="outline">Showing first {data.returned_chunks}</Badge>}
                  </div>
                  <ScrollArea className="flex-1 pr-2">
                    <div className="space-y-3">
                      {data.chunks.map((chunk) => (
                        <Card key={chunk.id} className="p-3 bg-muted/20">
                          <div className="flex items-center gap-2 flex-wrap mb-2">
                            <Badge variant="outline">id {chunk.id}</Badge>
                            <Badge variant="outline">p{chunk.page_no}:b{chunk.block_index}</Badge>
                            <Badge variant="secondary">{chunk.char_count} chars</Badge>
                            {chunk.section_primary && <Badge variant="outline">{chunk.section_primary}</Badge>}
                          </div>
                          <div className="text-sm leading-relaxed whitespace-pre-wrap">{chunk.text_preview}</div>
                          <Separator className="my-2" />
                          <details>
                            <summary className="text-xs cursor-pointer text-muted-foreground">
                              Show chunk metadata
                            </summary>
                            <pre className="mt-2 text-[11px] leading-5 whitespace-pre-wrap break-words bg-background border rounded-md p-2">
                              {JSON.stringify(chunk.metadata, null, 2)}
                            </pre>
                          </details>
                        </Card>
                      ))}
                      {data.chunks.length === 0 && (
                        <div className="text-sm text-muted-foreground">No chunks found.</div>
                      )}
                    </div>
                  </ScrollArea>
                </Card>
              </div>

              <div
                role="separator"
                aria-orientation="horizontal"
                className={`shrink-0 py-1 cursor-row-resize select-none touch-none ${isResizing ? 'bg-muted/30' : ''}`}
                onPointerDown={(event) => {
                  if (event.button !== 0) return;
                  event.preventDefault();
                  beginResize(event.clientY);
                }}
                onDoubleClick={() => setTopPanelsHeight(clampTopPanelsHeight(DEFAULT_TOP_PANELS_HEIGHT))}
              >
                <div
                  className={`mx-auto h-1.5 w-20 rounded-full transition-colors ${
                    isResizing ? 'bg-primary/60' : 'bg-border hover:bg-muted-foreground/50'
                  }`}
                />
                <div className="text-[10px] text-center text-muted-foreground mt-1">
                  Drag to resize
                </div>
              </div>

              <Card className="p-3 min-h-0 flex-1 flex flex-col overflow-hidden">
                <div className="font-medium text-sm mb-2 flex items-center gap-2">
                  Section Detail
                  {selectedCanonical && <Badge variant="outline">{selectedCanonical}</Badge>}
                </div>
                {!selectedCanonical && (
                  <div className="text-sm text-muted-foreground">Select a section to view its full text and figures.</div>
                )}
                {selectedCanonical && sectionLoading && (
                  <div className="text-sm text-muted-foreground">Loading section detail...</div>
                )}
                {selectedCanonical && !sectionLoading && sectionError && (
                  <div className="text-sm text-destructive">{sectionError}</div>
                )}
                {selectedCanonical && !sectionLoading && !sectionError && sectionDetail && (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1 min-h-0 overflow-hidden">
                    <div className="lg:col-span-2 min-h-0 flex flex-col">
                      <div className="text-xs text-muted-foreground mb-2">
                        Pages: {sectionDetail.pages.join(', ') || 'n/a'} • Source blocks: {sectionDetail.source_block_count} • Chunks: {sectionDetail.chunk_count}
                      </div>
                      <ScrollArea className="flex-1 pr-2 border rounded-md p-3 bg-muted/10">
                        <div className="text-sm leading-relaxed whitespace-pre-wrap">
                          {sectionDetail.full_text || 'No text found for this section.'}
                        </div>
                      </ScrollArea>
                      {sectionDetail.truncated && (
                        <div className="text-[11px] mt-2 text-muted-foreground">
                          Section text is truncated for display.
                        </div>
                      )}
                    </div>

                    <div className="min-h-0 flex flex-col">
                      <div className="text-xs text-muted-foreground mb-2">
                        Figures in this section ({sectionDetail.images.length})
                      </div>
                      <ScrollArea className="flex-1 pr-2">
                        <div className="space-y-3">
                          {sectionDetail.images.map((image) => (
                            <Card key={`${image.id}-${image.file_name}`} className="p-2 bg-muted/20">
                              <a href={buildFigureUrl(image)} target="_blank" rel="noreferrer">
                                <img
                                  src={buildFigureUrl(image)}
                                  alt={`${sectionDetail.section_canonical} p${image.page_no}`}
                                  className="w-full rounded-md border object-contain max-h-52 bg-background"
                                  loading="lazy"
                                />
                              </a>
                              <div className="text-[11px] text-muted-foreground mt-2">
                                Page {image.page_no}
                              </div>
                            </Card>
                          ))}
                          {sectionDetail.images.length === 0 && (
                            <div className="text-sm text-muted-foreground">
                              No extracted figures mapped to this section.
                            </div>
                          )}
                        </div>
                      </ScrollArea>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
