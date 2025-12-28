import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Document } from '@/shared/types';
import { NotesEditor } from './NotesEditor';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search, Plus, Trash2, Save, Tag, FileText, MessageSquare, Network, BookOpen, Filter, Link2 } from 'lucide-react';
import { format } from 'date-fns';
import { createNote, deleteNote, listNotes, updateNote } from '@/lib/api';
import { mapApiNote } from '@/lib/mappers';
import { toast } from 'sonner';

export default function EnhancedNotesPage() {
  const [documents, setDocuments] = useState<Document[]>([]);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [tagFilter, setTagFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingSaveRef = useRef<{ id: string; updates: { title?: string; body?: string; tags?: string[] } } | null>(null);

  const activeDocument = documents.find(d => d.id === selectedId);

  useEffect(() => {
    let isMounted = true;
    async function loadNotes() {
      setIsLoading(true);
      try {
        const rows = await listNotes();
        if (!isMounted) return;
        const mapped = rows.map(mapApiNote);
        setDocuments(mapped);
        if (mapped.length > 0) {
          setSelectedId(mapped[0].id);
        }
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Failed to load notes');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    loadNotes();
    return () => {
      isMounted = false;
    };
  }, []);

  // Extract unique tags
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    documents.forEach(doc => doc.tags.forEach(tag => tagSet.add(tag)));
    return Array.from(tagSet).sort();
  }, [documents]);

  // Filter documents
  const filteredDocuments = useMemo(() => {
    return documents.filter(doc => {
      const matchesSearch = !search || 
        doc.title.toLowerCase().includes(search.toLowerCase()) ||
        doc.content.toLowerCase().includes(search.toLowerCase()) ||
        doc.tags.some(tag => tag.toLowerCase().includes(search.toLowerCase()));
      
      const matchesType = typeFilter === 'all' || doc.type === typeFilter;
      const matchesTag = tagFilter === 'all' || doc.tags.includes(tagFilter);
      
      return matchesSearch && matchesType && matchesTag;
    });
  }, [documents, search, typeFilter, tagFilter]);

  // Group by type
  const documentsByType = useMemo(() => {
    const groups: Record<string, Document[]> = {
      summary: [],
      qa_set: [],
      rag_response: [],
      manual: []
    };
    
    filteredDocuments.forEach(doc => {
      if (groups[doc.type]) {
        groups[doc.type].push(doc);
      }
    });
    
    return groups;
  }, [filteredDocuments]);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'summary': return BookOpen;
      case 'qa_set': return MessageSquare;
      case 'rag_response': return Network;
      case 'manual': return FileText;
      default: return FileText;
    }
  };

  const getTypeBadgeColor = (type: string) => {
    switch (type) {
      case 'summary': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'qa_set': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'rag_response': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'manual': return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const scheduleSave = (id: string, updates: { title?: string; body?: string; tags?: string[] }) => {
    const current = pendingSaveRef.current;
    if (current && current.id === id) {
      pendingSaveRef.current = { id, updates: { ...current.updates, ...updates } };
    } else {
      pendingSaveRef.current = { id, updates };
    }

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      const pending = pendingSaveRef.current;
      if (!pending) return;
      pendingSaveRef.current = null;
      try {
        const updated = await updateNote(Number(pending.id), pending.updates);
        setDocuments((prev) => prev.map((doc) => (doc.id === pending.id ? mapApiNote(updated) : doc)));
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Failed to save note');
      }
    }, 600);
  };

  const handleCreate = async () => {
    try {
      const created = await createNote({ title: 'Untitled Note', body: '', tags: [] });
      const doc = mapApiNote(created);
      setDocuments((prev) => [doc, ...prev]);
      setSelectedId(doc.id);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create note');
    }
  };

  const handleUpdate = (content: string) => {
    if (selectedId) {
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === selectedId ? { ...d, content, updatedAt: Date.now() } : d
        )
      );
      scheduleSave(selectedId, { body: content });
    }
  };

  const handleUpdateTags = (tagsString: string) => {
    if (selectedId) {
      const tags = tagsString.split(',').map((t) => t.trim()).filter(Boolean);
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === selectedId ? { ...d, tags, updatedAt: Date.now() } : d
        )
      );
      scheduleSave(selectedId, { tags });
    }
  };

  const handleUpdateTitle = (title: string) => {
    if (selectedId) {
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === selectedId ? { ...d, title, updatedAt: Date.now() } : d
        )
      );
      scheduleSave(selectedId, { title });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteNote(Number(id));
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (selectedId === id) setSelectedId(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete note');
    }
  };

  return (
    <div className="flex h-full w-full">
      {/* Sidebar */}
      <div className="w-[320px] border-r bg-muted/10 flex flex-col h-full">
        <div className="p-4 border-b space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Documents</h2>
            <Button size="icon" variant="ghost" onClick={handleCreate}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input 
              placeholder="Search documents..." 
              className="pl-8 bg-background" 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="summary">Summaries</SelectItem>
                <SelectItem value="qa_set">Q&A Sets</SelectItem>
                <SelectItem value="rag_response">RAG Responses</SelectItem>
                <SelectItem value="manual">Manual Notes</SelectItem>
              </SelectContent>
            </Select>

            <Select value={tagFilter} onValueChange={setTagFilter}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Filter by tag" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Tags</SelectItem>
                {allTags.map(tag => (
                  <SelectItem key={tag} value={tag}>{tag}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Document Groups */}
        <div className="flex-1 overflow-auto">
          {typeFilter === 'all' ? (
            <div className="space-y-4 p-4">
              <div>
                <div className="flex items-center justify-between mb-2 px-2">
                  <span className="text-xs font-semibold text-muted-foreground">
                    Summaries ({documentsByType.summary.length})
                  </span>
                </div>
                {documentsByType.summary.map(doc => (
                  <DocumentItem
                    key={doc.id}
                    doc={doc}
                    isSelected={selectedId === doc.id}
                    onClick={() => setSelectedId(doc.id)}
                    onDelete={() => handleDelete(doc.id)}
                    getTypeIcon={getTypeIcon}
                    getTypeBadgeColor={getTypeBadgeColor}
                  />
                ))}
              </div>

              <div>
                <div className="flex items-center justify-between mb-2 px-2">
                  <span className="text-xs font-semibold text-muted-foreground">
                    Q&A Sets ({documentsByType.qa_set.length})
                  </span>
                </div>
                {documentsByType.qa_set.map(doc => (
                  <DocumentItem
                    key={doc.id}
                    doc={doc}
                    isSelected={selectedId === doc.id}
                    onClick={() => setSelectedId(doc.id)}
                    onDelete={() => handleDelete(doc.id)}
                    getTypeIcon={getTypeIcon}
                    getTypeBadgeColor={getTypeBadgeColor}
                  />
                ))}
              </div>

              <div>
                <div className="flex items-center justify-between mb-2 px-2">
                  <span className="text-xs font-semibold text-muted-foreground">
                    RAG Responses ({documentsByType.rag_response.length})
                  </span>
                </div>
                {documentsByType.rag_response.map(doc => (
                  <DocumentItem
                    key={doc.id}
                    doc={doc}
                    isSelected={selectedId === doc.id}
                    onClick={() => setSelectedId(doc.id)}
                    onDelete={() => handleDelete(doc.id)}
                    getTypeIcon={getTypeIcon}
                    getTypeBadgeColor={getTypeBadgeColor}
                  />
                ))}
              </div>

              <div>
                <div className="flex items-center justify-between mb-2 px-2">
                  <span className="text-xs font-semibold text-muted-foreground">
                    Manual Notes ({documentsByType.manual.length})
                  </span>
                </div>
                {documentsByType.manual.map(doc => (
                  <DocumentItem
                    key={doc.id}
                    doc={doc}
                    isSelected={selectedId === doc.id}
                    onClick={() => setSelectedId(doc.id)}
                    onDelete={() => handleDelete(doc.id)}
                    getTypeIcon={getTypeIcon}
                    getTypeBadgeColor={getTypeBadgeColor}
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="p-4 space-y-2">
              {filteredDocuments.map(doc => (
                <DocumentItem
                  key={doc.id}
                  doc={doc}
                  isSelected={selectedId === doc.id}
                  onClick={() => setSelectedId(doc.id)}
                  onDelete={() => handleDelete(doc.id)}
                  getTypeIcon={getTypeIcon}
                  getTypeBadgeColor={getTypeBadgeColor}
                />
              ))}
            </div>
          )}

          {filteredDocuments.length === 0 && (
            <div className="text-center py-10 text-muted-foreground text-sm px-4">
              No documents found
            </div>
          )}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 h-full">
        {activeDocument ? (
          <div className="h-full flex flex-col">
            <div className="h-14 border-b flex items-center px-6 justify-between">
              <input 
                value={activeDocument.title}
                onChange={(e) => handleUpdateTitle(e.target.value)}
                className="text-lg font-semibold bg-transparent border-none focus:outline-none w-full"
              />
              <div className="flex items-center gap-2">
                <Badge className={getTypeBadgeColor(activeDocument.type)}>
                  {activeDocument.type.replace('_', ' ')}
                </Badge>
                <Button size="sm" variant="ghost" className="text-muted-foreground">
                  <Save className="h-4 w-4 mr-2" /> Saved
                </Button>
              </div>
            </div>

            {/* Metadata Bar */}
            <div className="h-10 border-b px-6 flex items-center gap-4 text-xs text-muted-foreground bg-muted/5">
              <span>Created: {format(new Date(activeDocument.createdAt), 'MMM d, yyyy')}</span>
              <span>Updated: {format(new Date(activeDocument.updatedAt), 'MMM d, yyyy')}</span>
              {activeDocument.wordCount && <span>{activeDocument.wordCount} words</span>}
              {activeDocument.questionCount && <span>{activeDocument.questionCount} questions</span>}
              {activeDocument.agent && <span>Agent: {activeDocument.agent}</span>}
            </div>

            {/* Source Links */}
            {activeDocument.sourceLinks && activeDocument.sourceLinks.length > 0 && (
              <div className="h-10 border-b px-6 flex items-center gap-2 text-xs bg-muted/5">
                <Link2 className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">Sources:</span>
                {activeDocument.sourceLinks.map((link, idx) => (
                  <Button
                    key={idx}
                    variant="link"
                    size="sm"
                    className="h-6 text-xs p-0"
                    onClick={() => {
                      // Navigate to source
                      if (link.type === 'paper') {
                        window.location.href = `/library?paper=${link.id}`;
                      }
                    }}
                  >
                    {link.title}
                  </Button>
                ))}
              </div>
            )}

            {/* Tags */}
            <div className="h-10 border-b px-4 flex items-center gap-2 bg-muted/5">
              <Tag className="h-3.5 w-3.5 text-muted-foreground" />
              <Input 
                placeholder="Add tags (comma-separated)" 
                value={activeDocument.tags.join(', ')}
                onChange={(e) => handleUpdateTags(e.target.value)}
                className="border-0 bg-transparent h-8 text-xs placeholder-muted-foreground/50"
              />
            </div>

            <div className="flex-1 overflow-hidden">
              <NotesEditor content={activeDocument.content} onChange={handleUpdate} />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <FileText className="h-12 w-12 mb-4 opacity-50" />
            <p>Select or create a document</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface DocumentItemProps {
  doc: Document;
  isSelected: boolean;
  onClick: () => void;
  onDelete: () => void;
  getTypeIcon: (type: string) => any;
  getTypeBadgeColor: (type: string) => string;
}

function DocumentItem({ doc, isSelected, onClick, onDelete, getTypeIcon, getTypeBadgeColor }: DocumentItemProps) {
  const Icon = getTypeIcon(doc.type);
  
  return (
    <div 
      onClick={onClick}
      className={`p-3 mb-2 border rounded-lg cursor-pointer hover:bg-muted/50 transition-colors ${
        isSelected ? 'bg-secondary border-l-2 border-l-primary' : ''
      }`}
    >
      <div className="flex items-start gap-2">
        <Icon className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium text-sm truncate">{doc.title}</h3>
            <Badge className={`text-[10px] px-1.5 py-0 ${getTypeBadgeColor(doc.type)}`}>
              {doc.type.replace('_', ' ')}
            </Badge>
          </div>
          {doc.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-1">
              {doc.tags.slice(0, 2).map(tag => (
                <span key={tag} className="inline-block px-1.5 py-0.5 text-[10px] bg-primary/10 text-primary rounded">
                  {tag}
                </span>
              ))}
              {doc.tags.length > 2 && (
                <span className="text-[10px] text-muted-foreground">+{doc.tags.length - 2}</span>
              )}
            </div>
          )}
          <p className="text-xs text-muted-foreground truncate">
            {doc.content.substring(0, 50) || "No content"}
          </p>
          <div className="text-[10px] text-muted-foreground mt-1 flex justify-between">
            <span>{format(new Date(doc.updatedAt), 'MMM d, yyyy')}</span>
            {isSelected && (
              <Trash2 
                className="h-3 w-3 hover:text-destructive" 
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
