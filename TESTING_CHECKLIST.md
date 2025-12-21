# Component Testing Checklist

## ✅ Server Status
- [x] Development server started
- [x] Port 5000 accessible
- [x] Sonner toaster added to App.tsx
- [x] Routes updated to use enhanced pages

## 🧪 Components to Test

### 1. Research Library (`/library`)
- [ ] Search bar filters papers correctly
- [ ] Year filter dropdown works
- [ ] Author filter dropdown works
- [ ] Sort options (Recent, Title A-Z, Most Cited) work
- [ ] Multi-paper selection with checkboxes
- [ ] Select All / Clear Selection buttons
- [ ] Batch summarization panel appears when papers selected
- [ ] Batch summarization generates summaries
- [ ] Summary history displays multiple summaries
- [ ] Summary editor opens with Edit/Preview/Split modes
- [ ] Markdown toolbar functions work
- [ ] Auto-save indicator shows
- [ ] Save to Notes modal opens
- [ ] Export dialog opens and formats correctly

### 2. Notes Section (`/notes`)
- [ ] Document list displays all types
- [ ] Type filter works (Summary/Q&A/RAG/Manual)
- [ ] Tag filter works
- [ ] Search across documents works
- [ ] Document type badges display correctly
- [ ] Source links navigate correctly
- [ ] Document editing works
- [ ] Tags can be edited
- [ ] Metadata displays correctly

### 3. Q-Set Generation (`/questions`)
- [ ] Document selector shows papers and notes
- [ ] Paper/Note selection works
- [ ] Question configuration panel displays
- [ ] Question type counts can be adjusted
- [ ] Question type options (MC options, difficulty) work
- [ ] Generate Questions button works
- [ ] Questions appear in preview
- [ ] "Add More Questions" button works
- [ ] Question editor displays questions
- [ ] Edit question works
- [ ] Move up/down buttons work
- [ ] Delete question works
- [ ] Add custom question dialog works
- [ ] Export dialog opens
- [ ] Save to Notes works

### 4. RAG Page (`/rag`)
- [ ] Document ingestion panel displays
- [ ] Paper/Note selection works
- [ ] Context templates can be saved
- [ ] Context templates can be loaded
- [ ] Query history panel displays
- [ ] Agent selection (GPT/Gemini/Qwen) works
- [ ] Query input accepts text
- [ ] Advanced options work (citations, verbose, etc.)
- [ ] Temperature slider works
- [ ] Max chunks input works
- [ ] Query executes and shows response
- [ ] Citations display correctly
- [ ] Save to Notes works
- [ ] Send to Chat works
- [ ] Star/favorite queries works

## 🐛 Common Issues to Check

1. **Import Errors**: Check browser console for missing imports
2. **Type Errors**: Check TypeScript compilation
3. **Toast Notifications**: Verify sonner toasts appear
4. **Routing**: Verify all routes navigate correctly
5. **State Management**: Check if state persists correctly
6. **UI Components**: Verify all shadcn/ui components render

## 📝 Testing Steps

1. Open browser to http://localhost:5000
2. Navigate to each page:
   - `/library`
   - `/notes`
   - `/questions`
   - `/rag`
3. Test each feature systematically
4. Check browser console for errors
5. Verify toast notifications appear
6. Test responsive design (if applicable)

## 🔍 Browser Console Checks

- No import errors
- No undefined component errors
- No missing prop warnings
- Toast notifications work
- No React hydration errors

## ✅ Success Criteria

All components should:
- Render without errors
- Accept user input
- Display data correctly
- Show appropriate feedback (toasts)
- Navigate between states correctly

