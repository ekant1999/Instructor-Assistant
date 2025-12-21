import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { Loader2, RefreshCw, Save, CheckCircle2, FileUp, BookOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function QuestionSetsPage() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedContent, setGeneratedContent] = useState('');
  const [selectedPapers, setSelectedPapers] = useState<Set<string>>(new Set(['1']));
  const [questionType, setQuestionType] = useState('multiple-choice');
  
  const papers = [
    { id: '1', title: 'Attention Is All You Need', year: '2017' },
    { id: '2', title: 'BERT: Pre-training of Deep Bidirectional...', year: '2018' },
    { id: '3', title: 'GPT-4 Technical Report', year: '2023' }
  ];

  const togglePaper = (id: string) => {
    const newSet = new Set(selectedPapers);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedPapers(newSet);
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGeneratedContent('');
    
    const questions = [
      "### Question 1\n**What is the primary mechanism of the Transformer architecture?**\nA) LSTM cells\nB) Self-Attention\nC) Convolutions\nD) Backpropagation through time\n\n*Correct Answer: B*\n*Explanation: The Transformer relies entirely on self-attention mechanisms, as introduced in the 'Attention Is All You Need' paper.*",
      "\n\n### Question 2\n**Which of the following is NOT a benefit of the Transformer architecture?**\nA) Better parallelization\nB) Reduced toxicity\nC) Longer-range dependencies\nD) Faster training\n\n*Correct Answer: B*\n*Explanation: Reduced toxicity is not a direct architectural benefit of Transformers.*"
    ];

    for (const q of questions) {
      await new Promise(r => setTimeout(r, 1000));
      setGeneratedContent(prev => prev + q);
    }
    
    setIsGenerating(false);
  };

  return (
    <div className="h-full p-6 max-w-6xl mx-auto space-y-6 flex flex-col">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Question Sets</h1>
        <Button disabled={!generatedContent} size="lg">
          <Save className="h-5 w-5 mr-2" /> Save Set
        </Button>
      </div>

      <Tabs defaultValue="generate" className="flex-1 flex flex-col">
        <TabsList className="w-[300px]">
          <TabsTrigger value="generate">Generate</TabsTrigger>
          <TabsTrigger value="upload">Upload & Edit</TabsTrigger>
        </TabsList>
        
        <TabsContent value="generate" className="flex-1 mt-6 border rounded-xl overflow-hidden bg-background shadow-sm flex flex-col md:flex-row">
           {/* Left Panel - Controls */}
           <div className="w-full md:w-1/3 border-r bg-muted/10 p-6 flex flex-col gap-6 overflow-auto">
             {/* Source Material */}
             <div className="space-y-3">
               <h3 className="font-semibold text-base flex items-center gap-2">
                 <BookOpen className="h-5 w-5" />
                 Source Materials
               </h3>
               <Card className="p-4 space-y-3 border-primary/20 bg-primary/5">
                 {papers.map(paper => (
                   <div key={paper.id} className="flex items-center gap-3">
                     <Checkbox 
                       checked={selectedPapers.has(paper.id)}
                       onCheckedChange={() => togglePaper(paper.id)}
                     />
                     <label className="text-base flex-1 cursor-pointer">
                       <span className="font-medium">{paper.title}</span>
                       <span className="text-sm text-muted-foreground block">{paper.year}</span>
                     </label>
                   </div>
                 ))}
               </Card>
             </div>

             {/* Question Type */}
             <div className="space-y-3">
               <h3 className="font-semibold text-base">Question Type</h3>
               <div className="grid grid-cols-2 gap-2">
                 {[
                   { id: 'multiple-choice', label: 'Multiple Choice' },
                   { id: 'true-false', label: 'True/False' },
                   { id: 'short-answer', label: 'Short Answer' },
                   { id: 'mixed', label: 'Mixed' }
                 ].map(type => (
                   <Button 
                     key={type.id}
                     variant={questionType === type.id ? 'default' : 'outline'} 
                     size="default" 
                     className="h-10 text-base justify-start"
                     onClick={() => setQuestionType(type.id)}
                   >
                     {type.label}
                   </Button>
                 ))}
               </div>
             </div>

             {/* Model Selection */}
             <div className="space-y-3">
               <h3 className="font-semibold text-base">Model</h3>
               <Button variant="outline" size="default" className="w-full h-10 text-base justify-start">
                 ⚡ Qwen (Local) - Recommended
               </Button>
             </div>

             <div className="flex-1" />
             
             <Button onClick={handleGenerate} disabled={isGenerating || selectedPapers.size === 0} className="w-full" size="lg">
               {isGenerating ? <Loader2 className="h-5 w-5 animate-spin mr-2" /> : <RefreshCw className="h-5 w-5 mr-2" />}
               {isGenerating ? 'Generating...' : 'Generate Questions'}
             </Button>
           </div>

           {/* Right Panel - Preview */}
           <div className="flex-1 bg-background flex flex-col">
             <div className="p-4 border-b bg-muted/5 flex justify-between items-center text-sm text-muted-foreground">
               <span>Preview</span>
               <span>Markdown</span>
             </div>
             <ScrollArea className="flex-1 p-8">
               {generatedContent ? (
                 <div className="prose prose-base dark:prose-invert max-w-none">
                   <ReactMarkdown>{generatedContent}</ReactMarkdown>
                 </div>
               ) : (
                 <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50">
                   <FileUp className="h-16 w-16 mb-3" />
                   <p className="text-lg">{selectedPapers.size === 0 ? 'Select source materials' : 'Click generate to create questions'}</p>
                 </div>
               )}
             </ScrollArea>
           </div>
        </TabsContent>

        <TabsContent value="upload">
          <Card className="h-[400px] flex flex-col items-center justify-center border-dashed">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-secondary rounded-full flex items-center justify-center mx-auto">
                <FileUp className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <h3 className="font-semibold text-xl">Upload Question Set</h3>
                <p className="text-muted-foreground text-base">Drag and drop Markdown or CSV files</p>
              </div>
              <Button variant="outline">Select File</Button>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
