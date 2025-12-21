import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Download, FileText, FileCode, File, FileType } from 'lucide-react';

interface ExportSummaryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onExport: (format: 'pdf' | 'txt' | 'latex' | 'markdown' | 'docx', content: string, metadata: any) => void;
  content: string;
  paperTitle?: string;
  authors?: string;
  year?: string;
  agent?: string;
  style?: string;
}

export function ExportSummaryDialog({
  open,
  onOpenChange,
  onExport,
  content,
  paperTitle,
  authors,
  year,
  agent,
  style
}: ExportSummaryDialogProps) {
  const [format, setFormat] = useState<'pdf' | 'txt' | 'latex' | 'markdown' | 'docx'>('pdf');

  const formatOptions = [
    { value: 'pdf', label: 'PDF', icon: FileText, desc: 'Formatted document' },
    { value: 'txt', label: 'TXT', icon: File, desc: 'Plain text' },
    { value: 'latex', label: 'LaTeX', icon: FileCode, desc: 'Academic format' },
    { value: 'markdown', label: 'Markdown', icon: FileType, desc: 'Raw markdown' },
    { value: 'docx', label: 'DOCX', icon: FileText, desc: 'Microsoft Word' }
  ];

  const handleExport = () => {
    const metadata = {
      paperTitle,
      authors,
      year,
      agent,
      style,
      generatedAt: new Date().toISOString()
    };
    onExport(format, content, metadata);
    onOpenChange(false);
  };

  const getFilename = () => {
    const safeTitle = (paperTitle || 'Summary').replace(/[^a-z0-9]/gi, '_').substring(0, 50);
    const date = new Date().toISOString().split('T')[0];
    const ext = format === 'markdown' ? 'md' : format;
    return `${safeTitle}_Summary_${date}.${ext}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Export Summary</DialogTitle>
          <DialogDescription>
            Choose export format for your summary
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Format</label>
            <Select value={format} onValueChange={(v) => setFormat(v as any)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {formatOptions.map(opt => {
                  const Icon = opt.icon;
                  return (
                    <SelectItem key={opt.value} value={opt.value}>
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4" />
                        <div>
                          <div className="font-medium">{opt.label}</div>
                          <div className="text-xs text-muted-foreground">{opt.desc}</div>
                        </div>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>

          <div className="bg-muted/50 p-3 rounded-lg space-y-2 text-sm">
            <div className="font-medium">Export Details</div>
            <div className="text-xs text-muted-foreground space-y-1">
              <div>Filename: <code className="bg-background px-1 rounded">{getFilename()}</code></div>
              {paperTitle && <div>Paper: {paperTitle}</div>}
              {authors && <div>Authors: {authors}</div>}
              {year && <div>Year: {year}</div>}
              {agent && <div>Agent: {agent}</div>}
              {style && <div>Style: {style}</div>}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export {format.toUpperCase()}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

