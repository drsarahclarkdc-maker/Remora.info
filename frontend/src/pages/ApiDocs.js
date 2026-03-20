import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  ArrowLeft,
  Copy,
  Check,
  Code2,
  Zap,
  Key,
  Webhook,
  Bot,
  Clock,
  FileJson,
  Terminal
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ApiDocs = () => {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [docs, setDocs] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copiedCode, setCopiedCode] = useState(null);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const response = await fetch(`${API}/docs/reference`);
        if (response.ok) {
          setDocs(await response.json());
        }
      } catch (error) {
        console.error('Error fetching docs:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, []);

  const copyCode = (code, id) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(id);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const CodeBlock = ({ code, language, id }) => (
    <div className="relative group">
      <pre className="p-4 bg-muted/50 rounded-lg text-sm overflow-x-auto border border-border/50">
        <code className="text-foreground">{code}</code>
      </pre>
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8"
        onClick={() => copyCode(code, id)}
      >
        {copiedCode === id ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
      </Button>
    </div>
  );

  const EndpointCard = ({ endpoint, data }) => (
    <Card className="bg-card/50 border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <Badge variant={data.method === 'GET' ? 'secondary' : 'default'} className="font-mono">
            {data.method}
          </Badge>
          <code className="text-sm font-mono text-primary">{data.path}</code>
        </div>
        <CardDescription className="mt-2">{data.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 text-sm">
          <Key className="w-4 h-4 text-muted-foreground" />
          <span className="text-muted-foreground">Auth:</span>
          <Badge variant="outline">{data.auth}</Badge>
        </div>
        
        {data.request && (
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Request Body</p>
            <div className="space-y-1 text-sm">
              {Object.entries(data.request).map(([key, value]) => (
                <div key={key} className="flex gap-2">
                  <code className="text-primary">{key}</code>
                  <span className="text-muted-foreground">— {value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {data.example_request && (
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Example Request</p>
            <CodeBlock 
              code={JSON.stringify(data.example_request, null, 2)} 
              language="json" 
              id={`${endpoint}-req`}
            />
          </div>
        )}
        
        {data.example_response && (
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Example Response</p>
            <CodeBlock 
              code={JSON.stringify(data.example_response, null, 2)} 
              language="json" 
              id={`${endpoint}-res`}
            />
          </div>
        )}
        
        {data.events && (
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Available Events</p>
            <div className="space-y-1">
              {data.events.map((event, i) => (
                <div key={i} className="text-sm flex items-start gap-2">
                  <Zap className="w-3 h-3 text-primary mt-1 flex-shrink-0" />
                  <span className="text-muted-foreground">{event}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/')} data-testid="back-btn">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <Search className="w-4 h-4 text-primary-foreground" />
              </div>
              <span className="font-semibold text-lg">Remora API Docs</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="font-mono">v{docs?.version}</Badge>
            {user ? (
              <Button onClick={() => navigate('/dashboard')} data-testid="dashboard-btn">
                Dashboard
              </Button>
            ) : (
              <Button onClick={login} data-testid="sign-in-btn">
                Sign In
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          {/* Hero */}
          <div className="text-center mb-16">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
              API Reference
            </h1>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Everything you need to integrate Remora into your AI agents. 
              JSON in, JSON out. Simple.
            </p>
          </div>

          {/* Quick Start */}
          <Card className="bg-primary/5 border-primary/20 mb-12">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-primary" />
                Quick Start
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-card/50 border border-border/50">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary">1</div>
                    <span className="font-medium">Get API Key</span>
                  </div>
                  <p className="text-sm text-muted-foreground">Sign in and create an API key from your dashboard</p>
                </div>
                <div className="p-4 rounded-lg bg-card/50 border border-border/50">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary">2</div>
                    <span className="font-medium">Make Request</span>
                  </div>
                  <p className="text-sm text-muted-foreground">Add X-API-Key header and POST to /api/search</p>
                </div>
                <div className="p-4 rounded-lg bg-card/50 border border-border/50">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary">3</div>
                    <span className="font-medium">Get Results</span>
                  </div>
                  <p className="text-sm text-muted-foreground">Receive structured JSON with search results</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Authentication */}
          <section className="mb-12">
            <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
              <Key className="w-6 h-6" />
              Authentication
            </h2>
            <Card className="bg-card/50 border-border/50">
              <CardContent className="p-6">
                <p className="text-muted-foreground mb-4">
                  {docs?.authentication?.description}
                </p>
                <CodeBlock 
                  code={`curl -X POST "${BACKEND_URL}/api/search" \\
    -H "X-API-Key: rmr_your_api_key_here" \\
    -H "Content-Type: application/json" \\
    -d '{"query": "python async"}'`}
                  language="bash"
                  id="auth-example"
                />
              </CardContent>
            </Card>
          </section>

          {/* Endpoints */}
          <section className="mb-12">
            <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
              <Terminal className="w-6 h-6" />
              Endpoints
            </h2>
            
            <Tabs defaultValue="search" className="w-full">
              <TabsList className="grid w-full grid-cols-2 md:grid-cols-4 lg:grid-cols-6 mb-6">
                <TabsTrigger value="search">Search</TabsTrigger>
                <TabsTrigger value="content">Content</TabsTrigger>
                <TabsTrigger value="crawl">Crawl</TabsTrigger>
                <TabsTrigger value="bulk">Bulk Crawl</TabsTrigger>
                <TabsTrigger value="schedule">Schedule</TabsTrigger>
                <TabsTrigger value="webhooks">Webhooks</TabsTrigger>
              </TabsList>
              
              <TabsContent value="search" className="space-y-4">
                {docs?.endpoints?.search && (
                  <EndpointCard endpoint="search" data={docs.endpoints.search} />
                )}
              </TabsContent>
              
              <TabsContent value="content" className="space-y-4">
                {docs?.endpoints?.content && (
                  <EndpointCard endpoint="content" data={docs.endpoints.content} />
                )}
              </TabsContent>
              
              <TabsContent value="crawl" className="space-y-4">
                {docs?.endpoints?.crawl && (
                  <EndpointCard endpoint="crawl" data={docs.endpoints.crawl} />
                )}
              </TabsContent>
              
              <TabsContent value="bulk" className="space-y-4">
                {docs?.endpoints?.bulk_crawl && (
                  <EndpointCard endpoint="bulk_crawl" data={docs.endpoints.bulk_crawl} />
                )}
                {docs?.endpoints?.crawl_job_status && (
                  <EndpointCard endpoint="crawl_job_status" data={docs.endpoints.crawl_job_status} />
                )}
              </TabsContent>
              
              <TabsContent value="schedule" className="space-y-4">
                {docs?.endpoints?.schedule_crawl && (
                  <EndpointCard endpoint="schedule_crawl" data={docs.endpoints.schedule_crawl} />
                )}
              </TabsContent>
              
              <TabsContent value="webhooks" className="space-y-4">
                {docs?.endpoints?.webhooks && (
                  <EndpointCard endpoint="webhooks" data={docs.endpoints.webhooks} />
                )}
              </TabsContent>
            </Tabs>
          </section>

          {/* Code Examples */}
          <section className="mb-12">
            <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
              <Code2 className="w-6 h-6" />
              Code Examples
            </h2>
            
            <Tabs defaultValue="python" className="w-full">
              <TabsList className="mb-4">
                <TabsTrigger value="python">Python</TabsTrigger>
                <TabsTrigger value="javascript">JavaScript</TabsTrigger>
                <TabsTrigger value="curl">cURL</TabsTrigger>
              </TabsList>
              
              <TabsContent value="python">
                <CodeBlock 
                  code={docs?.code_examples?.python || '# Loading...'} 
                  language="python"
                  id="python-example"
                />
              </TabsContent>
              
              <TabsContent value="javascript">
                <CodeBlock 
                  code={docs?.code_examples?.javascript || '// Loading...'} 
                  language="javascript"
                  id="js-example"
                />
              </TabsContent>
              
              <TabsContent value="curl">
                <CodeBlock 
                  code={docs?.code_examples?.curl || '# Loading...'} 
                  language="bash"
                  id="curl-example"
                />
              </TabsContent>
            </Tabs>
          </section>

          {/* Rate Limits */}
          <section>
            <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
              <Clock className="w-6 h-6" />
              Rate Limits
            </h2>
            <Card className="bg-card/50 border-border/50">
              <CardContent className="p-6">
                <div className="flex items-center gap-3 mb-4">
                  <Badge className="bg-primary text-primary-foreground">Free for Everyone</Badge>
                  <span className="text-muted-foreground">Unlimited requests</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {docs?.rate_limits?.note}
                </p>
              </CardContent>
            </Card>
          </section>
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border mt-12">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Search className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold">Remora</span>
          </div>
          <p className="text-sm text-muted-foreground">
            The Search Engine for AI Agents
          </p>
        </div>
      </footer>
    </div>
  );
};

export default ApiDocs;
