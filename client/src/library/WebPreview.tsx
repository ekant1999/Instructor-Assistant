import React, { useEffect, useRef } from 'react';
import { ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Paper } from '@/shared/types';

interface WebPreviewProps {
  paper: Paper | null;
  highlightText?: string;
  highlightSectionId?: string;
  scrollToSectionId?: string;
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function renderHighlightedText(text: string, query: string | undefined, markRef?: (el: HTMLSpanElement | null) => void) {
  if (!query || !query.trim()) {
    return text;
  }
  const escaped = escapeRegExp(query.trim());
  if (!escaped) return text;
  const regex = new RegExp(escaped, 'i');
  const match = regex.exec(text);
  if (!match) return text;
  const before = text.slice(0, match.index);
  const hit = text.slice(match.index, match.index + match[0].length);
  const after = text.slice(match.index + match[0].length);
  return (
    <>
      {before}
      <mark
        ref={markRef}
        className="bg-yellow-200/80 dark:bg-yellow-600/40 border border-yellow-500/70 text-foreground rounded-sm px-0.5"
      >
        {hit}
      </mark>
      {after}
    </>
  );
}

export function WebPreview({ paper, highlightText, highlightSectionId, scrollToSectionId }: WebPreviewProps) {
  const sectionRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const firstMatchRef = useRef<HTMLSpanElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    firstMatchRef.current = null;
  }, [highlightText, highlightSectionId, paper?.id]);

  useEffect(() => {
    if (scrollToSectionId) {
      const element = sectionRefs.current.get(scrollToSectionId);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
    }
    if (firstMatchRef.current) {
      firstMatchRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [scrollToSectionId, highlightSectionId, highlightText]);

  useEffect(() => {
    if (highlightText || highlightSectionId || scrollToSectionId) return;
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [highlightText, highlightSectionId, scrollToSectionId, paper?.id]);

  if (!paper) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-muted-foreground bg-secondary/20 m-4 rounded-xl border border-dashed">
        <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mb-4">
          <ExternalLink className="h-6 w-6 opacity-50" />
        </div>
        <p>Select a web document to preview</p>
      </div>
    );
  }

  const sections = paper.sections || [];
  const sourceUrl = paper.sourceUrl || undefined;
  const normalizedQuery = highlightText?.trim().toLowerCase() || "";
  return (
    <div className="h-full flex flex-col bg-background">
      <div className="h-14 border-b flex items-center justify-between px-6 bg-secondary/10">
        <h2 className="font-semibold text-sm truncate max-w-[300px]">{paper.title}</h2>
        <div className="flex gap-2">
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

      <div ref={scrollRef} className="flex-1 overflow-auto bg-neutral-100 dark:bg-neutral-900">
        <div className="max-w-4xl mx-auto px-6 py-6 space-y-5">
          {sections.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              Extracted content is not ready yet. Please try again in a moment.
            </div>
          ) : (
            sections.map((section, idx) => (
              <div
                key={section.id || idx}
                ref={(el) => {
                  if (el) {
                    sectionRefs.current.set(section.id, el);
                  } else {
                    sectionRefs.current.delete(section.id);
                  }
                }}
                className={`bg-white dark:bg-neutral-950 rounded-lg border p-4 ${
                  highlightSectionId === section.id ? 'border-yellow-500 ring-2 ring-yellow-500/40' : ''
                }`}
              >
                <div className="text-xs text-muted-foreground mb-2">
                  Chunk {idx + 1}
                </div>
                <div className="text-sm leading-relaxed whitespace-pre-wrap">
                  {(() => {
                    const content = section.content || "";
                    const hasExactQuery =
                      normalizedQuery && content.toLowerCase().includes(normalizedQuery);
                    const fallbackHighlight =
                      !hasExactQuery && highlightSectionId === section.id
                        ? section.matchText || highlightText
                        : undefined;
                    const highlightValue = hasExactQuery ? highlightText : fallbackHighlight;
                    const captureRef =
                      highlightSectionId === section.id && !firstMatchRef.current
                        ? (el: HTMLSpanElement | null) => {
                            if (el) firstMatchRef.current = el;
                          }
                        : undefined;
                    return renderHighlightedText(content, highlightValue, captureRef);
                  })()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
