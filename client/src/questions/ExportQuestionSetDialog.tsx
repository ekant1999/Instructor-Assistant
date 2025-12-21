import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Download, FileText, FileCode, File, FileType, Code } from 'lucide-react';
import { QuestionSet } from '@/shared/types';

interface ExportQuestionSetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onExport: (format: string, options: ExportOptions) => void;
  questionSet: QuestionSet | null;
}

interface ExportOptions {
  includeAnswers: boolean;
  includeExplanations: boolean;
  separateAnswerKey: boolean;
}

export function ExportQuestionSetDialog({
  open,
  onOpenChange,
  onExport,
  questionSet
}: ExportQuestionSetDialogProps) {
  const [format, setFormat] = useState<string>('pdf');
  const [options, setOptions] = useState<ExportOptions>({
    includeAnswers: false,
    includeExplanations: true,
    separateAnswerKey: true
  });

  const formatOptions = [
    { value: 'pdf', label: 'PDF', icon: FileText, desc: 'Formatted quiz with answer key' },
    { value: 'txt', label: 'TXT', icon: File, desc: 'Plain text version' },
    { value: 'markdown', label: 'Markdown', icon: FileType, desc: 'Markdown format' },
    { value: 'canvas', label: 'Canvas LMS', icon: Code, desc: 'Canvas quiz import format' },
    { value: 'moodle', label: 'Moodle XML', icon: FileCode, desc: 'Moodle import format' },
    { value: 'json', label: 'JSON', icon: Code, desc: 'Structured data format' }
  ];

  const handleExport = () => {
    onExport(format, options);
    onOpenChange(false);
  };

  const getFilename = () => {
    const safeTitle = (questionSet?.title || 'QuestionSet').replace(/[^a-z0-9]/gi, '_').substring(0, 50);
    const date = new Date().toISOString().split('T')[0];
    const count = questionSet?.questions.length || 0;
    const ext = format === 'markdown' ? 'md' : format === 'json' ? 'json' : format;
    return `QSet_${safeTitle}_${date}_${count}Q.${ext}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Export Question Set</DialogTitle>
          <DialogDescription>
            Choose export format and options for your question set
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Format</label>
            <Select value={format} onValueChange={setFormat}>
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

          <div className="space-y-3">
            <label className="text-sm font-medium">Export Options</label>
            
            <div className="flex items-center gap-2">
              <Checkbox
                id="include-answers"
                checked={options.includeAnswers}
                onCheckedChange={(checked) =>
                  setOptions({ ...options, includeAnswers: checked as boolean })
                }
              />
              <Label htmlFor="include-answers" className="text-sm cursor-pointer">
                Include answers in document
              </Label>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="include-explanations"
                checked={options.includeExplanations}
                onCheckedChange={(checked) =>
                  setOptions({ ...options, includeExplanations: checked as boolean })
                }
              />
              <Label htmlFor="include-explanations" className="text-sm cursor-pointer">
                Include explanations
              </Label>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="separate-key"
                checked={options.separateAnswerKey}
                onCheckedChange={(checked) =>
                  setOptions({ ...options, separateAnswerKey: checked as boolean })
                }
                disabled={options.includeAnswers}
              />
              <Label htmlFor="separate-key" className="text-sm cursor-pointer">
                Create separate answer key file
              </Label>
            </div>
          </div>

          <div className="bg-muted/50 p-3 rounded-lg space-y-2 text-sm">
            <div className="font-medium">Export Details</div>
            <div className="text-xs text-muted-foreground space-y-1">
              <div>Filename: <code className="bg-background px-1 rounded">{getFilename()}</code></div>
              {questionSet && (
                <>
                  <div>Title: {questionSet.title}</div>
                  <div>Questions: {questionSet.questions.length}</div>
                  {questionSet.sourceDocumentIds && (
                    <div>Sources: {questionSet.sourceDocumentIds.length} documents</div>
                  )}
                </>
              )}
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

