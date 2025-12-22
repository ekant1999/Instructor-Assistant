# Instructor Assistant

A comprehensive web application designed to help instructors manage research papers, generate summaries, create question sets, and interact with documents using RAG (Retrieval-Augmented Generation) technology.

## 🎯 Features

### 📚 Research Library
<img width="600" height="600" alt="image" src="https://github.com/user-attachments/assets/42174f6e-ee1a-464e-b289-8d25edf2f275" />

- **Search & Filter**: Search papers by title, author, keywords with real-time filtering
- **Multi-Paper Operations**: Select multiple papers with checkboxes for batch operations
- **Batch Summarization**: Generate summaries for multiple papers simultaneously with progress tracking
- **Multiple Summaries**: Create and manage multiple summaries per paper with full history
- **Advanced Editor**: Markdown editor with Edit/Preview/Split modes and auto-save
- **Export Options**: Export summaries in PDF, TXT, LaTeX, Markdown, and DOCX formats
- **Save to Notes**: Seamlessly save summaries to your notes library

### 📝 Notes Section
<img width="600" height="600" alt="image" src="https://github.com/user-attachments/assets/a6af7e3f-affd-4c89-ba74-0acf01d92b9b" />

- **Unified Library**: Centralized document management for all content types (Summaries, Q&A, RAG responses, Manual notes)
- **Smart Filtering**: Filter by document type, tags, and search across all documents
- **Hierarchical Organization**: Organize documents by type with clear visual hierarchy
- **Source Tracking**: Navigate back to source papers and linked documents
- **Metadata Display**: View word counts, creation dates, and generation agents

### ❓ Question Set Generation
<img width="600" height="600" alt="image" src="https://github.com/user-attachments/assets/4f2f8e16-2cd7-45ef-8686-7fe28afe59d3" />

- **Custom Configuration**: Configure question types individually (Multiple Choice, True/False, Short Answer, Essay)
- **Advanced Options**: Set number of options, include explanations, word count ranges, and rubrics
- **Incremental Generation**: Add more questions to existing sets without regenerating
- **Question Editor**: Edit, reorder, and delete individual questions with a user-friendly interface
- **Document Selection**: Select source documents from your Notes library
- **Multiple Export Formats**: Export in Canvas, Moodle, JSON, PDF, TXT, and Markdown formats
- **Export Options**: Include/exclude answers, explanations, and generate separate answer keys

### 🔍 RAG (Retrieval-Augmented Generation)
<img width="600" height="600" alt="image" src="https://github.com/user-attachments/assets/365b8a15-0812-412c-b545-8ef382d3322c" />

- **Multiple Agents**: Support for GPT Web, Gemini Web, and Qwen Local agents
- **Selective Ingestion**: Choose specific documents to include in RAG queries
- **Context Templates**: Save and load document selection templates for repeated use
- **Query History**: View past queries with favorites and search functionality
- **Enhanced Responses**: Display responses with citations and source tracking
- **Advanced Options**: Configure max chunks, temperature, verbose mode, and citation preferences
- **Integration**: Save responses to Notes or send directly to Chat

### 💬 Chat Interface
- **AI-Powered Conversations**: Interactive chat interface for general assistance
- **Context-Aware**: Integrates with your documents and research library

## 🛠️ Tech Stack

### Frontend
- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Wouter** - Lightweight routing
- **TanStack Query** - Data fetching and caching
- **Zustand** - State management
- **Radix UI** - Accessible component primitives
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **React Markdown** - Markdown rendering

### Backend
- **Express** - Web server
- **PostgreSQL** - Database
- **Drizzle ORM** - Database toolkit
- **WebSocket (ws)** - Real-time communication
- **Passport** - Authentication

### Development Tools
- **TypeScript** - Type checking
- **ESBuild** - Fast bundling
- **Drizzle Kit** - Database migrations

## 📦 Installation

