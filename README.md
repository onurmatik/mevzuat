# mevzuat.info

mevzuat.info is a service for tracking and querying Turkish legislation. The project fetches official legal texts, stores them for reference, and exposes tools to search and stay up to date with changes in Turkish laws and regulations.

An RSS feed with the most recently added documents is available at `/rss/latest/`.

## Project structure

- `mevzuat/` – Django application providing web interface and APIs.
- `scripts/` – helper scripts used to fetch and process legislative documents.

## Installation

### Backend
pip install -r requirements.txt

### Frontend

npm install react react-dom

npx create-next-app@latest frontend

npm install -D tailwindcss postcss autoprefixer

cd frontend

npx shadcn@latest init

npm install recharts


## MCP server

The repository includes a simple [Model Context Protocol](https://github.com/modelcontextprotocol/standard) server built with the [FastMCP](https://pypi.org/project/fastmcp/) framework. After installing backend dependencies and setting up the database, run:

```bash
python -m mevzuat.mcp_server
```

The server exposes tools for working with the stored legislation, including listing document types, returning document counts, listing documents and performing document searches.

## Contributing

Contributions are welcome. Please ensure code changes are checked with `python -m py_compile` before submitting.

