# RepoDiscoverAI for VS Code

Search and discover awesome GitHub repositories without leaving your IDE.

## Features

- 🔍 **Search Repositories** - Search 5000+ curated GitHub repos
- 📊 **View Details** - See repo stats, description, and technologies
- 🚀 **Quick Clone** - Clone repos directly from VS Code
- 🔥 **Trending** - View daily/weekly/monthly trending repos
- ⭐ **Collections** - Access your saved collections

## Installation

### From VSIX (Development)

1. Build the extension:
```bash
npm install
npm run compile
npm run package
```

2. Install the VSIX:
```bash
code --install-extension repodiscoverai-0.1.0.vsix
```

### From Marketplace (Coming Soon)

```bash
# Will be available soon on VS Code Marketplace
```

## Usage

### Search Repositories

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type "RepoDiscoverAI: Search Repositories"
3. Enter your search query
4. Browse results and click to view details

### View Trending

1. Press `Ctrl+Shift+P`
2. Type "RepoDiscoverAI: View Trending"
3. Select time period (today/week/month)

### Quick Clone

1. Search for a repository
2. Click the clone button in the webview
3. Repo will be cloned to your default projects folder

## Commands

| Command | Description |
|---------|-------------|
| `RepoDiscoverAI: Search` | Search repositories |
| `RepoDiscoverAI: Trending` | View trending repos |
| `RepoDiscoverAI: Collections` | View your collections |
| `RepoDiscoverAI: Clone` | Clone a repository |
| `RepoDiscoverAI: Open Details` | Open repo details in webview |

## Configuration

Add these to your `settings.json`:

```json
{
  "repodiscoverai.apiUrl": "https://api.repodiscover.ai",
  "repodiscoverai.clonePath": "~/projects",
  "repodiscoverai.showStars": true,
  "repodiscoverai.defaultLanguage": "all"
}
```

## Screenshots

### Search Interface
![Search](images/search.png)

### Repo Details
![Details](images/details.png)

### Trending View
![Trending](images/trending.png)

## Development

### Prerequisites

- Node.js >= 18
- npm >= 9
- VS Code

### Setup

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Run extension (opens new VS Code window)
npm run watch
```

### Debug

1. Open this folder in VS Code
2. Press `F5` to launch Extension Development Host
3. Test commands in the new window

### Package

```bash
npm run package
```

## API Integration

The extension connects to the RepoDiscoverAI API:

```typescript
const API_BASE = 'https://api.repodiscover.ai';

// Search repositories
async function search(query: string) {
  const response = await fetch(`${API_BASE}/api/search?q=${query}`);
  return response.json();
}

// Get trending
async function getTrending(since: string) {
  const response = await fetch(`${API_BASE}/api/trending?since=${since}`);
  return response.json();
}
```

## Changelog

### 0.1.0 (2026-03-09)
- Initial release
- Search functionality
- Trending view
- Quick clone
- Webview details

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md).

## Support

- 📧 Email: support@repodiscover.ai
- 💬 Discord: https://discord.gg/repodiscoverai
- 🐛 Issues: https://github.com/weisenchen/RepoDiscoverAI/issues
