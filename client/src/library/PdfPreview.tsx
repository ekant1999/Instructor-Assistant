import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Paper } from '@/shared/types';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, ExternalLink, Download, ZoomIn, ZoomOut } from 'lucide-react';
import { API_BASE, getNgrokSkipHeaders, withNgrokSkipParam } from '@/lib/api';

interface PdfPreviewProps {
  paper: Paper | null;
  initialPage?: number;  // Navigate to specific page
  onPageChange?: (page: number) => void;  // Callback when page changes
}

export function PdfPreview({ paper, initialPage, onPageChange }: PdfPreviewProps) {
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

  useEffect(() => {
    if (!isWidget) return;
    activeSrcRef.current = pdfSrc;
    setPageNum(initialPage || 1);  // Use initialPage if provided
    setZoom(1);
    setPageCount(null);
    setRenderError(null);
    pdfDocRef.current = null;
  }, [isWidget, pdfSrc, initialPage]);
  
  // Notify parent when page changes
  useEffect(() => {
    if (onPageChange) {
      onPageChange(pageNum);
    }
  }, [pageNum, onPageChange]);

  useEffect(() => {
    if (!isWidget || !pdfSrc) return;
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
  }, [isWidget, pdfSrc, pageNum, zoom]);

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

        {pdfSrc && !isWidget && (
          <iframe title={paper.title} src={pdfSrc} className="h-full w-full" />
        )}

        {pdfSrc && isWidget && (
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

        {pdfSrc && isWidget && (
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
