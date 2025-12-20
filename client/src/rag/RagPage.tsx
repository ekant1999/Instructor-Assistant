import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Search, BookOpen, ExternalLink, Network, Copy, CheckCircle2, MessageSquare, Save } from 'lucide-react';
import { useState as useStateType } from 'react';

export default function RagPage() {
  const [query, setQuery] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [includeCitations, setIncludeCitations] = useState(true);
  const [maxChunks, setMaxChunks] = useState('5');
  const [copied, setCopied] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setHasSearched(true);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText('Based on the documents...');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full p-6 space-y-6">
       <div className="text-center mb-6">
         <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 mb-4">
           <Network className="h-6 w-6 text-primary" />
         </div>
         <h1 className="text-3xl font-bold tracking-tight mb-2">Knowledge Retrieval</h1>
         <p className="text-muted-foreground">Search across all your papers, notes, and external sources.</p>
       </div>

       {/* Query Section */}
       <div className="space-y-4">
         <form onSubmit={handleSearch} className="flex gap-2">
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

         {/* Advanced Options */}
         <Card className="p-4 bg-muted/5">
           <div className="space-y-3">
             <p className="text-xs font-semibold uppercase text-muted-foreground">Advanced Options</p>
             <div className="grid grid-cols-2 gap-4">
               <div className="flex items-center gap-2">
                 <Checkbox 
                   id="citations" 
                   checked={includeCitations}
                   onCheckedChange={(checked) => setIncludeCitations(checked as boolean)}
                 />
                 <Label htmlFor="citations" className="text-sm cursor-pointer">Include citations</Label>
               </div>
               <div className="space-y-1">
                 <Label htmlFor="chunks" className="text-sm">Max chunks: {maxChunks}</Label>
                 <Input 
                   id="chunks"
                   type="number" 
                   min="1" 
                   max="20"
                   value={maxChunks}
                   onChange={(e) => setMaxChunks(e.target.value)}
                   className="h-7 text-sm"
                 />
               </div>
             </div>
           </div>
         </Card>
       </div>

       {hasSearched && (
         <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 flex-1">
            {/* Answer Card */}
            <Card className="p-6 border-primary/20 bg-primary/5 shadow-sm">
               <div className="flex items-start justify-between mb-4">
                 <h3 className="font-semibold flex items-center gap-2 text-primary">
                   <BookOpen className="h-4 w-4" /> 
                   Synthesized Answer
                 </h3>
                 <div className="flex gap-2">
                   <Button 
                     variant="ghost" 
                     size="icon" 
                     className="h-8 w-8"
                     onClick={handleCopy}
                     title="Copy answer"
                   >
                     {copied ? (
                       <CheckCircle2 className="h-4 w-4 text-green-500" />
                     ) : (
                       <Copy className="h-4 w-4" />
                     )}
                   </Button>
                 </div>
               </div>

               <p className="leading-relaxed text-foreground/90 mb-6">
                 Based on the documents in your library, <span className="bg-yellow-100 dark:bg-yellow-900/30 px-1 rounded">Transformer models</span> utilize a mechanism called self-attention to weigh the significance of different words in a sentence regardless of their positional distance. This allows for significantly more parallelization compared to RNNs.
               </p>
               
               <div className="flex flex-wrap gap-2">
                 <Button 
                   variant="outline" 
                   size="sm" 
                   className="bg-background h-8 text-xs"
                   onClick={() => navigator.clipboard.writeText('Based on the documents...')}
                 >
                   <MessageSquare className="h-3 w-3 mr-2" /> Send to Chat
                 </Button>
                 <Button 
                   variant="outline" 
                   size="sm" 
                   className="bg-background h-8 text-xs"
                 >
                   <Save className="h-3 w-3 mr-2" /> Save as Note
                 </Button>
               </div>
            </Card>

            {/* Citations */}
            {includeCitations && (
              <div>
                <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Sources</h3>
                <div className="grid gap-3">
                  {[1, 2, 3].map((i) => (
                    <Card key={i} className="p-4 hover:bg-muted/50 transition-colors cursor-pointer group">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h4 className="font-medium text-sm group-hover:text-primary transition-colors">Attention Is All You Need</h4>
                          <p className="text-xs text-muted-foreground mt-1">Vaswani et al., 2017 • Page {3 + i}</p>
                        </div>
                        <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                      </div>
                      <p className="text-xs mt-3 text-muted-foreground border-l-2 border-primary/30 pl-2 italic">
                        "[{i}] ...the transformer is the first transduction model relying entirely on self-attention..."
                      </p>
                    </Card>
                  ))}
                </div>
              </div>
            )}
         </div>
       )}
    </div>
  );
}
