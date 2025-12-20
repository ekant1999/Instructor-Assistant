import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Loader2, Sparkles } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

export interface SummarizeConfig {
  scope: 'full' | 'selected' | 'multiple';
  method: 'local' | 'gpt' | 'gemini';
  style: 'bullet' | 'detailed' | 'teaching';
  customPrompt?: string;
}

interface SummarizePanelProps {
  selectedSectionCount: number;
  onSummarize: (config: SummarizeConfig) => void;
  isLoading: boolean;
}

export function SummarizePanel({
  selectedSectionCount,
  onSummarize,
  isLoading
}: SummarizePanelProps) {
  const [config, setConfig] = useState<SummarizeConfig>({
    scope: 'full',
    method: 'local',
    style: 'bullet',
    customPrompt: ''
  });

  const handleSummarize = () => {
    onSummarize(config);
  };

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6 max-w-2xl">
        {/* Scope */}
        <div className="space-y-3">
          <h3 className="font-semibold text-sm">Summarization Scope</h3>
          <RadioGroup value={config.scope} onValueChange={(v) => setConfig({ ...config, scope: v as any })}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="full" id="scope-full" />
              <Label htmlFor="scope-full" className="cursor-pointer flex-1">
                <span className="font-medium text-sm">Full Document</span>
                <p className="text-xs text-muted-foreground">Summarize entire paper</p>
              </Label>
            </div>
            <div className="flex items-center space-x-2" style={{ opacity: selectedSectionCount === 0 ? 0.5 : 1, pointerEvents: selectedSectionCount === 0 ? 'none' : 'auto' }}>
              <RadioGroupItem value="selected" id="scope-selected" disabled={selectedSectionCount === 0} />
              <Label htmlFor="scope-selected" className="cursor-pointer flex-1">
                <span className="font-medium text-sm">Selected Sections Only</span>
                <p className="text-xs text-muted-foreground">{selectedSectionCount} sections selected</p>
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="multiple" id="scope-multiple" />
              <Label htmlFor="scope-multiple" className="cursor-pointer flex-1">
                <span className="font-medium text-sm">Multiple Papers</span>
                <p className="text-xs text-muted-foreground">Summarize all papers in library</p>
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Method */}
        <div className="space-y-3">
          <h3 className="font-semibold text-sm">Summarization Method</h3>
          <RadioGroup value={config.method} onValueChange={(v) => setConfig({ ...config, method: v as any })}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="local" id="method-local" />
              <Label htmlFor="method-local" className="cursor-pointer flex-1">
                <span className="font-medium text-sm flex items-center gap-2">
                  🏠 Local Model (Qwen)
                </span>
                <p className="text-xs text-muted-foreground">Fast, no internet required</p>
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="gpt" id="method-gpt" />
              <Label htmlFor="method-gpt" className="cursor-pointer flex-1">
                <span className="font-medium text-sm">🔗 GPT (Simulated)</span>
                <p className="text-xs text-muted-foreground">High quality, web-based</p>
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="gemini" id="method-gemini" />
              <Label htmlFor="method-gemini" className="cursor-pointer flex-1">
                <span className="font-medium text-sm">✨ Gemini (Simulated)</span>
                <p className="text-xs text-muted-foreground">Multimodal, experimental</p>
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Style */}
        <div className="space-y-3">
          <h3 className="font-semibold text-sm">Summarization Style</h3>
          <RadioGroup value={config.style} onValueChange={(v) => setConfig({ ...config, style: v as any })}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="bullet" id="style-bullet" />
              <Label htmlFor="style-bullet" className="cursor-pointer flex-1">
                <span className="font-medium text-sm">Short Bullet Points</span>
                <p className="text-xs text-muted-foreground">Quick key takeaways</p>
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="detailed" id="style-detailed" />
              <Label htmlFor="style-detailed" className="cursor-pointer flex-1">
                <span className="font-medium text-sm">Detailed Academic</span>
                <p className="text-xs text-muted-foreground">In-depth structured summary</p>
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="teaching" id="style-teaching" />
              <Label htmlFor="style-teaching" className="cursor-pointer flex-1">
                <span className="font-medium text-sm">Teaching / Exam-Focused</span>
                <p className="text-xs text-muted-foreground">Key concepts & review questions</p>
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Custom Prompt */}
        <div className="space-y-3">
          <h3 className="font-semibold text-sm">Custom Instruction (Optional)</h3>
          <Textarea
            placeholder="Add any custom notes or requirements for the summary..."
            value={config.customPrompt || ''}
            onChange={(e) => setConfig({ ...config, customPrompt: e.target.value })}
            className="min-h-[100px]"
          />
        </div>

        {/* Action */}
        <Button
          onClick={handleSummarize}
          disabled={isLoading}
          className="w-full h-10"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Generating Summary...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4 mr-2" /> Generate Summary
            </>
          )}
        </Button>

        <Card className="p-3 bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900">
          <p className="text-xs text-blue-900 dark:text-blue-100">
            💡 <strong>Tip:</strong> Select specific sections above to summarize only those parts. Choose "Teaching" style for exam prep questions.
          </p>
        </Card>
      </div>
    </ScrollArea>
  );
}
