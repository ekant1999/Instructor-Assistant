import React, { useRef, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Paper, Document } from '@/shared/types';
import { BookOpen, FileText, Search, Upload, X } from 'lucide-react';

export interface UploadContext {
  id: string;
  filename: string;
  characters: number;
  preview: string;
  text: string;
}

interface DocumentSelectorProps {
  papers: Paper[];
  notes: Document[];
  uploads: UploadContext[];
  selectedPaperIds: Set<string>;
  selectedNoteIds: Set<string>;
  selectedUploadIds: Set<string>;
  onPaperToggle: (id: string) => void;
  onNoteToggle: (id: string) => void;
  onUploadToggle: (id: string) => void;
  onUpload: (files: FileList | File[]) => void;
  onClearSelection: () => void;
  onPaperSearchChange?: (query: string) => void;
  isUploading?: boolean;
}

export function DocumentSelector({
  papers,
  notes,
  uploads,
  selectedPaperIds,
  selectedNoteIds,
  selectedUploadIds,
  onPaperToggle,
  onNoteToggle,
  onUploadToggle,
  onUpload,
  onClearSelection,
  onPaperSearchChange,
  isUploading = false
}: DocumentSelectorProps) {
  const [paperSearch, setPaperSearch] = useState('');
  const [noteSearch, setNoteSearch] = useState('');
  const [noteTypeFilter, setNoteTypeFilter] = useState<string>('all');
  const [uploadSearch, setUploadSearch] = useState('');
  const uploadInputRef = useRef<HTMLInputElement>(null);
  
  // Notify parent when paper search changes (debounced)
  React.useEffect(() => {
    if (onPaperSearchChange) {
      const timer = setTimeout(() => {
        onPaperSearchChange(paperSearch);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [paperSearch, onPaperSearchChange]);

  // Backend now handles paper search, so no client-side filtering needed
  const filteredPapers = papers;

  const filteredNotes = notes.filter(n => {
    const matchesSearch = !noteSearch ||
      n.title.toLowerCase().includes(noteSearch.toLowerCase()) ||
      n.content.toLowerCase().includes(noteSearch.toLowerCase());
    
    const matchesType = noteTypeFilter === 'all' || n.type === noteTypeFilter;
    
    return matchesSearch && matchesType;
  });

  const filteredUploads = uploads.filter((upload) =>
    upload.filename.toLowerCase().includes(uploadSearch.toLowerCase())
  );

  const totalSelected = selectedPaperIds.size + selectedNoteIds.size + selectedUploadIds.size;

  return (
    <Card className="p-5 space-y-4 overflow-hidden">
      <div className="flex items-center justify-between gap-3 shrink-0">
        <h3 className="font-semibold text-sm flex items-center gap-2 flex-1 min-w-0">
          <BookOpen className="h-4 w-4 shrink-0" />
          <span className="whitespace-nowrap">Source Documents</span>
        </h3>
        {totalSelected > 0 && (
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {totalSelected} selected
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearSelection}
              className="h-7 text-xs px-2 shrink-0"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>

      <Tabs defaultValue="uploads" className="w-full">
        <TabsList className="grid w-full grid-cols-3 h-auto">
          <TabsTrigger value="uploads" className="text-xs py-2">
            Uploads ({uploads.length})
          </TabsTrigger>
          <TabsTrigger value="papers" className="text-xs py-2">
            Papers ({papers.length})
          </TabsTrigger>
          <TabsTrigger value="notes" className="text-xs py-2">
            Notes ({notes.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="uploads" className="space-y-3 mt-4">
          <div className="flex items-center gap-2">
            <input
              ref={uploadInputRef}
              type="file"
              accept=".pdf,.ppt,.pptx"
              multiple
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  onUpload(e.target.files);
                  e.target.value = '';
                }
              }}
              className="hidden"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => uploadInputRef.current?.click()}
              disabled={isUploading}
            >
              <Upload className="h-3 w-3 mr-2" />
              {isUploading ? 'Uploading...' : 'Upload PDF/PPT'}
            </Button>
            <span className="text-[11px] text-muted-foreground">
              PDF, PPT, PPTX
            </span>
          </div>

          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search uploads..."
              value={uploadSearch}
              onChange={(e) => setUploadSearch(e.target.value)}
              className="pl-8 h-8 text-xs"
            />
          </div>

          <div className="space-y-2 max-h-[250px] overflow-y-auto pr-2">
            {filteredUploads.map((upload) => (
              <div
                key={upload.id}
                className={`p-2 sm:p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedUploadIds.has(upload.id)
                    ? 'bg-primary/10 border-primary'
                    : 'hover:bg-muted/50'
                }`}
                onClick={() => onUploadToggle(upload.id)}
              >
                <div className="flex items-start gap-2">
                  <Checkbox
                    checked={selectedUploadIds.has(upload.id)}
                    onCheckedChange={() => onUploadToggle(upload.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{upload.filename}</p>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {upload.preview || 'No preview available'}
                    </p>
                    <p className="text-[10px] text-muted-foreground mt-1">
                      {upload.characters.toLocaleString()} chars
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {filteredUploads.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">
                No uploads yet
              </p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="papers" className="space-y-3 mt-4">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search papers..."
              value={paperSearch}
              onChange={(e) => setPaperSearch(e.target.value)}
              className="pl-8 h-8 text-xs"
            />
          </div>

          <div className="space-y-2 max-h-[250px] overflow-y-auto pr-2">
            {filteredPapers.map(paper => (
              <div
                key={paper.id}
                className={`p-2 sm:p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedPaperIds.has(paper.id)
                    ? 'bg-primary/10 border-primary'
                    : 'hover:bg-muted/50'
                }`}
                onClick={() => onPaperToggle(paper.id)}
              >
                <div className="flex items-start gap-2">
                  <Checkbox
                    checked={selectedPaperIds.has(paper.id)}
                    onCheckedChange={() => onPaperToggle(paper.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{paper.title}</p>
                    <p className="text-xs text-muted-foreground line-clamp-1">
                      {paper.source} • {paper.year}
                      {paper.authors && ` • ${paper.authors.split(',')[0]}`}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {filteredPapers.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">
                No papers found
              </p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="notes" className="space-y-3 mt-4">
          <div className="space-y-2">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search notes..."
                value={noteSearch}
                onChange={(e) => setNoteSearch(e.target.value)}
                className="pl-8 h-8 text-xs"
              />
            </div>

            <select
              value={noteTypeFilter}
              onChange={(e) => setNoteTypeFilter(e.target.value)}
              className="w-full h-8 text-xs border rounded-md px-2 bg-background"
            >
              <option value="all">All Types</option>
              <option value="summary">Summaries</option>
              <option value="qa_set">Q&A Sets</option>
              <option value="rag_response">RAG Responses</option>
              <option value="manual">Manual Notes</option>
            </select>
          </div>

          <div className="space-y-2 max-h-[250px] overflow-y-auto pr-2">
            {filteredNotes.map(note => (
              <div
                key={note.id}
                className={`p-2 sm:p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedNoteIds.has(note.id)
                    ? 'bg-primary/10 border-primary'
                    : 'hover:bg-muted/50'
                }`}
                onClick={() => onNoteToggle(note.id)}
              >
                <div className="flex items-start gap-2">
                  <Checkbox
                    checked={selectedNoteIds.has(note.id)}
                    onCheckedChange={() => onNoteToggle(note.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-1 sm:gap-2 mb-1">
                      <p className="text-sm font-medium truncate flex-1 min-w-0">{note.title}</p>
                      <Badge className="text-[10px] px-1.5 py-0 shrink-0">
                        {note.type.replace('_', ' ')}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {note.content.substring(0, 60)}...
                    </p>
                    {note.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {note.tags.slice(0, 2).map(tag => (
                          <span
                            key={tag}
                            className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {filteredNotes.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">
                No notes found
              </p>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </Card>
  );
}
