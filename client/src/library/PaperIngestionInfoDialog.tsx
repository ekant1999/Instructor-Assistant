import React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { API_BASE, getPaperIngestionSectionDetail, withNgrokSkipParam } from '@/lib/api';
import { ApiPaperFigureInfo, ApiPaperIngestionInfo, ApiPaperIngestionSectionDetail } from '@/lib/api-types';

interface PaperIngestionInfoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: ApiPaperIngestionInfo | null;
  loading: boolean;
  error: string | null;
}

function formatSourceSummary(info: ApiPaperIngestionInfo | null): string {
  if (!info?.section_source_summary?.length) return 'n/a';
  return info.section_source_summary
    .map((item) => `${item.source} (${item.count})`)
    .join(', ');
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
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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
            </div>

            <Card className="p-3">
              <div className="text-xs text-muted-foreground mb-1">Section Sources</div>
              <div className="text-sm">{formatSourceSummary(data)}</div>
              {data.message && <div className="text-xs text-muted-foreground mt-2">{data.message}</div>}
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[32vh] min-h-[220px] max-h-[420px] shrink-0">
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
        )}
      </DialogContent>
    </Dialog>
  );
}
