import React from 'react';
import { Switch, Route } from 'wouter';
import ChatPage from '@/chat/ChatPage';
import EnhancedLibraryPage from '@/library/EnhancedLibraryPage';
import EnhancedNotesPage from '@/notes/EnhancedNotesPage';
import EnhancedQuestionSetsPage from '@/questions/EnhancedQuestionSetsPage';
import EnhancedRagPage from '@/rag/EnhancedRagPage';

// Keep original pages available as fallback if needed
import LibraryPage from '@/library/LibraryPage';
import NotesPage from '@/notes/NotesPage';
import QuestionSetsPage from '@/questions/QuestionSetsPage';
import RagPage from '@/rag/RagPage';

export default function AppRoutes() {
  return (
    <Switch>
      <Route path="/" component={ChatPage} />
      {/* Enhanced pages with all new features */}
      <Route path="/library" component={EnhancedLibraryPage} />
      <Route path="/notes" component={EnhancedNotesPage} />
      <Route path="/questions" component={EnhancedQuestionSetsPage} />
      <Route path="/rag" component={EnhancedRagPage} />
      {/* Fallback to original pages if needed */}
      <Route path="/library/original" component={LibraryPage} />
      <Route path="/notes/original" component={NotesPage} />
      <Route path="/questions/original" component={QuestionSetsPage} />
      <Route path="/rag/original" component={RagPage} />
      <Route>404 - Not Found</Route>
    </Switch>
  );
}
