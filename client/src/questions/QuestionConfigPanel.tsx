import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Plus, Minus } from 'lucide-react';

export interface QuestionTypeConfig {
  type: 'multiple-choice' | 'true-false' | 'short-answer' | 'essay';
  enabled: boolean;
  count: number;
  options?: {
    numOptions?: number; // For MC
    includeAllOfAbove?: boolean;
    includeNoneOfAbove?: boolean;
    includeExplanation?: boolean; // For TF
    expectedLength?: string; // For short answer
    includeSampleAnswer?: boolean; // For short answer
    wordCountRange?: { min: number; max: number }; // For essay
    includeRubric?: boolean; // For essay
  };
}

interface QuestionConfigPanelProps {
  configs: QuestionTypeConfig[];
  onChange: (configs: QuestionTypeConfig[]) => void;
}

export function QuestionConfigPanel({ configs, onChange }: QuestionConfigPanelProps) {
  const updateConfig = (index: number, updates: Partial<QuestionTypeConfig>) => {
    const newConfigs = [...configs];
    newConfigs[index] = { ...newConfigs[index], ...updates };
    onChange(newConfigs);
  };

  const toggleEnabled = (index: number) => {
    updateConfig(index, { enabled: !configs[index].enabled });
  };

  const updateCount = (index: number, count: number) => {
    updateConfig(index, { count: Math.max(0, count) });
  };

  const totalQuestions = configs
    .filter(c => c.enabled)
    .reduce((sum, c) => sum + c.count, 0);

  return (
    <Card className="p-5 space-y-4 overflow-hidden">
      <div className="flex items-center justify-between gap-3 shrink-0">
        <h3 className="font-semibold text-sm whitespace-nowrap">Question Configuration</h3>
        <span className="text-xs text-muted-foreground whitespace-nowrap shrink-0">
          Total: <strong>{totalQuestions}</strong> questions
        </span>
      </div>

      <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2">
        {configs.map((config, index) => (
          <div key={config.type} className="space-y-3 p-4 border rounded-lg bg-background overflow-hidden">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                <Checkbox
                  checked={config.enabled}
                  onCheckedChange={() => toggleEnabled(index)}
                  className="shrink-0"
                />
                <Label className="font-medium capitalize text-sm whitespace-nowrap">
                  {config.type.replace('-', ' ')}
                </Label>
              </div>
              {config.enabled && (
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8 shrink-0"
                    onClick={() => updateCount(index, config.count - 1)}
                    disabled={config.count <= 0}
                  >
                    <Minus className="h-3.5 w-3.5" />
                  </Button>
                  <Input
                    type="number"
                    value={config.count}
                    onChange={(e) => updateCount(index, parseInt(e.target.value) || 0)}
                    className="w-16 h-8 text-center text-sm"
                    min="0"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8 shrink-0"
                    onClick={() => updateCount(index, config.count + 1)}
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>

            {config.enabled && (
              <div className="pl-7 space-y-3 text-xs">
                {config.type === 'multiple-choice' && (
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs mb-2 block font-medium">Number of options</Label>
                      <Select
                        value={String(config.options?.numOptions || 4)}
                        onValueChange={(v) =>
                          updateConfig(index, {
                            options: { ...config.options, numOptions: parseInt(v) }
                          })
                        }
                      >
                        <SelectTrigger className="h-9 text-xs w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="3">3 options</SelectItem>
                          <SelectItem value="4">4 options</SelectItem>
                          <SelectItem value="5">5 options</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-start gap-2.5">
                      <Checkbox
                        checked={config.options?.includeAllOfAbove || false}
                        onCheckedChange={(checked) =>
                          updateConfig(index, {
                            options: {
                              ...config.options,
                              includeAllOfAbove: checked as boolean
                            }
                          })
                        }
                        className="mt-0.5 shrink-0"
                      />
                      <Label className="text-xs leading-relaxed cursor-pointer break-words flex-1">Include "All of the above" option</Label>
                    </div>
                    <div className="flex items-start gap-2.5">
                      <Checkbox
                        checked={config.options?.includeNoneOfAbove || false}
                        onCheckedChange={(checked) =>
                          updateConfig(index, {
                            options: {
                              ...config.options,
                              includeNoneOfAbove: checked as boolean
                            }
                          })
                        }
                        className="mt-0.5 shrink-0"
                      />
                      <Label className="text-xs leading-relaxed cursor-pointer break-words flex-1">Include "None of the above" option</Label>
                    </div>
                  </div>
                )}

                {config.type === 'true-false' && (
                  <div className="flex items-start gap-2.5">
                    <Checkbox
                      checked={config.options?.includeExplanation || false}
                      onCheckedChange={(checked) =>
                        updateConfig(index, {
                          options: {
                            ...config.options,
                            includeExplanation: checked as boolean
                          }
                        })
                      }
                      className="mt-0.5 shrink-0"
                    />
                    <Label className="text-xs leading-relaxed cursor-pointer break-words flex-1">Include explanation for each question</Label>
                  </div>
                )}

                {config.type === 'short-answer' && (
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs mb-1.5 block">Expected answer length</Label>
                      <Select
                        value={config.options?.expectedLength || 'sentence'}
                        onValueChange={(v) =>
                          updateConfig(index, {
                            options: { ...config.options, expectedLength: v }
                          })
                        }
                      >
                        <SelectTrigger className="h-8 text-xs w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="sentence">1 sentence</SelectItem>
                          <SelectItem value="paragraph">1 paragraph</SelectItem>
                          <SelectItem value="brief">Brief (2-3 sentences)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-start gap-2.5">
                      <Checkbox
                        checked={config.options?.includeSampleAnswer || false}
                        onCheckedChange={(checked) =>
                          updateConfig(index, {
                            options: {
                              ...config.options,
                              includeSampleAnswer: checked as boolean
                            }
                          })
                        }
                        className="mt-0.5 shrink-0"
                      />
                      <Label className="text-xs leading-relaxed cursor-pointer break-words flex-1">Include sample answer</Label>
                    </div>
                  </div>
                )}

                {config.type === 'essay' && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-xs mb-1.5 block">Min words</Label>
                        <Input
                          type="number"
                          value={config.options?.wordCountRange?.min || 200}
                          onChange={(e) =>
                            updateConfig(index, {
                              options: {
                                ...config.options,
                                wordCountRange: {
                                  min: parseInt(e.target.value) || 200,
                                  max: config.options?.wordCountRange?.max || 500
                                }
                              }
                            })
                          }
                          className="h-8 text-xs w-full"
                        />
                      </div>
                      <div>
                        <Label className="text-xs mb-1.5 block">Max words</Label>
                        <Input
                          type="number"
                          value={config.options?.wordCountRange?.max || 500}
                          onChange={(e) =>
                            updateConfig(index, {
                              options: {
                                ...config.options,
                                wordCountRange: {
                                  min: config.options?.wordCountRange?.min || 200,
                                  max: parseInt(e.target.value) || 500
                                }
                              }
                            })
                          }
                          className="h-8 text-xs w-full"
                        />
                      </div>
                    </div>
                    <div className="flex items-start gap-2.5">
                      <Checkbox
                        checked={config.options?.includeRubric || false}
                        onCheckedChange={(checked) =>
                          updateConfig(index, {
                            options: {
                              ...config.options,
                              includeRubric: checked as boolean
                            }
                          })
                        }
                        className="mt-0.5 shrink-0"
                      />
                      <Label className="text-xs leading-relaxed cursor-pointer break-words flex-1">Generate rubric</Label>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

