# Personal Knowledge Agent - Frontend

Next.js 14+ frontend application for the Personal Knowledge Agent system.

## Features

- **Ask Questions**: Query your knowledge base with natural language
- **Upload Knowledge**: Add new information to your database
- **View Sources**: Browse and manage stored knowledge chunks
- **Memory Timeline**: Track system activity and learning over time

## Tech Stack

- Next.js 14+ (App Router)
- React 18+
- TypeScript (strict mode)
- API Client for backend communication

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

### Build for Production

```bash
# Create production build
npm run build

# Start production server
npm start
```

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout with navigation
│   ├── page.tsx           # Home page
│   ├── query/             # Ask questions page
│   ├── upload/            # Upload knowledge page
│   ├── sources/           # View sources page
│   └── timeline/          # Memory timeline page
├── lib/                   # Shared utilities
│   ├── api-client.ts     # Backend API client
│   └── types.ts          # TypeScript type definitions
├── package.json
├── tsconfig.json
└── next.config.js
```

## API Configuration

The API base URL can be configured via environment variable:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Default: `http://localhost:8000/api/v1`

## Pages

### Ask Questions (`/query`)

- Submit natural language queries
- Select reasoning mode (ELI5, Exam, Research, Comparison)
- View answers with sources and confidence scores
- See reasoning steps and citations

### Upload Knowledge (`/upload`)

- Add new content to knowledge base
- Provide metadata (title, source, topic, tags)
- Get quality assessment feedback

### View Sources (`/sources`)

- Browse all stored knowledge chunks
- View chunk details and metadata
- Delete unwanted chunks
- Pagination support

### Memory Timeline (`/timeline`)

- View system activity history
- Filter by time range
- See queries, uploads, and system events
- View system statistics

## Development

### Type Safety

The project uses strict TypeScript. All API types are defined in `lib/types.ts`.

### API Client

The API client (`lib/api-client.ts`) provides:

- Type-safe API calls
- Error handling
- Streaming support (SSE)
- Automatic JSON parsing

### No Styling Yet

This initial version focuses on functionality. Styling will be added in a future iteration.

## License

MIT
