import React, { useState } from 'react';
import { Question } from '@/shared/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { GripVertical, Trash2, Edit, Plus, ArrowUp, ArrowDown, CheckCircle2 } from 'lucide-react';

interface QuestionEditorProps {
  questions: Question[];
  onUpdate: (questions: Question[]) => void;
}

export function QuestionEditor({ questions, onUpdate }: QuestionEditorProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);

  const handleEdit = (question: Question) => {
    setEditingQuestion({ ...question });
    setEditingId(question.id);
  };

  const handleSaveEdit = () => {
    if (!editingQuestion || !editingId) return;
    
    const updated = questions.map(q => 
      q.id === editingId ? editingQuestion : q
    );
    onUpdate(updated);
    setEditingId(null);
    setEditingQuestion(null);
  };

  const handleDelete = (id: string) => {
    onUpdate(questions.filter(q => q.id !== id));
  };

  const handleMove = (id: string, direction: 'up' | 'down') => {
    const index = questions.findIndex(q => q.id === id);
    if (index === -1) return;
    
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= questions.length) return;
    
    const newQuestions = [...questions];
    [newQuestions[index], newQuestions[newIndex]] = [newQuestions[newIndex], newQuestions[index]];
    onUpdate(newQuestions);
  };

  const handleAddQuestion = (question: Question) => {
    onUpdate([...questions, question]);
    setShowAddDialog(false);
  };

  const getTypeBadgeColor = (type: string) => {
    switch (type) {
      case 'multiple-choice': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'true-false': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'short-answer': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'essay': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <div className="space-y-3 sm:space-y-4 p-2 sm:p-0">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0">
        <h3 className="font-semibold text-sm">Questions ({questions.length})</h3>
        <Button size="sm" onClick={() => setShowAddDialog(true)} className="w-full sm:w-auto">
          <Plus className="h-4 w-4 mr-2" />
          Add Question
        </Button>
      </div>

      <div className="space-y-3">
        {questions.map((question, index) => (
          <Card key={question.id} className="p-3 sm:p-4">
            <div className="flex items-start gap-2 sm:gap-3">
              <div className="flex flex-col items-center gap-1 pt-1 shrink-0">
                <GripVertical className="h-4 w-4 text-muted-foreground cursor-move" />
                <span className="text-xs font-medium text-muted-foreground">
                  {index + 1}
                </span>
              </div>

              <div className="flex-1 space-y-3">
                {editingId === question.id && editingQuestion ? (
                  <EditQuestionForm
                    question={editingQuestion}
                    onChange={setEditingQuestion}
                    onSave={handleSaveEdit}
                    onCancel={() => {
                      setEditingId(null);
                      setEditingQuestion(null);
                    }}
                  />
                ) : (
                  <>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge className={getTypeBadgeColor(question.type)}>
                            {question.type.replace('-', ' ')}
                          </Badge>
                          {question.difficulty && (
                            <Badge variant="outline" className="text-xs">
                              {question.difficulty}
                            </Badge>
                          )}
                        </div>
                        <p className="font-medium mb-2">{question.question}</p>
                        
                        {question.type === 'multiple-choice' && question.options && (
                          <div className="space-y-1 ml-4">
                            {question.options.map((opt, optIdx) => (
                              <div
                                key={optIdx}
                                className={`text-sm ${
                                  optIdx === question.correctAnswer
                                    ? 'text-green-600 dark:text-green-400 font-medium'
                                    : ''
                                }`}
                              >
                                {String.fromCharCode(65 + optIdx)}) {opt}
                                {optIdx === question.correctAnswer && (
                                  <CheckCircle2 className="h-3 w-3 inline ml-1" />
                                )}
                              </div>
                            ))}
                          </div>
                        )}

                        {(question.type === 'true-false' || question.type === 'short-answer' || question.type === 'essay') && (
                          <div className="ml-4 text-sm text-muted-foreground">
                            <strong>Answer:</strong> {question.correctAnswer}
                          </div>
                        )}

                        {question.explanation && (
                          <div className="mt-2 p-2 bg-muted/50 rounded text-xs">
                            <strong>Explanation:</strong> {question.explanation}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-1 sm:gap-2 pt-2 border-t">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMove(question.id, 'up')}
                        disabled={index === 0}
                        className="h-7 text-xs flex-1 sm:flex-initial"
                      >
                        <ArrowUp className="h-3 w-3 sm:mr-1" />
                        <span className="hidden sm:inline">Up</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMove(question.id, 'down')}
                        disabled={index === questions.length - 1}
                        className="h-7 text-xs flex-1 sm:flex-initial"
                      >
                        <ArrowDown className="h-3 w-3 sm:mr-1" />
                        <span className="hidden sm:inline">Down</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(question)}
                        className="h-7 text-xs flex-1 sm:flex-initial"
                      >
                        <Edit className="h-3 w-3 sm:mr-1" />
                        <span className="hidden sm:inline">Edit</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(question.id)}
                        className="h-7 text-xs text-destructive hover:text-destructive flex-1 sm:flex-initial"
                      >
                        <Trash2 className="h-3 w-3 sm:mr-1" />
                        <span className="hidden sm:inline">Delete</span>
                      </Button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {questions.length === 0 && (
        <div className="text-center py-8 text-muted-foreground text-sm">
          No questions yet. Click "Add Question" to create one.
        </div>
      )}

      <AddQuestionDialog
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        onAdd={handleAddQuestion}
      />
    </div>
  );
}

function EditQuestionForm({
  question,
  onChange,
  onSave,
  onCancel
}: {
  question: Question;
  onChange: (q: Question) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs font-medium mb-1 block">Question</label>
        <Textarea
          value={question.question}
          onChange={(e) => onChange({ ...question, question: e.target.value })}
          className="min-h-[80px]"
        />
      </div>

      {question.type === 'multiple-choice' && (
        <div className="space-y-2">
          <label className="text-xs font-medium">Options</label>
          {question.options?.map((opt, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <span className="text-xs w-6">{String.fromCharCode(65 + idx)})</span>
              <Input
                value={opt}
                onChange={(e) => {
                  const newOptions = [...(question.options || [])];
                  newOptions[idx] = e.target.value;
                  onChange({ ...question, options: newOptions });
                }}
                className="flex-1"
              />
              <input
                type="radio"
                checked={question.correctAnswer === idx}
                onChange={() => onChange({ ...question, correctAnswer: idx })}
              />
            </div>
          ))}
        </div>
      )}

      {(question.type === 'true-false' || question.type === 'short-answer' || question.type === 'essay') && (
        <div>
          <label className="text-xs font-medium mb-1 block">Correct Answer</label>
          <Textarea
            value={String(question.correctAnswer)}
            onChange={(e) => onChange({ ...question, correctAnswer: e.target.value })}
            className="min-h-[60px]"
          />
        </div>
      )}

      <div>
        <label className="text-xs font-medium mb-1 block">Explanation (optional)</label>
        <Textarea
          value={question.explanation || ''}
          onChange={(e) => onChange({ ...question, explanation: e.target.value })}
          className="min-h-[60px]"
          placeholder="Explanation for the answer..."
        />
      </div>

      <div>
        <label className="text-xs font-medium mb-1 block">Difficulty</label>
        <Select
          value={question.difficulty || 'medium'}
          onValueChange={(v) => onChange({ ...question, difficulty: v as any })}
        >
          <SelectTrigger className="h-8">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="easy">Easy</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="hard">Hard</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex gap-2 pt-2">
        <Button size="sm" onClick={onSave} className="flex-1">
          Save
        </Button>
        <Button size="sm" variant="outline" onClick={onCancel} className="flex-1">
          Cancel
        </Button>
      </div>
    </div>
  );
}

function AddQuestionDialog({
  open,
  onOpenChange,
  onAdd
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (q: Question) => void;
}) {
  const [type, setType] = useState<Question['type']>('multiple-choice');
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState<string[]>(['', '', '', '']);
  const [correctAnswer, setCorrectAnswer] = useState<string | number>('');
  const [explanation, setExplanation] = useState('');
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium');

  const handleAdd = () => {
    const newQuestion: Question = {
      id: Math.random().toString(),
      type,
      question,
      correctAnswer: type === 'multiple-choice' ? parseInt(String(correctAnswer)) : correctAnswer,
      options: type === 'multiple-choice' ? options.filter(o => o.trim()) : undefined,
      explanation: explanation || undefined,
      difficulty
    };
    onAdd(newQuestion);
    // Reset form
    setQuestion('');
    setOptions(['', '', '', '']);
    setCorrectAnswer('');
    setExplanation('');
    setDifficulty('medium');
    setType('multiple-choice');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Add Custom Question</DialogTitle>
          <DialogDescription>
            Create a custom question to add to your question set
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Question Type</label>
            <Select value={type} onValueChange={(v) => setType(v as any)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="multiple-choice">Multiple Choice</SelectItem>
                <SelectItem value="true-false">True/False</SelectItem>
                <SelectItem value="short-answer">Short Answer</SelectItem>
                <SelectItem value="essay">Essay</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">Question</label>
            <Textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="min-h-[100px]"
              placeholder="Enter your question..."
            />
          </div>

          {type === 'multiple-choice' && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Options</label>
              {options.map((opt, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className="text-xs w-6">{String.fromCharCode(65 + idx)})</span>
                  <Input
                    value={opt}
                    onChange={(e) => {
                      const newOptions = [...options];
                      newOptions[idx] = e.target.value;
                      setOptions(newOptions);
                    }}
                    placeholder={`Option ${idx + 1}`}
                  />
                  <input
                    type="radio"
                    checked={correctAnswer === idx}
                    onChange={() => setCorrectAnswer(idx)}
                  />
                </div>
              ))}
            </div>
          )}

          {(type === 'true-false' || type === 'short-answer' || type === 'essay') && (
            <div>
              <label className="text-sm font-medium mb-2 block">Correct Answer</label>
              <Textarea
                value={String(correctAnswer)}
                onChange={(e) => setCorrectAnswer(e.target.value)}
                className="min-h-[80px]"
                placeholder="Enter the correct answer..."
              />
            </div>
          )}

          <div>
            <label className="text-sm font-medium mb-2 block">Explanation (optional)</label>
            <Textarea
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              className="min-h-[60px]"
              placeholder="Explanation for the answer..."
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">Difficulty</label>
            <Select value={difficulty} onValueChange={(v) => setDifficulty(v as any)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="easy">Easy</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="hard">Hard</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleAdd} disabled={!question || (type === 'multiple-choice' && !options.some(o => o.trim()))}>
            Add Question
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

