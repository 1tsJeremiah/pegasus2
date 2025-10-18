#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import os from 'os';
import { pathToFileURL } from 'url';
import { ListToolsRequestSchema, CallToolRequestSchema } from '@modelcontextprotocol/sdk/types.js';

const repoPath = process.env.GOOGLE_MCP_REPO ?? path.join(os.homedir(), 'mcp-google');
const modulePath = path.join(repoPath, 'build', 'index.js');
if (!fs.existsSync(modulePath)) {
  console.error(`[google-mcp-readonly] Build artifact not found at ${modulePath}. Run 'npm run build' inside the repo.`);
  process.exit(1);
}

const moduleUrl = pathToFileURL(modulePath).href;
const { server, main } = await import(moduleUrl);

const allowedTools = new Set([
  'list-calendars',
  'list-events',
  'search-events',
  'list-colors',
  'get-freebusy',
  'list-contacts',
  'get-contact',
  'list-emails',
  'get-email',
  'list-labels'
]);

const originalSetHandler = server.setRequestHandler.bind(server);
server.setRequestHandler = (schema, handler) => {
  if (schema === ListToolsRequestSchema) {
    return originalSetHandler(schema, async (...args) => {
      const result = await handler(...args);
      if (result?.tools) {
        result.tools = result.tools.filter((tool) => allowedTools.has(tool.name));
      }
      return result;
    });
  }
  if (schema === CallToolRequestSchema) {
    return originalSetHandler(schema, async (request, ...rest) => {
      const name = request?.params?.name;
      if (!allowedTools.has(name)) {
        throw new Error(`Tool '${name}' disabled in read-only mode.`);
      }
      return handler(request, ...rest);
    });
  }
  return originalSetHandler(schema, handler);
};

const profile = process.env.GOOGLE_PROFILE ?? 'primary';
const configDir = process.env.GOOGLE_CONFIG_DIR ?? path.join(os.homedir(), '.config', 'mindstack', 'google', profile);
fs.mkdirSync(configDir, { recursive: true });

if (!process.env.GOOGLE_CALENDAR_MCP_TOKEN_PATH) {
  process.env.GOOGLE_CALENDAR_MCP_TOKEN_PATH = path.join(configDir, 'tokens.json');
}
if (!process.env.GOOGLE_OAUTH_CREDENTIALS) {
  const candidate = path.join(configDir, 'client_secret.json');
  if (fs.existsSync(candidate)) {
    process.env.GOOGLE_OAUTH_CREDENTIALS = candidate;
  }
}

process.env.GOOGLE_MCP_READ_ONLY = '1';

await main();
