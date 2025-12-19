import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Search, ChevronRight, BookOpen, ExternalLink, Network } from 'lucide-react';

export default function RagPage() {
  const [query, setQuery] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setHasSearched(true);
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full p-6">
       <div className="text-center mb-10 mt-10">
         <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 mb-4">
           <Network className="h-6 w-6 text-primary" />
         </div>
         <h1 className="text-3xl font-bold tracking-tight mb-2">Knowledge Retrieval</h1>
         <p className="text-muted-foreground">Search across all your papers, notes, and external sources.</p>
       </div>

       <form onSubmit={handleSearch} className="flex gap-2 mb-8">
         <div className="relative flex-1">
           <Search className="absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
           <Input 
             className="pl-10 h-11 text-lg shadow-sm" 
             placeholder="Ask a question about your knowledge base..." 
             value={query}
             onChange={(e) => setQuery(e.target.value)}
           />
         </div>
         <Button type="submit" size="lg" className="h-11 px-8">Search</Button>
       </form>

       {hasSearched && (
         <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
            {/* Answer Card */}
            <Card className="p-6 border-primary/20 bg-primary/5 shadow-sm">
               <h3 className="font-semibold flex items-center gap-2 mb-3 text-primary">
                 <BookOpen className="h-4 w-4" /> 
                 Synthesized Answer
               </h3>
               <p className="leading-relaxed text-foreground/90">
                 Based on the documents in your library, <span className="bg-yellow-100 dark:bg-yellow-900/30 px-1 rounded">Transformer models</span> utilize a mechanism called self-attention to weigh the significance of different words in a sentence regardless of their positional distance. This allows for significantly more parallelization compared to RNNs.
               </p>
               <div className="mt-4 flex gap-2">
                 <Button variant="outline" size="sm" className="bg-background">Copy Answer</Button>
                 <Button variant="outline" size="sm" className="bg-background">Save to Notes</Button>
               </div>
            </Card>

            {/* Citations */}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Sources</h3>
              <div className="grid gap-3">
                {[1, 2, 3].map((i) => (
                  <Card key={i} className="p-4 hover:bg-muted/50 transition-colors cursor-pointer group">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium text-sm group-hover:text-primary transition-colors">Attention Is All You Need</h4>
                        <p className="text-xs text-muted-foreground mt-1">Vaswani et al., 2017 • Page {3 + i}</p>
                      </div>
                      <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <p className="text-xs mt-3 text-muted-foreground border-l-2 border-primary/30 pl-2 italic">
                      "...the transformer is the first transduction model relying entirely on self-attention..."
                    </p>
                  </Card>
                ))}
              </div>
            </div>
         </div>
       )}
    </div>
  );
}
