import React, { useState } from 'react';
import { Note } from '@/shared/types';
import { NotesEditor } from './NotesEditor';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Plus, Trash2, Save } from 'lucide-react';
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

  const filteredNotes = notes.filter(n => 
    n.title.toLowerCase().includes(search.toLowerCase()) || 
    n.content.toLowerCase().includes(search.toLowerCase())
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
               <p className="text-xs text-muted-foreground mt-1 truncate">
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
