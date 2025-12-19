import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, RefreshCw, Save, CheckCircle2, FileUp } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function QuestionSetsPage() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedContent, setGeneratedContent] = useState('');
  
  const handleGenerate = async () => {
    setIsGenerating(true);
    setGeneratedContent('');
    
    const questions = [
      "### Question 1\n**What is the primary mechanism of the Transformer architecture?**\nA) LSTM cells\nB) Self-Attention\nC) Convolutions\nD) Backpropagation through time\n\n*Correct Answer: B*",
      "\n\n### Question 2\n**Which of the following is NOT a benefit of Reinforcement Learning from Human Feedback (RLHF)?**\nA) Reduced toxicity\nB) Better alignment with user intent\nC) Reduced training compute cost\nD) Improved factual accuracy\n\n*Correct Answer: C*"
    ];

    for (const q of questions) {
      await new Promise(r => setTimeout(r, 1000));
      setGeneratedContent(prev => prev + q);
    }
    
    setIsGenerating(false);
  };

  return (
    <div className="h-full p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Question Sets</h1>
        <Button>
          <Save className="h-4 w-4 mr-2" /> Save Set
        </Button>
      </div>

      <Tabs defaultValue="generate" className="h-full flex flex-col">
        <TabsList className="w-[400px]">
          <TabsTrigger value="generate">Generate</TabsTrigger>
          <TabsTrigger value="upload">Upload & Edit</TabsTrigger>
        </TabsList>
        
        <TabsContent value="generate" className="flex-1 mt-6 border rounded-xl overflow-hidden bg-background shadow-sm flex flex-col md:flex-row h-[600px]">
           {/* Controls */}
           <div className="w-full md:w-1/3 border-r bg-muted/10 p-6 flex flex-col gap-4">
             <div className="space-y-2">
               <label className="text-sm font-medium">Topic / Source Material</label>
               <Textarea 
                 placeholder="Paste text or describe the topic..." 
                 className="min-h-[150px] bg-background"
               />
             </div>
             
             <div className="space-y-2">
               <label className="text-sm font-medium">Question Type</label>
               <div className="grid grid-cols-2 gap-2">
                 <Button variant="outline" size="sm" className="justify-start">Multiple Choice</Button>
                 <Button variant="outline" size="sm" className="justify-start">True/False</Button>
                 <Button variant="outline" size="sm" className="justify-start">Short Answer</Button>
                 <Button variant="outline" size="sm" className="justify-start">Mixed</Button>
               </div>
             </div>

             <div className="flex-1" />
             
             <Button onClick={handleGenerate} disabled={isGenerating} className="w-full">
               {isGenerating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
               {isGenerating ? 'Generating...' : 'Generate Questions'}
             </Button>
           </div>

           {/* Preview */}
           <div className="flex-1 bg-background flex flex-col">
             <div className="p-3 border-b bg-muted/5 flex justify-between items-center text-xs text-muted-foreground">
               <span>Preview</span>
               <span>Markdown</span>
             </div>
             <ScrollArea className="flex-1 p-8">
               {generatedContent ? (
                 <div className="prose prose-sm dark:prose-invert max-w-none">
                   <ReactMarkdown>{generatedContent}</ReactMarkdown>
                 </div>
               ) : (
                 <div className="h-full flex flex-col items-center justify-center text-muted-foreground opacity-50">
                   <FileUp className="h-12 w-12 mb-2" />
                   <p>Enter a topic and click generate</p>
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
                <h3 className="font-semibold text-lg">Upload Question Set</h3>
                <p className="text-muted-foreground">Drag and drop Markdown or CSV files</p>
              </div>
              <Button variant="outline">Select File</Button>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
