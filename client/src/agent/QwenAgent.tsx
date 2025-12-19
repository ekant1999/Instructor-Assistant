import React, { useState } from 'react';
import { Bot, X, ChevronUp, ChevronDown, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useLocation } from 'wouter';

export default function QwenAgent() {
  const [isOpen, setIsOpen] = useState(false);
  const [location] = useLocation();

  const getContextHint = () => {
    if (location === '/') return "Ready to chat";
    if (location === '/library') return "Watching library activity";
    if (location === '/notes') return "Assisting with notes";
    if (location === '/questions') return "Question generation ready";
    return "Agent active";
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {isOpen && (
        <Card className="w-64 p-4 shadow-xl border-primary/20 bg-background/95 backdrop-blur animate-in slide-in-from-bottom-5 fade-in">
          <div className="flex justify-between items-start mb-2">
            <h4 className="font-semibold text-sm flex items-center gap-2">
              <Bot className="h-4 w-4 text-primary" />
              Agent Status
            </h4>
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setIsOpen(false)}>
              <X className="h-3 w-3" />
            </Button>
          </div>
          
          <div className="space-y-3">
             <div className="text-xs text-muted-foreground">
               Current Context: <span className="text-foreground font-medium">{location}</span>
             </div>
             
             <div className="bg-secondary/50 p-2 rounded text-xs space-y-1">
               <div className="flex items-center gap-2">
                 <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                 <span>Monitoring intent...</span>
               </div>
               <div className="text-muted-foreground pl-3.5">
                 {getContextHint()}
               </div>
             </div>

             <div className="grid grid-cols-2 gap-2">
               <Button variant="outline" size="sm" className="h-7 text-xs">Analyze</Button>
               <Button variant="outline" size="sm" className="h-7 text-xs">Summarize</Button>
             </div>
          </div>
        </Card>
      )}

      <Button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "h-12 w-12 rounded-full shadow-lg transition-all duration-300",
          isOpen ? "bg-secondary text-secondary-foreground" : "bg-primary text-primary-foreground hover:scale-105"
        )}
      >
        {isOpen ? <ChevronDown className="h-6 w-6" /> : <Bot className="h-6 w-6" />}
      </Button>
    </div>
  );
}
