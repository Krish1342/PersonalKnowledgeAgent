# Frontend Components

Reusable React components for the Personal Knowledge Agent frontend.

## Components

### QueryResult

Displays query results with:

- Answer text
- Confidence score (color-coded)
- Source count
- Validation status
- Processing time
- Expandable citations
- Reasoning steps
- Suggestions and knowledge gaps

**Usage:**

```tsx
import QueryResult from "@/components/QueryResult";

<QueryResult result={queryResponse} />;
```

### ChunkCard

Displays a knowledge chunk/source with:

- Title and metadata badges
- Content preview with expand/collapse
- Quality and confidence scores
- Tags display
- Access statistics
- Delete functionality

**Usage:**

```tsx
import ChunkCard from "@/components/ChunkCard";

<ChunkCard chunk={chunkData} onDelete={(id) => handleDelete(id)} />;
```

### LoadingSpinner

Animated loading indicator.

**Usage:**

```tsx
import LoadingSpinner from "@/components/LoadingSpinner";

<LoadingSpinner message="Loading..." />;
```

### ErrorMessage

Error display with optional retry button.

**Usage:**

```tsx
import ErrorMessage from "@/components/ErrorMessage";

<ErrorMessage error={errorMessage} onRetry={() => retryFunction()} />;
```

## Features

- **Type Safety**: All components are fully typed with TypeScript
- **Reusable**: Can be used across multiple pages
- **Responsive**: Adapts to different screen sizes
- **Accessible**: Semantic HTML with proper ARIA labels
- **Interactive**: Expandable sections, hover effects, and animations
