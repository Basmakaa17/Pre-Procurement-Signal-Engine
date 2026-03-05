# Supabase MCP Setup

This guide explains how to add the Supabase MCP (Model Context Protocol) server to Cursor IDE.

## Prerequisites

- Node.js installed (for running the MCP server)
- Supabase project URL and service key from your `.env` file

## Setup Steps

### Option 1: Through Cursor Settings UI

1. Open Cursor Settings (Cmd/Ctrl + ,)
2. Navigate to **Features** > **Model Context Protocol**
3. Click **Add Server** or **Edit Configuration**
4. Add the following configuration:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-supabase"
      ],
      "env": {
        "SUPABASE_URL": "YOUR_SUPABASE_URL_HERE",
        "SUPABASE_SERVICE_KEY": "YOUR_SUPABASE_SERVICE_KEY_HERE"
      }
    }
  }
}
```

5. Replace `YOUR_SUPABASE_URL_HERE` and `YOUR_SUPABASE_SERVICE_KEY_HERE` with values from your `backend/.env` file:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_SERVICE_KEY`: Your Supabase service role key

### Option 2: Manual Configuration File

If Cursor supports a configuration file, create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-supabase"
      ],
      "env": {
        "SUPABASE_URL": "YOUR_SUPABASE_URL_HERE",
        "SUPABASE_SERVICE_KEY": "YOUR_SUPABASE_SERVICE_KEY_HERE"
      }
    }
  }
}
```

## Getting Your Supabase Credentials

Your Supabase credentials are stored in `backend/.env`:

- `SUPABASE_URL`: Found in your Supabase project settings
- `SUPABASE_SERVICE_KEY`: Found in your Supabase project settings (Service Role key, not the anon key)

## Verification

After setup, you should be able to:
- Query your Supabase database directly from Cursor
- Access tables, run queries, and view data through MCP tools
- Use natural language to interact with your database

## Troubleshooting

1. **MCP server not starting**: Ensure Node.js is installed and `npx` is available
2. **Connection errors**: Verify your Supabase URL and service key are correct
3. **Permission errors**: Ensure you're using the service role key, not the anon key

## Available MCP Tools

Once configured, the Supabase MCP server provides tools for:
- Querying tables
- Inserting/updating/deleting records
- Running SQL queries
- Managing database schema
- And more...