### Prerequisites
- Node.js 18+ and npm
- PostgreSQL database
- Environment variables configured

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Instructor-Assistant
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/instructor_assistant
   PORT=5000
   NODE_ENV=development
   ```

4. **Set up the database**
   ```bash
   npm run db:push
   ```

5. **Start the development server**
   ```bash
   npm run dev
   ```

The application will be available at:
- **Main Application**: http://localhost:5000
- **Client Dev Server** (if running separately): http://localhost:5173

## 🚀 Usage

### Accessing Features

- **Chat**: Navigate to `/` for the main chat interface
- **Research Library**: Navigate to `/library` to manage papers and generate summaries
- **Notes**: Navigate to `/notes` to view and manage all your documents
- **Question Sets**: Navigate to `/questions` to generate and edit question sets
- **RAG**: Navigate to `/rag` to query your documents with AI assistance

### Quick Start Workflow

1. **Upload Papers**: Go to Library page and upload PDF papers
2. **Generate Summaries**: Select papers and generate summaries with your preferred agent
3. **Save to Notes**: Save summaries to your Notes library for easy access
4. **Create Questions**: Use saved documents in Notes to generate question sets
5. **Query with RAG**: Select documents and ask questions using the RAG interface
6. **Export**: Export any content in your preferred format

## 📁 Project Structure

```
Instructor-Assistant/
├── client/                 # Frontend React application
│   ├── src/
│   │   ├── agent/         # AI agent implementations
│   │   ├── app/           # App shell and routing
│   │   ├── chat/          # Chat interface components
│   │   ├── components/    # Reusable UI components
│   │   ├── library/       # Research library features
│   │   ├── notes/         # Notes management
│   │   ├── questions/     # Question set generation
│   │   ├── rag/           # RAG functionality
│   │   └── shared/        # Shared types and utilities
│   └── public/            # Static assets
├── server/                 # Backend Express server
│   ├── index.ts           # Server entry point
│   ├── routes.ts          # API routes
│   └── storage.ts         # File storage utilities
├── shared/                 # Shared code between client and server
│   └── schema.ts          # Database schema definitions
└── script/                 # Build and utility scripts
```

## 🗄️ Database Schema

The application uses PostgreSQL with the following main tables:

- **users** - User accounts and authentication
- **papers** - Research papers with metadata
- **summaries** - Multiple summaries per paper
- **documents** - Unified document library (Notes)
- **questionSets** - Generated question sets
- **ragQueries** - RAG query history
- **contextTemplates** - Saved RAG context templates
- **exports** - Export history

See `shared/schema.ts` for complete schema definitions.

## 🧪 Development

### Available Scripts

- `npm run dev` - Start development server (runs both client and server)
- `npm run dev:client` - Start only the client dev server (port 5173)
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run check` - Type check with TypeScript
- `npm run db:push` - Push database schema changes

### Development Workflow

1. Make changes to the codebase
2. The dev server will automatically reload
3. Check the browser console for any errors
4. Use `npm run check` to verify TypeScript types

## 🔧 Configuration

### Port Configuration
The application runs on port 5000 by default. You can change this by setting the `PORT` environment variable.

### Database Configuration
Ensure your `DATABASE_URL` environment variable is correctly set to your PostgreSQL connection string.

## 📝 API Documentation

The application uses RESTful API endpoints. Main endpoints include:

- `/api/papers` - Paper CRUD operations
- `/api/summaries` - Summary management
- `/api/documents` - Document library operations
- `/api/questions` - Question set generation
- `/api/rag` - RAG query processing
- `/api/export` - Export generation

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -ti:5000
   # Kill the process if needed
   kill -9 <PID>
   ```

2. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check `DATABASE_URL` environment variable
   - Ensure database exists and user has proper permissions

3. **Component Import Errors**
   - Run `npm install` to ensure all dependencies are installed
   - Check that all UI components exist in `client/src/components/ui/`
   - Verify TypeScript compilation: `npm run check`

4. **Build Errors**
   - Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
   - Check for TypeScript errors: `npm run check`

## 🚧 Roadmap

- [ ] Server-side API implementation for all features
- [ ] Selenium integration for GPT/Gemini web agents
- [ ] Server-side export generation (PDF, LaTeX, DOCX)
- [ ] Enhanced document lineage tracking
- [ ] Smart contextual suggestions
- [ ] User authentication and multi-user support
- [ ] Advanced search and filtering
- [ ] Collaborative features

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues, questions, or contributions, please open an issue on the repository.

---

**Built with ❤️ for instructors and researchers**

