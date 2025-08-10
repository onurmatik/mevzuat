# mevzuat.info

mevzuat.info is a service for tracking and querying Turkish legislation. The project fetches official legal texts, stores them for reference, and exposes tools to search and stay up to date with changes in Turkish laws and regulations.

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

The repository includes a simple [Model Context Protocol](https://github.com/modelcontextprotocol/standard) server that exposes stored Mevzuat documents to MCP-compliant agents. After installing backend dependencies and setting up the database, run:

```bash
python scripts/mevzuat_mcp_server.py
```

The server lists each document as a resource and returns the markdown content when available, falling back to JSON metadata otherwise.

## Contributing

Contributions are welcome. Please ensure code changes are checked with `python -m py_compile` before submitting.

