import React, { useState } from 'react';
import { Note } from '@/shared/types';
import { NotesEditor } from './NotesEditor';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Plus, Trash2, Save, Tag, Bold, Italic, Heading2, List } from 'lucide-react';
import { useChatStore } from '@/chat/store';

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([
    { id: '1', title: 'Lecture 1: Introduction to AI', content: '# Lecture 1\n\nKey topics covered today...', tags: ['AI', 'Intro'], updatedAt: Date.now() },
    { id: '2', title: 'Research Ideas', content: '- Explore transformers for biological sequences\n- Read Vaswani et al.', tags: ['Research'], updatedAt: Date.now() - 100000 },
  ]);
  const [selectedId, setSelectedId] = useState<string | null>('1');
  const [search, setSearch] = useState('');
  const { messages } = useChatStore();

  const activeNote = notes.find(n => n.id === selectedId);

  const handleCreate = () => {
    const newNote: Note = {
      id: Math.random().toString(),
      title: 'Untitled Note',
      content: '',
      tags: [],
      updatedAt: Date.now()
    };
    setNotes([newNote, ...notes]);
    setSelectedId(newNote.id);
  };

  const handleUpdate = (content: string) => {
    if (selectedId) {
      setNotes(notes.map(n => n.id === selectedId ? { ...n, content, updatedAt: Date.now() } : n));
    }
  };

  const handleUpdateTags = (tagsString: string) => {
    if (selectedId) {
      const tags = tagsString.split(',').map(t => t.trim()).filter(t => t.length > 0);
      setNotes(notes.map(n => n.id === selectedId ? { ...n, tags } : n));
    }
  };

  const filteredNotes = notes.filter(n => 
    n.title.toLowerCase().includes(search.toLowerCase()) || 
    n.content.toLowerCase().includes(search.toLowerCase()) ||
    n.tags.some(tag => tag.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="flex h-full w-full">
      {/* Sidebar */}
      <div className="w-[300px] border-r bg-muted/10 flex flex-col h-full">
        <div className="p-4 border-b space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Notes</h2>
            <Button size="icon" variant="ghost" onClick={handleCreate}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input 
              placeholder="Search notes..." 
              className="pl-8 bg-background" 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          {filteredNotes.map(note => (
             <div 
               key={note.id}
               onClick={() => setSelectedId(note.id)}
               className={`p-4 border-b cursor-pointer hover:bg-muted/50 transition-colors ${selectedId === note.id ? 'bg-secondary border-l-2 border-l-primary' : ''}`}
             >
               <h3 className="font-medium text-sm truncate">{note.title}</h3>
               {note.tags.length > 0 && (
                 <div className="flex flex-wrap gap-1 mt-2">
                   {note.tags.slice(0, 2).map(tag => (
                     <span key={tag} className="inline-block px-2 py-0.5 text-[10px] bg-primary/10 text-primary rounded">
                       {tag}
                     </span>
                   ))}
                   {note.tags.length > 2 && <span className="text-[10px] text-muted-foreground">+{note.tags.length - 2}</span>}
                 </div>
               )}
               <p className="text-xs text-muted-foreground mt-2 truncate">
                 {note.content.substring(0, 50) || "No content"}
               </p>
               <div className="text-[10px] text-muted-foreground mt-2 flex justify-between">
                 <span>{new Date(note.updatedAt).toLocaleDateString()}</span>
                 {selectedId === note.id && (
                    <Trash2 
                      className="h-3 w-3 hover:text-destructive" 
                      onClick={(e) => {
                        e.stopPropagation();
                        setNotes(notes.filter(n => n.id !== note.id));
                        if (selectedId === note.id) setSelectedId(null);
                      }}
                    />
                 )}
               </div>
             </div>
          ))}
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 h-full">
        {activeNote ? (
          <div className="h-full flex flex-col">
            <div className="h-14 border-b flex items-center px-6 justify-between">
              <input 
                value={activeNote.title}
                onChange={(e) => setNotes(notes.map(n => n.id === activeNote.id ? { ...n, title: e.target.value } : n))}
                className="text-lg font-semibold bg-transparent border-none focus:outline-none w-full"
              />
              <Button size="sm" variant="ghost" className="text-muted-foreground">
                <Save className="h-4 w-4 mr-2" /> Saved
              </Button>
            </div>

            {/* Toolbar */}
            <div className="h-12 border-b bg-muted/5 px-4 flex items-center gap-1">
              <Button size="icon" variant="ghost" className="h-8 w-8 text-sm" title="Bold"><Bold className="h-3.5 w-3.5" /></Button>
              <Button size="icon" variant="ghost" className="h-8 w-8 text-sm" title="Italic"><Italic className="h-3.5 w-3.5" /></Button>
              <Button size="icon" variant="ghost" className="h-8 w-8 text-sm" title="Heading"><Heading2 className="h-3.5 w-3.5" /></Button>
              <Button size="icon" variant="ghost" className="h-8 w-8 text-sm" title="List"><List className="h-3.5 w-3.5" /></Button>
              <div className="flex-1" />
              <span className="text-xs text-muted-foreground">{activeNote.content.length} chars</span>
            </div>

            {/* Tags */}
            <div className="h-10 border-b px-4 flex items-center gap-2 bg-muted/5">
              <Tag className="h-3.5 w-3.5 text-muted-foreground" />
              <Input 
                placeholder="Add tags (comma-separated)" 
                value={activeNote.tags.join(', ')}
                onChange={(e) => handleUpdateTags(e.target.value)}
                className="border-0 bg-transparent h-8 text-xs placeholder-muted-foreground/50"
              />
            </div>

            <div className="flex-1 overflow-hidden">
               <NotesEditor content={activeNote.content} onChange={handleUpdate} />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
             <p>Select or create a note</p>
          </div>
        )}
      </div>
    </div>
  );
}
