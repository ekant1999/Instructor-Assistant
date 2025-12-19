import React from 'react';
import { Switch, Route } from 'wouter';
import ChatPage from '@/chat/ChatPage';
import LibraryPage from '@/library/LibraryPage';
import NotesPage from '@/notes/NotesPage';
import QuestionSetsPage from '@/questions/QuestionSetsPage';
import RagPage from '@/rag/RagPage';

export default function AppRoutes() {
  return (
    <Switch>
      <Route path="/" component={ChatPage} />
      <Route path="/library" component={LibraryPage} />
      <Route path="/notes" component={NotesPage} />
      <Route path="/questions" component={QuestionSetsPage} />
      <Route path="/rag" component={RagPage} />
      <Route>404 - Not Found</Route>
    </Switch>
  );
}
