import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Paper } from '@/shared/types';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, ExternalLink, Download, ZoomIn, ZoomOut } from 'lucide-react';
import { API_BASE, getNgrokSkipHeaders, withNgrokSkipParam } from '@/lib/api';

interface PdfPreviewProps {
  paper: Paper | null;
  initialPage?: number;  // Navigate to specific page
  highlight?: { pageNo: number; bbox: { x0: number; y0: number; x1: number; y1: number } };
  highlightText?: string;
  onPageChange?: (page: number) => void;  // Callback when page changes
}

export function PdfPreview({ paper, initialPage, highlight, highlightText, onPageChange }: PdfPreviewProps) {
  const isWidget = useMemo(
    () => typeof document !== 'undefined' && document.documentElement.dataset.iaWidget === 'true',
    []
  );
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pdfDocRef = useRef<any>(null);
  const pdfjsRef = useRef<any>(null);
  const activeSrcRef = useRef<string | null>(null);
  const [pageCount, setPageCount] = useState<number | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [isRendering, setIsRendering] = useState(false);
  const [renderError, setRenderError] = useState<string | null>(null);

  if (!paper) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-muted-foreground bg-secondary/20 m-4 rounded-xl border border-dashed">
        <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mb-4">
           <ExternalLink className="h-6 w-6 opacity-50" />
        </div>
        <p>Select a paper to preview</p>
      </div>
    );
  }

  const rawPdfSrc = paper.pdfUrl
    ? (paper.pdfUrl.startsWith('http') ? paper.pdfUrl : `${API_BASE}${paper.pdfUrl}`)
    : null;
  const pdfSrc = rawPdfSrc ? withNgrokSkipParam(rawPdfSrc) : null;
  const sourceUrl = paper.sourceUrl || undefined;
  const [usePdfJs, setUsePdfJs] = useState(isWidget);
  const shouldUsePdfJs = usePdfJs;
  const iframeSrc = pdfSrc && initialPage ? `${pdfSrc}#page=${initialPage}` : pdfSrc;

  useEffect(() => {
    if (!pdfSrc) return;
    activeSrcRef.current = pdfSrc;
    setZoom(1);
    setPageCount(null);
    setRenderError(null);
    pdfDocRef.current = null;
    if (initialPage) {
      setPageNum(initialPage);
    } else {
      setPageNum(1);
    }
    setUsePdfJs(isWidget);
  }, [pdfSrc, isWidget]);

  useEffect(() => {
    if (initialPage) {
      setPageNum(initialPage);
    }
    if (initialPage || highlight || (highlightText && highlightText.trim().length > 1)) {
      setUsePdfJs(true);
    }
  }, [initialPage, highlightText, highlight]);

  useEffect(() => {
    if (highlight) {
      setUsePdfJs(true);
    }
  }, [highlight]);

  useEffect(() => {
    if (highlightText && highlightText.trim().length > 1) {
      setUsePdfJs(true);
    }
  }, [highlightText]);
  
  // Notify parent when page changes
  useEffect(() => {
    if (onPageChange) {
      onPageChange(pageNum);
    }
  }, [pageNum, onPageChange]);

  useEffect(() => {
    if (!shouldUsePdfJs || !pdfSrc) return;
    let cancelled = false;
    const render = async () => {
      setIsRendering(true);
      setRenderError(null);
      try {
        let pdfjs = pdfjsRef.current;
        if (!pdfjs) {
          const pdfjsModule = await import(
            /* @vite-ignore */ 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.2.67/build/pdf.min.mjs'
          );
          pdfjs = (pdfjsModule as any).default ?? pdfjsModule;
          if (pdfjs?.GlobalWorkerOptions && !pdfjs.GlobalWorkerOptions.workerSrc) {
            pdfjs.GlobalWorkerOptions.workerSrc =
              'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.2.67/build/pdf.worker.min.mjs';
          }
          pdfjsRef.current = pdfjs;
        }

        let pdfDoc = pdfDocRef.current;
        if (!pdfDoc || activeSrcRef.current !== pdfSrc) {
          const res = await fetch(pdfSrc, { headers: getNgrokSkipHeaders() });
          if (!res.ok) {
            throw new Error(`Failed to load PDF (${res.status})`);
          }
          const data = await res.arrayBuffer();
          const loadingTask = pdfjs.getDocument({ data, disableWorker: true });
          pdfDoc = await loadingTask.promise;
          if (cancelled) return;
          pdfDocRef.current = pdfDoc;
          activeSrcRef.current = pdfSrc;
          setPageCount(pdfDoc.numPages);
          if (pageNum > pdfDoc.numPages) {
            setPageNum(1);
          }
        }

        const page = await pdfDoc.getPage(pageNum);
        if (cancelled) return;
        const canvas = canvasRef.current;
        if (!canvas) return;
        const context = canvas.getContext('2d');
        if (!context) return;

        const baseViewport = page.getViewport({ scale: 1 });
        const containerWidth = canvas.parentElement?.clientWidth ?? 720;
        const maxWidth = Math.max(320, containerWidth - 16);
        const fitScale = Math.min(2, maxWidth / baseViewport.width);
        const targetScale = Math.max(0.6, Math.min(3, fitScale * zoom));
        const viewport = page.getViewport({ scale: targetScale });
        const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;
        context.setTransform(dpr, 0, 0, dpr, 0, 0);
        await page.render({ canvasContext: context, viewport }).promise;

        let drewExact = false;
        const query = highlightText ? highlightText.trim() : '';
        if (query.length > 1) {
          const normalizedQuery = query.replace(/\s+/g, ' ').toLowerCase();
          const textContent = await page.getTextContent();
          const items = (textContent.items || []) as Array<any>;
          let combined = '';
          const indexed: Array<{ start: number; end: number; item: any }> = [];
          for (const item of items) {
            const raw = (item.str || '').replace(/\s+/g, ' ').trim();
            if (!raw) continue;
            if (combined.length > 0) {
              combined += ' ';
            }
            const start = combined.length;
            combined += raw;
            const end = combined.length;
            indexed.push({ start, end, item });
          }

          const haystack = combined.toLowerCase();
          const idx = haystack.indexOf(normalizedQuery);
          if (idx !== -1) {
            drewExact = true;
            const matchStart = idx;
            const matchEnd = idx + normalizedQuery.length;
            for (const entry of indexed) {
              if (entry.end <= matchStart || entry.start >= matchEnd) continue;
              const item = entry.item;
              if (!item.transform) continue;
              const pdfjs = pdfjsRef.current;
              const tx = pdfjs?.Util?.transform ? pdfjs.Util.transform(viewport.transform, item.transform) : item.transform;
              const x = tx[4];
              const y = tx[5];
              const fontHeight = Math.hypot(tx[2], tx[3]) || item.height || 10;
              const width = (item.width || 0);
              const height = fontHeight;
              const drawX = x;
              const drawY = y - height;
              context.save();
              context.globalAlpha = 0.22;
              context.fillStyle = '#fde68a';
              context.fillRect(drawX, drawY, width, height);
              context.globalAlpha = 0.85;
              context.strokeStyle = '#f59e0b';
              context.lineWidth = 1.5;
              context.strokeRect(drawX, drawY, width, height);
              context.restore();
            }
          }
        }

        if (!drewExact && highlight && highlight.pageNo === pageNum && typeof (viewport as any).convertToViewportRectangle === 'function') {
          const { x0, y0, x1, y1 } = highlight.bbox;
          const pdfViewport = page.getViewport({ scale: 1 });
          const pdfHeight = pdfViewport.height;
          const fy0 = pdfHeight - y1;
          const fy1 = pdfHeight - y0;
          const rect = (viewport as any).convertToViewportRectangle([x0, fy0, x1, fy1]);
          const [vx0, vy0, vx1, vy1] = rect;
          const left = Math.min(vx0, vx1);
          const top = Math.min(vy0, vy1);
          const width = Math.abs(vx1 - vx0);
          const height = Math.abs(vy1 - vy0);
          context.save();
          context.globalAlpha = 0.25;
          context.fillStyle = '#facc15';
          context.fillRect(left, top, width, height);
          context.globalAlpha = 0.9;
          context.strokeStyle = '#f59e0b';
          context.lineWidth = 2;
          context.strokeRect(left, top, width, height);
          context.restore();
        }
      } catch (err) {
        if (!cancelled) {
          setRenderError(err instanceof Error ? err.message : 'Failed to render PDF preview');
        }
      } finally {
        if (!cancelled) {
          setIsRendering(false);
        }
      }
    };

    render();
    return () => {
      cancelled = true;
    };
  }, [shouldUsePdfJs, pdfSrc, pageNum, zoom, highlight, highlightText]);

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="h-14 border-b flex items-center justify-between px-6 bg-secondary/10">
        <h2 className="font-semibold text-sm truncate max-w-[300px]">{paper.title}</h2>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8"
            disabled={!pdfSrc}
            onClick={() => {
              if (pdfSrc) window.open(pdfSrc, '_blank');
            }}
          >
            <Download className="h-4 w-4 mr-2" /> Download
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8"
            disabled={!sourceUrl}
            onClick={() => {
              if (sourceUrl) window.open(sourceUrl, '_blank');
            }}
          >
            <ExternalLink className="h-4 w-4 mr-2" /> Open Original
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden bg-neutral-100 dark:bg-neutral-900 relative">
        {!pdfSrc && (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            PDF preview not available for this paper.
          </div>
        )}

        {pdfSrc && !shouldUsePdfJs && (
          <iframe title={paper.title} src={iframeSrc || undefined} className="h-full w-full" />
        )}

        {pdfSrc && shouldUsePdfJs && (
          <div className="h-full w-full overflow-auto p-4">
            {renderError ? (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                {renderError}
              </div>
            ) : (
              <canvas ref={canvasRef} className="mx-auto bg-white rounded shadow" />
            )}
            {isRendering && (
              <div className="mt-3 text-center text-xs text-muted-foreground">Rendering preview…</div>
            )}
          </div>
        )}

        {pdfSrc && shouldUsePdfJs && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-background/90 border rounded-full px-3 py-1 shadow-sm">
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                disabled={zoom <= 0.7 || isRendering}
                onClick={() => setZoom((prev) => Math.max(0.7, Math.round((prev - 0.1) * 10) / 10))}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="text-xs text-muted-foreground w-[48px] text-center">
                {Math.round(zoom * 100)}%
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                disabled={zoom >= 2.5 || isRendering}
                onClick={() => setZoom((prev) => Math.min(2.5, Math.round((prev + 0.1) * 10) / 10))}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
            </div>
            {pageCount && pageCount > 1 && (
              <>
                <div className="h-4 w-px bg-border" />
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  disabled={pageNum <= 1 || isRendering}
                  onClick={() => setPageNum((prev) => Math.max(1, prev - 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-xs text-muted-foreground">
                  {pageNum} / {pageCount}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  disabled={pageNum >= pageCount || isRendering}
                  onClick={() => setPageNum((prev) => Math.min(pageCount, prev + 1))}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
