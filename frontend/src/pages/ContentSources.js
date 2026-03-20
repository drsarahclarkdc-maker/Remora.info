import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { toast } from 'sonner';
import { 
  Globe, 
  Plus, 
  Trash2, 
  RefreshCw, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  ExternalLink,
  Loader2
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ContentSources = () => {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteSourceId, setDeleteSourceId] = useState(null);
  const [crawlingSourceId, setCrawlingSourceId] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    crawl_frequency: ''
  });

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    try {
      const response = await fetch(`${API}/sources`, { credentials: 'include' });
      if (response.ok) {
        setSources(await response.json());
      }
    } catch (error) {
      console.error('Error fetching sources:', error);
      toast.error('Failed to load content sources');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.name.trim() || !formData.url.trim()) {
      toast.error('Please fill in name and URL');
      return;
    }

    try {
      const body = {
        name: formData.name,
        url: formData.url
      };
      if (formData.crawl_frequency && formData.crawl_frequency !== 'manual') {
        body.crawl_frequency = formData.crawl_frequency;
      }

      const response = await fetch(`${API}/sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body)
      });

      if (response.ok) {
        fetchSources();
        setDialogOpen(false);
        setFormData({ name: '', url: '', crawl_frequency: '' });
        toast.success('Content source created and initial crawl complete');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create source');
      }
    } catch (error) {
      console.error('Error creating source:', error);
      toast.error('Failed to create source');
    }
  };

  const handleDelete = async () => {
    if (!deleteSourceId) return;

    try {
      const response = await fetch(`${API}/sources/${deleteSourceId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        setSources(sources.filter(s => s.source_id !== deleteSourceId));
        toast.success('Content source deleted');
      } else {
        toast.error('Failed to delete source');
      }
    } catch (error) {
      console.error('Error deleting source:', error);
      toast.error('Failed to delete source');
    } finally {
      setDeleteSourceId(null);
    }
  };

  const handleCrawl = async (sourceId) => {
    setCrawlingSourceId(sourceId);
    try {
      const response = await fetch(`${API}/sources/${sourceId}/crawl`, {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Crawled: ${result.title}`);
        fetchSources();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Crawl failed');
      }
    } catch (error) {
      console.error('Error crawling source:', error);
      toast.error('Crawl failed');
    } finally {
      setCrawlingSourceId(null);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="content-sources-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Content Sources</h1>
            <p className="text-muted-foreground mt-1">
              Manage URLs to crawl and keep content fresh.
            </p>
          </div>
          <Button onClick={() => setDialogOpen(true)} data-testid="add-source-btn">
            <Plus className="w-4 h-4 mr-2" />
            Add Source
          </Button>
        </div>

        {/* Sources List */}
        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : sources.length === 0 ? (
            <Card className="bg-card/50 border-border/50">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="w-16 h-16 rounded-xl bg-muted flex items-center justify-center mb-4">
                  <Globe className="w-8 h-8 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-center">No content sources yet</p>
                <p className="text-sm text-muted-foreground mt-1 text-center">
                  Add a source to start crawling content.
                </p>
                <Button className="mt-4" onClick={() => setDialogOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Source
                </Button>
              </CardContent>
            </Card>
          ) : (
            sources.map((source) => (
              <Card 
                key={source.source_id} 
                className="bg-card/50 border-border/50"
                data-testid={`source-card-${source.source_id}`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4 min-w-0 flex-1">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Globe className="w-5 h-5 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-semibold">{source.name}</h3>
                          <Badge variant={source.is_active ? 'default' : 'secondary'} className="text-xs">
                            {source.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                          {source.crawl_frequency && (
                            <Badge variant="outline" className="text-xs">
                              <Clock className="w-3 h-3 mr-1" />
                              {source.crawl_frequency}
                            </Badge>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-2 mt-2">
                          <code className="text-xs text-muted-foreground font-mono truncate max-w-md">
                            {source.url}
                          </code>
                          <a href={source.url} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="w-3 h-3 text-muted-foreground hover:text-primary" />
                          </a>
                        </div>

                        <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            {source.last_status === 'success' ? (
                              <CheckCircle2 className="w-3 h-3 text-green-500" />
                            ) : source.last_status?.startsWith('failed') ? (
                              <XCircle className="w-3 h-3 text-destructive" />
                            ) : (
                              <Clock className="w-3 h-3" />
                            )}
                            Last crawl: {formatDate(source.last_crawl)}
                          </span>
                          <span>
                            {source.content_count || 0} items crawled
                          </span>
                          <span className="text-muted-foreground/60">
                            {source.domain}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex gap-2 flex-shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleCrawl(source.source_id)}
                        disabled={crawlingSourceId === source.source_id}
                        data-testid={`crawl-source-${source.source_id}`}
                      >
                        {crawlingSourceId === source.source_id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <RefreshCw className="w-4 h-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteSourceId(source.source_id)}
                        data-testid={`delete-source-${source.source_id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        {/* Create Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Add Content Source</DialogTitle>
              <DialogDescription>
                Add a URL to crawl. Optionally set up automatic crawling.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="name" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Name
                </Label>
                <Input
                  id="name"
                  placeholder="e.g., Python Docs"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="mt-2"
                  data-testid="source-name-input"
                />
              </div>

              <div>
                <Label htmlFor="url" className="text-sm uppercase tracking-wider text-muted-foreground">
                  URL
                </Label>
                <Input
                  id="url"
                  type="url"
                  placeholder="https://docs.python.org/3/"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  className="mt-2"
                  data-testid="source-url-input"
                />
              </div>

              <div>
                <Label htmlFor="frequency" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Crawl Frequency
                </Label>
                <Select 
                  value={formData.crawl_frequency} 
                  onValueChange={(value) => setFormData({ ...formData, crawl_frequency: value })}
                >
                  <SelectTrigger className="mt-2" data-testid="source-frequency-select">
                    <SelectValue placeholder="Select frequency" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual only</SelectItem>
                    <SelectItem value="hourly">Hourly</SelectItem>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">
                  How often to automatically refresh this content.
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleCreate} data-testid="save-source-btn">
                Add Source
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation */}
        <AlertDialog open={!!deleteSourceId} onOpenChange={() => setDeleteSourceId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Content Source?</AlertDialogTitle>
              <AlertDialogDescription>
                This will delete the source and any associated scheduled crawls. Crawled content will remain.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                Delete Source
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </DashboardLayout>
  );
};

export default ContentSources;
