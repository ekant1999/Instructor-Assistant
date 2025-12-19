import React from 'react';
import { Link, useLocation } from 'wouter';
import { cn } from '@/lib/utils';
import { MessageSquare, Library, NotebookPen, FileQuestion, Network, Settings, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ChatInput } from '@/chat/ChatInput';
import QwenAgent from '@/agent/QwenAgent';

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const [location] = useLocation();

  const navItems = [
    { label: 'Chat', icon: MessageSquare, path: '/' },
    { label: 'Library', icon: Library, path: '/library' },
    { label: 'Notes', icon: NotebookPen, path: '/notes' },
    { label: 'Q-Sets', icon: FileQuestion, path: '/questions' },
    { label: 'RAG', icon: Network, path: '/rag' },
  ];

  const isChatPage = location === '/';

  return (
    <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">
      {/* Top Bar */}
      <header className="h-14 border-b border-border flex items-center justify-between px-4 bg-background/80 backdrop-blur-sm z-50 sticky top-0">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="md:hidden">
            <Menu className="h-5 w-5" />
          </Button>
          <div className="font-bold text-lg tracking-tight flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-foreground">
              IA
            </div>
            <span className="hidden md:inline">Instructor Assistant</span>
          </div>
        </div>

        <nav className="flex items-center gap-1 bg-secondary/30 p-1 rounded-lg">
          {navItems.map((item) => {
            const isActive = location === item.path;
            const Icon = item.icon;
            return (
              <Link key={item.path} href={item.path}>
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "h-8 px-3 rounded-md transition-all text-sm font-medium",
                    isActive 
                      ? "bg-background shadow-sm text-foreground" 
                      : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                  )}
                >
                  <Icon className="h-4 w-4 mr-2" />
                  {item.label}
                </Button>
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
           <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500" />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 relative overflow-hidden flex flex-col">
        {children}
        
        {/* Persistent Chat Input Layer - always sits above content at bottom */}
        {/* On Chat Page, it's integrated into the scroll flow usually, but we can make it fixed overlay for all pages if we wanted.
            However, for this design, if we are NOT on chat page, maybe we show a minimized version or hide it?
            The Prompt says: "Floating Chat Input (ChatGPT-style)" in App Layout.
            Standard ChatGPT: Input is on the chat page.
            Let's keep it simply in the Chat Page for now to avoid layout conflicts with other complex pages (like Editor).
            Wait, if I put it here, it overlays everything.
            Let's put it here ONLY if we are on ChatPage, or maybe a "Global Command" bar?
            Actually, let's keep it in ChatPage for strictly replicating the "Chat Experience" there, 
            and maybe other pages have their own context. 
            BUT, the prompt says "App Layout ... Floating Chat Input". 
            I'll implement it as: If we are on ChatPage, we render the Input fixed at bottom. 
            If we are on other pages, maybe we rely on the Floating Agent.
        */}
        {isChatPage && (
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-background via-background to-transparent z-40">
             <ChatInput />
          </div>
        )}
      </main>

      {/* Global Floating Agent */}
      <QwenAgent />
    </div>
  );
}
