import React from 'react';
import { Paper } from '@/shared/types';
import { Button } from '@/components/ui/button';
import { ExternalLink, Download } from 'lucide-react';
import { API_BASE } from '@/lib/api';

export function PdfPreview({ paper }: { paper: Paper | null }) {
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

  const pdfSrc = paper.pdfUrl ? (paper.pdfUrl.startsWith('http') ? paper.pdfUrl : `${API_BASE}${paper.pdfUrl}`) : null;
  const sourceUrl = paper.sourceUrl || undefined;

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

      <div className="flex-1 overflow-hidden bg-neutral-100 dark:bg-neutral-900">
        {pdfSrc ? (
          <iframe title={paper.title} src={pdfSrc} className="h-full w-full" />
        ) : (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            PDF preview not available for this paper.
          </div>
        )}
      </div>
    </div>
  );
}
