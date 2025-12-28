import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { X, Upload, Plus, Loader2 } from 'lucide-react';
import { Paper } from '@/shared/types';
import { mapApiPaper } from '@/lib/mappers';
import { toast } from 'sonner';

interface UploadItem {
  id: string;
  type: 'doi' | 'url' | 'file';
  value: string;
  title?: string;
  progress?: number;
}

interface UploadPanelProps {
  onUpload: (papers: Paper[]) => void;
  onDownload: (input: { source: string; source_url?: string }) => Promise<any>;
}

export function UploadPanel({ onUpload, onDownload }: UploadPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [inputType, setInputType] = useState<'doi' | 'url'>('url');
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleAddUpload = () => {
    if (!inputValue.trim()) return;
    const newUpload: UploadItem = {
      id: Math.random().toString(),
      type: inputType,
      value: inputValue,
      progress: 0
    };
    setUploads([...uploads, newUpload]);
    setInputValue('');
  };

  const handleProcess = async () => {
    if (uploads.length === 0) return;
    setIsProcessing(true);

    const results: Paper[] = [];
    for (let i = 0; i < uploads.length; i++) {
      const upload = uploads[i];
      setUploads((u) => u.map((x, idx) => (idx === i ? { ...x, progress: 15 } : x)));
      try {
        const apiPaper = await onDownload({
          source: upload.value,
          source_url: upload.type === 'url' ? upload.value : undefined
        });
        results.push(mapApiPaper(apiPaper));
        setUploads((u) => u.map((x, idx) => (idx === i ? { ...x, progress: 100 } : x)));
      } catch (error) {
        toast.error(error instanceof Error ? error.message : 'Failed to download paper');
        setUploads((u) => u.map((x, idx) => (idx === i ? { ...x, progress: 0 } : x)));
      }
    }

    if (results.length > 0) {
      onUpload(results);
    }
    setUploads([]);
    setIsProcessing(false);
    setIsOpen(false);
  };

  const handleRemove = (id: string) => {
    setUploads(uploads.filter(u => u.id !== id));
  };

  if (!isOpen) {
    return (
      <div className="border-b px-6 py-3 flex justify-between items-center bg-muted/5">
        <span className="text-sm text-muted-foreground">Bulk upload papers</span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsOpen(true)}
          className="h-8 text-xs"
        >
          <Plus className="h-3 w-3 mr-2" /> Upload Papers
        </Button>
      </div>
    );
  }

  return (
    <div className="border-b bg-blue-50 dark:bg-blue-950/20 p-4 space-y-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">Upload Multiple Papers</h3>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsOpen(false)}
          className="h-6 w-6"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex gap-2">
        <div className="flex-1 flex gap-2">
          <div className="flex gap-1 bg-white dark:bg-black/20 p-1 rounded">
            <Button
              variant={inputType === 'url' ? 'default' : 'ghost'}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setInputType('url')}
            >
              URL
            </Button>
            <Button
              variant={inputType === 'doi' ? 'default' : 'ghost'}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setInputType('doi')}
            >
              DOI
            </Button>
          </div>
          <Input
            placeholder={inputType === 'doi' ? '10.1234/doi.example' : 'https://arxiv.org/...'}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddUpload()}
            className="h-8 text-sm"
          />
          <Button
            onClick={handleAddUpload}
            disabled={!inputValue.trim()}
            variant="outline"
            size="sm"
            className="h-8 text-xs"
          >
            <Plus className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {uploads.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">{uploads.length} items to upload</p>
          {uploads.map(u => (
            <Card key={u.id} className="p-3 bg-white dark:bg-black/30 border-white/20">
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{u.type.toUpperCase()}: {u.value}</p>
                  {u.progress !== undefined && u.progress < 100 && (
                    <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded mt-1 overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all"
                        style={{ width: `${u.progress}%` }}
                      />
                    </div>
                  )}
                  {u.progress === 100 && (
                    <p className="text-xs text-green-600 mt-1">✓ Ready</p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemove(u.id)}
                  disabled={isProcessing}
                  className="h-6 w-6 shrink-0"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            </Card>
          ))}
          <Button
            onClick={handleProcess}
            disabled={isProcessing}
            className="w-full h-8 text-xs"
          >
            {isProcessing ? (
              <>
                <Loader2 className="h-3 w-3 mr-2 animate-spin" /> Processing...
              </>
            ) : (
              <>
                <Upload className="h-3 w-3 mr-2" /> Upload All
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
