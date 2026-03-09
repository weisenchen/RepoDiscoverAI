/**
 * RepoDiscoverAI VS Code Extension
 * 
 * Discover awesome GitHub repositories without leaving your IDE.
 */

import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import fetch from 'node-fetch';

// API Configuration
const API_BASE = 'https://api.repodiscover.ai';

/**
 * Repository interface
 */
interface Repository {
  id: number;
  full_name: string;
  description: string;
  html_url: string;
  stargazers_count: number;
  forks_count: number;
  language: string;
  topics: string[];
  clone_url: string;
}

/**
 * Search result interface
 */
interface SearchResult {
  repos: Repository[];
  total: number;
  page: number;
  per_page: number;
}

/**
 * Webview Panel Manager
 */
class RepoWebviewPanel {
  public static currentPanel: RepoWebviewPanel | undefined;
  public static readonly viewType = 'repodiscoverai';

  private readonly _panel: vscode.WebviewPanel;
  private readonly _extensionPath: string;
  private _disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionPath: string) {
    const column = vscode.window.activeTextEditor
      ? vscode.window.activeTextEditor.viewColumn
      : undefined;

    if (RepoWebviewPanel.currentPanel) {
      RepoWebviewPanel.currentPanel._panel.reveal(column);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      RepoWebviewPanel.viewType,
      'RepoDiscoverAI',
      column || vscode.ViewColumn.One,
      {
        enableScripts: true,
        localResourceRoots: [
          vscode.Uri.file(path.join(extensionPath, 'media'))
        ]
      }
    );

    RepoWebviewPanel.currentPanel = new RepoWebviewPanel(panel, extensionPath);
  }

  private constructor(panel: vscode.WebviewPanel, extensionPath: string) {
    this._panel = panel;
    this._extensionPath = extensionPath;

    this._update();

    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

    this._panel.webview.onDidReceiveMessage(
      async (message) => {
        switch (message.command) {
          case 'search':
            await this._doSearch(message.text);
            break;
          case 'clone':
            await this._doClone(message.url);
            break;
          case 'open':
            await this._doOpen(message.url);
            break;
        }
      },
      null,
      this._disposables
    );
  }

  public dispose() {
    RepoWebviewPanel.currentPanel = undefined;
    this._panel.dispose();
    while (this._disposables.length) {
      const x = this._disposables.pop();
      if (x) {
        x.dispose();
      }
    }
  }

  private async _doSearch(query: string) {
    try {
      const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
      const data: SearchResult = await response.json();
      
      this._panel.webview.postMessage({
        command: 'searchResults',
        repos: data.repos,
        total: data.total
      });
    } catch (error) {
      vscode.window.showErrorMessage(`Search failed: ${error}`);
    }
  }

  private async _doClone(url: string) {
    try {
      const clonePath = vscode.workspace.getConfiguration('repodiscoverai').get('clonePath', '~/projects');
      const expandedPath = clonePath.replace('~', require('os').homedir());
      
      if (!fs.existsSync(expandedPath)) {
        fs.mkdirSync(expandedPath, { recursive: true });
      }

      const repoName = url.split('/').pop()?.replace('.git', '') || 'repo';
      const targetPath = path.join(expandedPath, repoName);

      const terminal = vscode.window.createTerminal('Clone Repo');
      terminal.sendText(`git clone ${url} ${targetPath}`);
      terminal.show();

      vscode.window.showInformationMessage(`Cloning ${repoName} to ${targetPath}`);
    } catch (error) {
      vscode.window.showErrorMessage(`Clone failed: ${error}`);
    }
  }

  private async _doOpen(url: string) {
    await vscode.env.openExternal(vscode.Uri.parse(url));
  }

  private _update() {
    this._panel.title = 'RepoDiscoverAI';
    this._panel.webview.html = this._getHtmlForWebview();
  }

  private _getHtmlForWebview(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RepoDiscoverAI</title>
  <style>
    body {
      font-family: var(--vscode-font-family);
      padding: 20px;
      color: var(--vscode-foreground);
    }
    .search-box {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
    }
    .search-box input {
      flex: 1;
      padding: 8px 12px;
      border: 1px solid var(--vscode-input-border);
      background: var(--vscode-input-background);
      color: var(--vscode-input-foreground);
      border-radius: 4px;
    }
    .search-box button {
      padding: 8px 16px;
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    .repo-card {
      border: 1px solid var(--vscode-widget-border);
      border-radius: 6px;
      padding: 15px;
      margin-bottom: 15px;
      background: var(--vscode-widget-background);
    }
    .repo-name {
      font-size: 16px;
      font-weight: bold;
      color: var(--vscode-textLink-foreground);
      margin-bottom: 8px;
    }
    .repo-desc {
      color: var(--vscode-descriptionForeground);
      margin-bottom: 10px;
    }
    .repo-stats {
      display: flex;
      gap: 15px;
      font-size: 13px;
      color: var(--vscode-descriptionForeground);
    }
    .repo-actions {
      margin-top: 10px;
      display: flex;
      gap: 10px;
    }
    .repo-actions button {
      padding: 6px 12px;
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
    }
    .loading {
      text-align: center;
      padding: 40px;
      color: var(--vscode-descriptionForeground);
    }
    .trending-section {
      margin-bottom: 20px;
    }
    .section-title {
      font-size: 18px;
      font-weight: bold;
      margin-bottom: 15px;
    }
  </style>
</head>
<body>
  <div class="trending-section">
    <div class="section-title">🔥 Trending Repositories</div>
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="Search repositories..." />
      <button id="searchBtn">Search</button>
    </div>
  </div>
  
  <div id="results"></div>

  <script>
    const vscode = acquireVsCodeApi();
    
    document.getElementById('searchBtn').addEventListener('click', () => {
      const query = document.getElementById('searchInput').value;
      if (query) {
        vscode.postMessage({ command: 'search', text: query });
      }
    });

    document.getElementById('searchInput').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        const query = document.getElementById('searchInput').value;
        if (query) {
          vscode.postMessage({ command: 'search', text: query });
        }
      }
    });

    window.addEventListener('message', (event) => {
      const message = event.data;
      const resultsDiv = document.getElementById('results');
      
      if (message.command === 'searchResults') {
        if (message.repos.length === 0) {
          resultsDiv.innerHTML = '<div class="loading">No results found</div>';
          return;
        }

        resultsDiv.innerHTML = message.repos.map(repo => \`
          <div class="repo-card">
            <div class="repo-name">
              <a href="#" onclick="vscode.postMessage({command: 'open', url: '\${repo.html_url}'})">
                \${repo.full_name}
              </a>
            </div>
            <div class="repo-desc">\${repo.description || 'No description'}</div>
            <div class="repo-stats">
              <span>⭐ \${repo.stargazers_count}</span>
              <span>🍴 \${repo.forks_count}</span>
              <span>📦 \${repo.language || 'N/A'}</span>
            </div>
            <div class="repo-actions">
              <button onclick="vscode.postMessage({command: 'clone', url: '\${repo.clone_url}'})">
                📥 Clone
              </button>
              <button onclick="vscode.postMessage({command: 'open', url: '\${repo.html_url}'})">
                🔗 Open
              </button>
            </div>
          </div>
        \`).join('');
      }
    });

    // Load trending on startup
    vscode.postMessage({ command: 'search', text: '' });
  </script>
</body>
</html>`;
  }
}

/**
 * Extension activation
 */
export function activate(context: vscode.ExtensionContext) {
  console.log('RepoDiscoverAI extension is now active!');

  // Register search command
  const searchCommand = vscode.commands.registerCommand(
    'repodiscoverai.search',
    () => {
      RepoWebviewPanel.createOrShow(context.extensionPath);
    }
  );

  // Register trending command
  const trendingCommand = vscode.commands.registerCommand(
    'repodiscoverai.trending',
    async () => {
      const since = await vscode.window.showQuickPick(
        ['today', 'week', 'month'],
        { placeHolder: 'Select time period' }
      );

      if (since) {
        try {
          const response = await fetch(`${API_BASE}/api/trending?since=${since}`);
          const data = await response.json();
          
          const selected = await vscode.window.showQuickPick(
            data.repos.slice(0, 20).map((repo: Repository) => ({
              label: repo.full_name,
              description: `⭐ ${repo.stargazers_count} | ${repo.language}`,
              repo: repo
            })),
            { placeHolder: `Trending ${since} - Select a repo` }
          );

          if (selected) {
            const action = await vscode.window.showQuickPick(
              ['Open in Browser', 'Clone Repository'],
              { placeHolder: 'Select action' }
            );

            if (action === 'Open in Browser') {
              await vscode.env.openExternal(vscode.Uri.parse(selected.repo.html_url));
            } else if (action === 'Clone Repository') {
              const clonePath = vscode.workspace.getConfiguration('repodiscoverai').get('clonePath', '~/projects');
              const expandedPath = clonePath.replace('~', require('os').homedir());
              
              const repoName = selected.repo.clone_url.split('/').pop()?.replace('.git', '') || 'repo';
              const targetPath = path.join(expandedPath, repoName);

              const terminal = vscode.window.createTerminal('Clone Repo');
              terminal.sendText(`git clone ${selected.repo.clone_url} ${targetPath}`);
              terminal.show();
            }
          }
        } catch (error) {
          vscode.window.showErrorMessage(`Failed to fetch trending: ${error}`);
        }
      }
    }
  );

  // Register collections command
  const collectionsCommand = vscode.commands.registerCommand(
    'repodiscoverai.collections',
    async () => {
      vscode.window.showInformationMessage('Collections feature coming soon!');
    }
  );

  context.subscriptions.push(searchCommand, trendingCommand, collectionsCommand);
}

export function deactivate() {}
