import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Search, Send, Clock, FileJson, Copy, Loader2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SearchTest = () => {
  const [keys, setKeys] = useState([]);
  const [selectedKey, setSelectedKey] = useState('');
  const [query, setQuery] = useState('');
  const [intent, setIntent] = useState('');
  const [maxResults, setMaxResults] = useState(10);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [keysLoading, setKeysLoading] = useState(true);

  useEffect(() => {
    fetchKeys();
    seedSampleData();
  }, []);

  const fetchKeys = async () => {
    try {
      const response = await fetch(`${API}/keys`, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setKeys(data);
        if (data.length > 0) {
          // We need to create a key to test with, but we can't get the full key
          // So we'll prompt user to create one
        }
      }
    } catch (error) {
      console.error('Error fetching keys:', error);
    } finally {
      setKeysLoading(false);
    }
  };

  const seedSampleData = async () => {
    try {
      await fetch(`${API}/seed`, {
        method: 'POST',
        credentials: 'include'
      });
    } catch (error) {
      console.error('Error seeding data:', error);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    if (!selectedKey.trim()) {
      toast.error('Please enter an API key');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch(`${API}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': selectedKey
        },
        body: JSON.stringify({
          query,
          intent: intent || undefined,
          max_results: maxResults
        })
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
        toast.success(`Found ${data.total} results in ${data.processing_time_ms}ms`);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Search failed');
        setResult({ error: error.detail || 'Search failed' });
      }
    } catch (error) {
      console.error('Search error:', error);
      toast.error('Search failed');
      setResult({ error: 'Search request failed' });
    } finally {
      setLoading(false);
    }
  };

  const copyResult = () => {
    navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    toast.success('Copied to clipboard');
  };

  const exampleQueries = [
    { query: 'python async', intent: 'documentation' },
    { query: 'react components', intent: 'tutorial' },
    { query: 'kubernetes deployment', intent: 'infrastructure' },
    { query: 'api authentication', intent: 'security' }
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="search-test-page">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Search API Test</h1>
          <p className="text-muted-foreground mt-1">
            Test the Agent Query API with your API key.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Query Builder */}
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Search className="w-5 h-5" />
                Query Builder
              </CardTitle>
              <CardDescription>
                Build and test search queries
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="apiKey" className="text-sm uppercase tracking-wider text-muted-foreground">
                  API Key
                </Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="rmr_..."
                  value={selectedKey}
                  onChange={(e) => setSelectedKey(e.target.value)}
                  className="mt-2 font-mono"
                  data-testid="api-key-input"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Enter your API key (create one in API Keys page)
                </p>
              </div>

              <div>
                <Label htmlFor="query" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Search Query
                </Label>
                <Input
                  id="query"
                  placeholder="e.g., python async patterns"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="mt-2"
                  data-testid="search-query-input"
                />
              </div>

              <div>
                <Label htmlFor="intent" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Intent (Optional)
                </Label>
                <Input
                  id="intent"
                  placeholder="e.g., documentation, tutorial"
                  value={intent}
                  onChange={(e) => setIntent(e.target.value)}
                  className="mt-2"
                  data-testid="search-intent-input"
                />
              </div>

              <div>
                <Label htmlFor="maxResults" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Max Results
                </Label>
                <Input
                  id="maxResults"
                  type="number"
                  min="1"
                  max="50"
                  value={maxResults}
                  onChange={(e) => setMaxResults(parseInt(e.target.value) || 10)}
                  className="mt-2 w-24"
                  data-testid="max-results-input"
                />
              </div>

              <Button 
                onClick={handleSearch} 
                disabled={loading}
                className="w-full"
                data-testid="search-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    Execute Search
                  </>
                )}
              </Button>

              {/* Example Queries */}
              <div className="pt-4 border-t border-border/50">
                <p className="text-xs uppercase tracking-wider text-muted-foreground mb-3">
                  Try these examples
                </p>
                <div className="flex flex-wrap gap-2">
                  {exampleQueries.map((example, index) => (
                    <Badge
                      key={index}
                      variant="outline"
                      className="cursor-pointer hover:bg-secondary"
                      onClick={() => {
                        setQuery(example.query);
                        setIntent(example.intent);
                      }}
                    >
                      {example.query}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Response */}
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileJson className="w-5 h-5" />
                  Response
                </CardTitle>
                {result && !result.error && (
                  <Button variant="ghost" size="sm" onClick={copyResult}>
                    <Copy className="w-4 h-4 mr-2" />
                    Copy
                  </Button>
                )}
              </div>
              {result && !result.error && (
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {result.processing_time_ms}ms
                  </span>
                  <span>{result.total} results</span>
                </div>
              )}
            </CardHeader>
            <CardContent>
              {!result ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <Search className="w-12 h-12 mb-4 opacity-50" />
                  <p>Execute a search to see results</p>
                </div>
              ) : result.error ? (
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                  <p className="text-sm text-destructive">{result.error}</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {result.results?.length > 0 ? (
                    result.results.map((item, index) => (
                      <div
                        key={index}
                        className="p-4 rounded-lg bg-muted/30 border border-border/50"
                      >
                        <h4 className="font-medium text-sm">{item.title}</h4>
                        {item.url && (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary hover:underline mt-1 block truncate"
                          >
                            {item.url}
                          </a>
                        )}
                        {item.description && (
                          <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                            {item.description}
                          </p>
                        )}
                        {item.structured_data && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {Object.entries(item.structured_data).map(([key, value]) => (
                              <Badge key={key} variant="outline" className="text-xs">
                                {key}: {Array.isArray(value) ? value.join(', ') : String(value)}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>No results found</p>
                    </div>
                  )}
                  
                  {/* Raw JSON */}
                  <details className="mt-4">
                    <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                      View raw JSON
                    </summary>
                    <pre className="mt-2 p-4 bg-muted/50 rounded-lg text-xs overflow-x-auto">
                      <code>{JSON.stringify(result, null, 2)}</code>
                    </pre>
                  </details>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* API Reference */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-lg">API Reference</CardTitle>
            <CardDescription>How to use the Search API</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="p-4 bg-muted/50 rounded-lg text-sm overflow-x-auto">
              <code>{`POST ${API}/search
Headers:
  X-API-Key: rmr_your_api_key
  Content-Type: application/json

Body:
{
  "query": "python async patterns",
  "intent": "documentation",      // optional
  "filters": { "type": "docs" },  // optional
  "max_results": 10               // optional, default 10
}

Response:
{
  "results": [...],
  "total": 42,
  "query": "python async patterns",
  "processing_time_ms": 23
}`}</code>
            </pre>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default SearchTest;
