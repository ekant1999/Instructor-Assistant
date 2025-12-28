import React, { useState } from 'react';
import { PaperList } from './PaperList';
import { PdfPreview } from './PdfPreview';
import { UploadPanel } from './UploadPanel';
import { SectionSelector } from './SectionSelector';
import { SummarizePanel, SummarizeConfig } from './SummarizePanel';
import { SummaryEditor } from './SummaryEditor';
import { Paper } from '@/shared/types';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, Layers, Sparkles, BookOpen, Loader2 } from 'lucide-react';
import { useChatStore } from '@/chat/store';
import { downloadPaper } from '@/lib/api';

export default function LibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([
    {
      id: '1',
      title: 'Attention Is All You Need',
      source: 'ArXiv',
      year: '2017',
      abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...',
      sections: [
        { id: 'abstract', title: 'Abstract', content: 'The dominant sequence transduction models are based on complex recurrent...' },
        { id: 'intro', title: 'Introduction', content: 'Recurrent neural networks, long short-term memory...' },
        { id: 'methods', title: 'Methods', content: 'The overall architecture follows an encoder-decoder structure...' },
        { id: 'results', title: 'Results', content: 'We achieved state-of-the-art BLEU scores on the WMT 2014...' },
        { id: 'discussion', title: 'Discussion', content: 'The Transformer model demonstrates...' }
      ]
    },
    { id: '2', title: 'GPT-4 Technical Report', source: 'OpenAI', year: '2023' },
    { id: '3', title: 'Constitutional AI: Harmlessness from AI Feedback', source: 'Anthropic', year: '2022' }
  ]);
  const [selectedId, setSelectedId] = useState<string | undefined>('1');
  const [selectedSections, setSelectedSections] = useState<Set<string>>(new Set());
  const [summary, setSummary] = useState('');
  const [isSummarizing, setIsSummarizing] = useState(false);
  const sendMessage = useChatStore(state => state.sendMessage);

  const selectedPaper = papers.find(p => p.id === selectedId) || null;

  const handleAddPapers = (newPapers: Paper[]) => {
    setPapers([...newPapers, ...papers]);
  };

  const handleSelectSection = (sectionId: string) => {
    const newSet = new Set(selectedSections);
    if (newSet.has(sectionId)) {
      newSet.delete(sectionId);
    } else {
      newSet.add(sectionId);
    }
    setSelectedSections(newSet);
  };

  const handleSelectAll = () => {
    if (selectedPaper?.sections) {
      if (selectedSections.size === selectedPaper.sections.length) {
        setSelectedSections(new Set());
      } else {
        setSelectedSections(new Set(selectedPaper.sections.map(s => s.id)));
      }
    }
  };

  const handleSummarize = (config: SummarizeConfig) => {
    setIsSummarizing(true);
    
    // Simulate API call
    setTimeout(() => {
      let mockSummary = '';
      if (config.style === 'bullet') {
        mockSummary = `## Summary: ${selectedPaper?.title}

- Introduces the Transformer architecture based on self-attention mechanisms
- Eliminates recurrence and convolutions entirely
- Achieves superior performance on machine translation tasks
- Enables more parallelization during training
- Demonstrates effectiveness with different sequence lengths
- Establishes new SOTA on WMT 2014 English-to-German and English-to-French datasets`;
      } else if (config.style === 'detailed') {
        mockSummary = `## Detailed Summary: ${selectedPaper?.title}

### Background
The paper addresses limitations of existing sequence transduction models that rely on recurrent or convolutional networks, which inherently process sequences sequentially.

### Key Innovation
The authors propose the Transformer, which relies entirely on self-attention mechanisms to capture dependencies between input and output, without recurrence or convolutions.

### Architecture
The model follows an encoder-decoder structure where:
- Encoder: Stacked attention and feed-forward layers
- Decoder: Similar structure with additional attention over encoder outputs
- Positional encodings provide sequence order information

### Results
- Achieved state-of-the-art BLEU scores on WMT 2014 translation tasks
- Significantly faster training than baseline models
- Better generalization to longer sequences`;
      } else {
        mockSummary = `## Teaching Summary: ${selectedPaper?.title}

### Core Concept
Self-attention mechanism: Each element can directly attend to every other element in the sequence.

### Why It Matters
- Previous models (RNNs, CNNs) had bottlenecks in processing sequence information
- Transformers allow parallel processing and better long-range dependencies

### Key Terms to Remember
- **Attention Score**: Similarity between query and key vectors
- **Multi-Head Attention**: Multiple attention mechanisms running in parallel
- **Positional Encoding**: Encodes sequence position since there's no recurrence

### Exam Questions
1. How does self-attention differ from RNN attention?
2. Why is the Transformer more parallelizable?
3. What are the components of the Transformer encoder block?`;
      }
      
      if (config.customPrompt) {
        mockSummary += `\n\n---\n\n### Custom Notes\n${config.customPrompt}`;
      }

      setSummary(mockSummary);
      setIsSummarizing(false);
    }, 2000);
  };

  const handleSaveSummary = (markdown: string, action: 'save' | 'append'): void => {
    sendMessage(`I've generated a summary. ${action === 'save' ? 'Created a new note' : 'Appended to an existing note'} with the summary.`);
  };

  return (
    <div className="flex h-full w-full flex-col bg-background">
      {/* Upload Panel - Full Width */}
      <UploadPanel onUpload={handleAddPapers} onDownload={downloadPaper} />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - Papers List */}
        <div className="w-[320px] border-r bg-muted/5 flex flex-col h-full overflow-hidden">
          <div className="p-4 border-b sticky top-0 bg-background z-10">
            <h2 className="font-semibold text-sm flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Papers
            </h2>
            <p className="text-xs text-muted-foreground mt-1">{papers.length} papers in library</p>
          </div>

          <div className="flex-1 overflow-auto">
            <PaperList
              papers={papers}
              selectedId={selectedId}
              onSelect={(p) => {
                setSelectedId(p.id);
                setSelectedSections(new Set());
                setSummary('');
              }}
              onDelete={(id) => setPapers(papers.filter(p => p.id !== id))}
              onSummarize={(id) => {
                const p = papers.find(x => x.id === id);
                if (p) sendMessage(`Please summarize: "${p.title}"`);
              }}
            />
          </div>
        </div>

        {/* Main Panel - Tabs */}
        <div className="flex-1 h-full overflow-hidden">
          {selectedPaper ? (
            <Tabs defaultValue="preview" className="h-full flex flex-col">
              <TabsList className="w-full justify-start rounded-none border-b h-auto p-0 bg-transparent">
                <TabsTrigger value="preview" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
                  <FileText className="h-4 w-4 mr-2" />
                  Preview
                </TabsTrigger>
                <TabsTrigger value="sections" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
                  <Layers className="h-4 w-4 mr-2" />
                  Sections
                </TabsTrigger>
                <TabsTrigger value="summarize" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
                  <Sparkles className="h-4 w-4 mr-2" />
                  Summarize
                </TabsTrigger>
                {summary && (
                  <TabsTrigger value="output" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">
                    <BookOpen className="h-4 w-4 mr-2" />
                    Output
                  </TabsTrigger>
                )}
              </TabsList>

              <TabsContent value="preview" className="flex-1 overflow-hidden">
                <PdfPreview paper={selectedPaper} />
              </TabsContent>

              <TabsContent value="sections" className="flex-1 overflow-hidden">
                <SectionSelector
                  paper={selectedPaper}
                  selectedSections={selectedSections}
                  onSelectSection={handleSelectSection}
                  onSelectAll={handleSelectAll}
                  onCopy={(text) => navigator.clipboard.writeText(text)}
                />
              </TabsContent>

              <TabsContent value="summarize" className="flex-1 overflow-hidden">
                <SummarizePanel
                  selectedSectionCount={selectedSections.size}
                  onSummarize={handleSummarize}
                  isLoading={isSummarizing}
                />
              </TabsContent>

              {summary && (
                <TabsContent value="output" className="flex-1 overflow-hidden">
                  <SummaryEditor
                    content={summary}
                    onSave={handleSaveSummary}
                    onExport={(md: string) => {
                      const element = document.createElement('a');
                      element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(md));
                      element.setAttribute('download', `summary-${selectedPaper.id}.md`);
                      element.style.display = 'none';
                      document.body.appendChild(element);
                      element.click();
                      document.body.removeChild(element);
                    }}
                  />
                </TabsContent>
              )}
            </Tabs>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              <p>Select a paper to get started</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
