import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Save, Download, Copy, CheckCircle2, Bold, Italic, Heading2, List, Link as LinkIcon, Eye, Edit, Split } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Summary } from '@/shared/types';

interface EnhancedSummaryEditorProps {
  summary: Summary;
  onSave: (markdown: string) => void;
  onExport: () => void; // Opens export dialog
  onSaveToNotes: () => void;
  paperTitle?: string;
}

export function EnhancedSummaryEditor({ 
  summary, 
  onSave, 
  onExport, 
  onSaveToNotes,
  paperTitle 
}: EnhancedSummaryEditorProps) {
  const [markdown, setMarkdown] = useState(summary.content);
  const [viewMode, setViewMode] = useState<'edit' | 'preview' | 'split'>('preview');
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const [charCount, setCharCount] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const autoSaveIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    setMarkdown(summary.content);
  }, [summary.content]);

  useEffect(() => {
    const words = markdown.trim().split(/\s+/).filter(Boolean);
    setWordCount(words.length);
    setCharCount(markdown.length);
  }, [markdown]);

  // Auto-save every 30 seconds
  useEffect(() => {
    if (autoSaveIntervalRef.current) {
      clearInterval(autoSaveIntervalRef.current);
    }
    autoSaveIntervalRef.current = setInterval(() => {
      onSave(markdown);
    }, 30000);

    return () => {
      if (autoSaveIntervalRef.current) {
        clearInterval(autoSaveIntervalRef.current);
      }
    };
  }, [markdown, onSave]);

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSave = () => {
    onSave(markdown);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const insertMarkdown = (before: string, after: string = '') => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = markdown.substring(start, end);
    const newText = markdown.substring(0, start) + before + selectedText + after + markdown.substring(end);
    
    setMarkdown(newText);
    
    // Restore cursor position
    setTimeout(() => {
      textarea.focus();
      const newPos = start + before.length + selectedText.length + after.length;
      textarea.setSelectionRange(newPos, newPos);
    }, 0);
  };

  const markdownActions = {
    bold: () => insertMarkdown('**', '**'),
    italic: () => insertMarkdown('*', '*'),
    heading: () => insertMarkdown('## ', ''),
    list: () => insertMarkdown('- ', ''),
    link: () => insertMarkdown('[', '](url)')
  };

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="h-14 border-b px-6 flex items-center justify-between bg-muted/5">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-sm">Summary Editor</h3>
          {summary.isEdited && (
            <span className="text-xs bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 px-2 py-0.5 rounded">
              Edited
            </span>
          )}
        </div>
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
            onClick={onExport}
            className="h-8 text-xs"
          >
            <Download className="h-3 w-3 mr-2" /> Export
          </Button>
        </div>
      </div>

      {/* View Mode Toggle */}
      <div className="h-12 border-b px-6 flex items-center justify-between bg-muted/5">
        <div className="flex items-center gap-1">
          <Button
            variant={viewMode === 'edit' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('edit')}
            className="h-8 text-xs"
          >
            <Edit className="h-3 w-3 mr-1" /> Edit
          </Button>
          <Button
            variant={viewMode === 'preview' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('preview')}
            className="h-8 text-xs"
          >
            <Eye className="h-3 w-3 mr-1" /> Preview
          </Button>
          <Button
            variant={viewMode === 'split' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('split')}
            className="h-8 text-xs"
          >
            <Split className="h-3 w-3 mr-1" /> Split
          </Button>
        </div>

        {/* Markdown Toolbar */}
        {viewMode === 'edit' || viewMode === 'split' ? (
          <div className="flex items-center gap-1 border rounded-md p-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={markdownActions.bold}
              title="Bold"
            >
              <Bold className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={markdownActions.italic}
              title="Italic"
            >
              <Italic className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={markdownActions.heading}
              title="Heading"
            >
              <Heading2 className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={markdownActions.list}
              title="List"
            >
              <List className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={markdownActions.link}
              title="Link"
            >
              <LinkIcon className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : null}

        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>{wordCount} words</span>
          <span>{charCount} chars</span>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'preview' && (
          <div className="h-full overflow-auto p-8">
            <div className="max-w-3xl mx-auto prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{markdown}</ReactMarkdown>
            </div>
          </div>
        )}

        {viewMode === 'edit' && (
          <Textarea
            ref={textareaRef}
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            className="h-full w-full resize-none border-0 rounded-none focus-visible:ring-0 p-8 font-mono text-sm"
            placeholder="Edit your summary here..."
          />
        )}

        {viewMode === 'split' && (
          <div className="h-full flex">
            <div className="w-1/2 border-r overflow-hidden">
              <Textarea
                ref={textareaRef}
                value={markdown}
                onChange={(e) => setMarkdown(e.target.value)}
                className="h-full w-full resize-none border-0 rounded-none focus-visible:ring-0 p-8 font-mono text-sm"
                placeholder="Edit your summary here..."
              />
            </div>
            <div className="w-1/2 overflow-auto p-8">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{markdown}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="h-14 border-t px-6 flex items-center justify-between bg-muted/5">
        <span className="text-xs text-muted-foreground">
          Auto-saves every 30 seconds
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onSaveToNotes}
            className="h-8 text-xs"
          >
            Save to Notes
          </Button>
          <Button
            onClick={handleSave}
            size="sm"
            className="h-8 text-xs"
          >
            {saved ? (
              <>
                <CheckCircle2 className="h-3 w-3 mr-2" /> Saved
              </>
            ) : (
              <>
                <Save className="h-3 w-3 mr-2" /> Save
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
