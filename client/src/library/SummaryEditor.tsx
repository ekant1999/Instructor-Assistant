import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Save, Download, Copy, CheckCircle2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface SummaryEditorProps {
  content: string;
  onSave: (markdown: string, action: 'save' | 'append') => void;
  onExport: (markdown: string) => void;
}

export function SummaryEditor({ content, onSave, onExport }: SummaryEditorProps) {
  const [markdown, setMarkdown] = useState(content);
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSave = (action: 'save' | 'append') => {
    onSave(markdown, action);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="h-14 border-b px-6 flex items-center justify-between bg-muted/5">
        <h3 className="font-semibold text-sm">Summary Output</h3>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            className="h-8 text-xs"
          >
            {copied ? (
              <>
                <CheckCircle2 className="h-3 w-3 mr-2" /> Copied
              </>
            ) : (
              <>
                <Copy className="h-3 w-3 mr-2" /> Copy
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onExport(markdown)}
            className="h-8 text-xs"
          >
            <Download className="h-3 w-3 mr-2" /> Export
          </Button>
        </div>
      </div>

      <Tabs defaultValue="preview" className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start rounded-none border-b h-auto p-0 bg-transparent">
          <TabsTrigger value="preview" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary text-sm">
            Preview
          </TabsTrigger>
          <TabsTrigger value="edit" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary text-sm">
            Edit Markdown
          </TabsTrigger>
        </TabsList>

        <TabsContent value="preview" className="flex-1 overflow-auto">
          <div className="p-8 max-w-3xl mx-auto">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{markdown}</ReactMarkdown>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="edit" className="flex-1 overflow-hidden">
          <Textarea
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            className="h-full w-full resize-none border-0 rounded-none focus-visible:ring-0 p-8 font-mono text-sm"
            placeholder="Edit your summary here..."
          />
        </TabsContent>
      </Tabs>

      <div className="h-14 border-t px-6 flex items-center justify-between bg-muted/5">
        <span className="text-xs text-muted-foreground">{markdown.length} characters</span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleSave('append')}
            className="h-8 text-xs"
          >
            ➕ Append to Note
          </Button>
          <Button
            onClick={() => handleSave('save')}
            size="sm"
            className="h-8 text-xs"
          >
            {saved ? (
              <>
                <CheckCircle2 className="h-3 w-3 mr-2" /> Saved
              </>
            ) : (
              <>
                <Save className="h-3 w-3 mr-2" /> Save as Note
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
