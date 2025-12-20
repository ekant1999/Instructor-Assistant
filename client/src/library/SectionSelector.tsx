import React from 'react';
import { Paper, Section } from '@/shared/types';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Copy, CheckCircle2, Layers } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useState } from 'react';

interface SectionSelectorProps {
  paper: Paper;
  selectedSections: Set<string>;
  onSelectSection: (sectionId: string) => void;
  onSelectAll: () => void;
  onCopy: (text: string) => void;
}

export function SectionSelector({
  paper,
  selectedSections,
  onSelectSection,
  onSelectAll,
  onCopy
}: SectionSelectorProps) {
  const [copied, setCopied] = useState(false);
  
  if (!paper.sections || paper.sections.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <p>No sections available for this paper</p>
      </div>
    );
  }

  const handleCopySection = (content: string) => {
    onCopy(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const selectedContent = paper.sections
    .filter(s => selectedSections.has(s.id))
    .map(s => `## ${s.title}\n\n${s.content}`)
    .join('\n\n---\n\n');

  return (
    <div className="h-full flex flex-col">
      <div className="h-14 border-b px-6 flex items-center justify-between bg-muted/5">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <Layers className="h-4 w-4" />
          {selectedSections.size} of {paper.sections.length} selected
        </h3>
        <Button
          variant="outline"
          size="sm"
          onClick={onSelectAll}
          className="h-8 text-xs"
        >
          {selectedSections.size === paper.sections.length ? 'Deselect All' : 'Select All'}
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {paper.sections.map((section) => (
            <Card
              key={section.id}
              className={`p-4 cursor-pointer transition-all ${
                selectedSections.has(section.id)
                  ? 'border-primary bg-primary/5'
                  : 'hover:border-primary/50'
              }`}
            >
              <div className="flex items-start gap-3">
                <Checkbox
                  checked={selectedSections.has(section.id)}
                  onCheckedChange={() => onSelectSection(section.id)}
                  className="mt-1"
                />
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm">{section.title}</h4>
                  <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                    {section.content}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleCopySection(section.content)}
                  className="h-8 w-8 shrink-0"
                  title="Copy section"
                >
                  {copied ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  ) : (
                    <Copy className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                  )}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </ScrollArea>

      {selectedContent && (
        <div className="h-32 border-t bg-muted/5 p-4 flex flex-col gap-2">
          <p className="text-xs font-medium text-muted-foreground">Selected Content Preview</p>
          <div className="flex-1 bg-background rounded border p-2 text-xs overflow-auto font-mono text-muted-foreground line-clamp-4">
            {selectedContent}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleCopySection(selectedContent)}
            className="w-full h-8 text-xs"
          >
            {copied ? (
              <>
                <CheckCircle2 className="h-3 w-3 mr-2" /> Copied
              </>
            ) : (
              <>
                <Copy className="h-3 w-3 mr-2" /> Copy Selected
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
