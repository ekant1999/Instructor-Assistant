import React, { useState } from 'react';
import { PaperList } from './PaperList';
import { PdfPreview } from './PdfPreview';
import { Paper } from '@/shared/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Plus, Link as LinkIcon, Upload } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from '@/components/ui/label';
import { useChatStore } from '@/chat/store';
import { useLocation } from 'wouter';

export default function LibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([
    { id: '1', title: 'Attention Is All You Need', source: 'ArXiv', year: '2017', abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...' },
    { id: '2', title: 'GPT-4 Technical Report', source: 'OpenAI', year: '2023' },
    { id: '3', title: 'Constitutional AI: Harmlessness from AI Feedback', source: 'Anthropic', year: '2022' }
  ]);
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const [, setLocation] = useLocation();
  const sendMessage = useChatStore(state => state.sendMessage);

  const handleAddPaper = (e: React.FormEvent) => {
    e.preventDefault();
    const newPaper: Paper = {
      id: Math.random().toString(),
      title: 'New Research Paper (Uploaded)',
      source: 'Upload',
      year: '2024'
    };
    setPapers([newPaper, ...papers]);
  };

  const handleSummarize = (id: string) => {
    const paper = papers.find(p => p.id === id);
    if (paper) {
      sendMessage(`Please summarize the paper: "${paper.title}"`);
      setLocation('/');
    }
  };

  const selectedPaper = papers.find(p => p.id === selectedId) || null;

  return (
    <div className="flex h-full w-full">
      {/* Sidebar List */}
      <div className="w-[350px] border-r bg-background flex flex-col h-full">
        <div className="p-4 border-b flex items-center justify-between sticky top-0 bg-background z-10">
          <h2 className="font-semibold">Library</h2>
          <Dialog>
            <DialogTrigger asChild>
              <Button size="sm" className="h-8">
                <Plus className="h-4 w-4 mr-2" /> Add Paper
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add to Library</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleAddPaper} className="space-y-4 pt-4">
                <div className="space-y-2">
                  <Label>Paper URL or DOI</Label>
                  <div className="flex gap-2">
                    <Input placeholder="https://arxiv.org/..." />
                    <Button type="button" variant="outline" size="icon"><LinkIcon className="h-4 w-4" /></Button>
                  </div>
                </div>
                <div className="relative">
                  <div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div>
                  <div className="relative flex justify-center text-xs uppercase"><span className="bg-background px-2 text-muted-foreground">Or upload</span></div>
                </div>
                <div className="border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center text-muted-foreground hover:bg-muted/50 transition-colors cursor-pointer">
                  <Upload className="h-8 w-8 mb-2" />
                  <span className="text-sm">Drag & drop PDF here</span>
                </div>
                <Button type="submit" className="w-full">Add to Library</Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
        
        <div className="flex-1 overflow-auto">
          <PaperList 
            papers={papers} 
            selectedId={selectedId}
            onSelect={(p) => setSelectedId(p.id)}
            onDelete={(id) => setPapers(papers.filter(p => p.id !== id))}
            onSummarize={handleSummarize}
          />
        </div>
      </div>

      {/* Main Preview */}
      <div className="flex-1 h-full overflow-hidden">
        <PdfPreview paper={selectedPaper} />
      </div>
    </div>
  );
}
