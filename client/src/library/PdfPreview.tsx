import React from 'react';
import { Paper } from '@/shared/types';
import { Button } from '@/components/ui/button';
import { ExternalLink, Download } from 'lucide-react';

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

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="h-14 border-b flex items-center justify-between px-6 bg-secondary/10">
        <h2 className="font-semibold text-sm truncate max-w-[300px]">{paper.title}</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="h-8">
            <Download className="h-4 w-4 mr-2" /> Download
          </Button>
          <Button variant="outline" size="sm" className="h-8">
            <ExternalLink className="h-4 w-4 mr-2" /> Open Original
          </Button>
        </div>
      </div>
      
      <div className="flex-1 p-8 overflow-auto bg-neutral-100 dark:bg-neutral-900">
        <div className="max-w-3xl mx-auto bg-white dark:bg-neutral-800 shadow-xl min-h-[800px] p-12 text-neutral-800 dark:text-neutral-200">
          <div className="text-center mb-8">
             <h1 className="text-2xl font-bold mb-2">{paper.title}</h1>
             <p className="text-sm text-neutral-500">{paper.source}, {paper.year}</p>
          </div>
          
          <div className="space-y-6 text-sm leading-relaxed text-justify font-serif">
            <h3 className="font-bold font-sans uppercase text-xs tracking-wider">Abstract</h3>
            <p>
              {paper.abstract || "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur."}
            </p>
            
            <h3 className="font-bold font-sans uppercase text-xs tracking-wider pt-4">1. Introduction</h3>
            <p>
              Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.
            </p>
            <p>
              Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur? Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae consequatur.
            </p>
            
             <h3 className="font-bold font-sans uppercase text-xs tracking-wider pt-4">2. Methodology</h3>
            <p>
              At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
