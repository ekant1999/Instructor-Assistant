import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { FileText, Plus, Link } from 'lucide-react';
import { Document } from '@/shared/types';

interface SaveSummaryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (action: 'new' | 'append', noteId?: string, title?: string, tags?: string[]) => void;
  existingNotes?: Document[];
  paperTitle?: string;
  paperAuthors?: string;
  paperYear?: string;
  agent?: string;
}

export function SaveSummaryModal({
  open,
  onOpenChange,
  onSave,
  existingNotes = [],
  paperTitle,
  paperAuthors,
  paperYear,
  agent
}: SaveSummaryModalProps) {
  const [action, setAction] = useState<'new' | 'append'>('new');
  const [selectedNoteId, setSelectedNoteId] = useState<string>('');
  const [title, setTitle] = useState(`Summary: ${paperTitle || 'Untitled'}`);
  const [tags, setTags] = useState('');

  const handleSave = () => {
    const tagArray = tags.split(',').map(t => t.trim()).filter(Boolean);
    if (action === 'append' && selectedNoteId) {
      onSave('append', selectedNoteId);
    } else {
      onSave('new', undefined, title, tagArray);
    }
    onOpenChange(false);
  };

  const defaultTags = [
    paperTitle,
    paperAuthors?.split(',')[0],
    paperYear,
    'summary',
    agent?.toLowerCase()
  ].filter(Boolean).join(', ');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Save Summary to Notes</DialogTitle>
          <DialogDescription>
            Choose how you want to save this summary
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <RadioGroup value={action} onValueChange={(v) => setAction(v as any)}>
            <div className="flex items-start space-x-2 p-3 border rounded-lg">
              <RadioGroupItem value="new" id="action-new" className="mt-1" />
              <Label htmlFor="action-new" className="cursor-pointer flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Plus className="h-4 w-4" />
                  <span className="font-medium">Save as New Note</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Creates a new note in the Notes section
                </p>
              </Label>
            </div>

            <div className="flex items-start space-x-2 p-3 border rounded-lg">
              <RadioGroupItem value="append" id="action-append" className="mt-1" />
              <Label htmlFor="action-append" className="cursor-pointer flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Link className="h-4 w-4" />
                  <span className="font-medium">Append to Existing Note</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Add to an existing note
                </p>
              </Label>
            </div>
          </RadioGroup>

          {action === 'new' && (
            <div className="space-y-3 pt-2">
              <div>
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Note title"
                />
              </div>
              <div>
                <Label htmlFor="tags">Tags (comma-separated)</Label>
                <Input
                  id="tags"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder={defaultTags}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Suggested: {defaultTags}
                </p>
              </div>
            </div>
          )}

          {action === 'append' && (
            <div className="space-y-2 pt-2">
              <Label>Select Note</Label>
              <Select value={selectedNoteId} onValueChange={setSelectedNoteId}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a note..." />
                </SelectTrigger>
                <SelectContent>
                  {existingNotes.map(note => (
                    <SelectItem key={note.id} value={note.id}>
                      <div className="flex items-center gap-2">
                        <FileText className="h-3 w-3" />
                        {note.title}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {existingNotes.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No existing notes. Create a new note instead.
                </p>
              )}
            </div>
          )}

          <div className="text-xs text-muted-foreground bg-muted/50 p-3 rounded-lg">
            <p className="font-medium mb-1">Metadata:</p>
            <ul className="space-y-1">
              {paperTitle && <li>Source: {paperTitle}</li>}
              {paperAuthors && <li>Authors: {paperAuthors}</li>}
              {paperYear && <li>Year: {paperYear}</li>}
              {agent && <li>Agent: {agent}</li>}
            </ul>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={action === 'append' && !selectedNoteId}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

