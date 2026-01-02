# Mevzuat.info Frontend Component

This component is the complete frontend application for the Mevzuat.info legislation search service.

## Features

- **Home Page**: Overview of the platform with statistics and recent documents.
- **Search & Discovery**: Advanced filtering by document type and date range.
- **Document Detail**: Clean, readable markdown view of legislation with metadata sidebars.
- **Responsive Design**: Optimized for mobile and desktop.
- **Theme**: Professional "Official" aesthetic using Tailwind CSS.

## Key Components

- `Navbar`: Main navigation.
- `StatsChart`: Visual distribution of document types using Recharts.
- `DocumentCard`: Summary view for lists.

## Usage

This is a full-page application component. Import and render it to display the entire app structure.

```tsx
import { App } from '@/sd-components/e1c5b5c2-5fb0-4142-92e8-af6e89304078';

function Main() {
  return <App />;
}
```

## Dependencies

- react-router-dom
- recharts
- react-markdown
- lucide-react
- framer-motion