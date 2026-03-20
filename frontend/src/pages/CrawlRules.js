import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { toast } from 'sonner';
import { 
  Settings2, 
  Plus, 
  Trash2, 
  Edit2, 
  Globe,
  Code2,
  Clock,
  Shield
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CrawlRules = () => {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [deleteRuleId, setDeleteRuleId] = useState(null);
  
  const [formData, setFormData] = useState({
    domain: '',
    name: '',
    title_selector: '',
    content_selector: '',
    description_selector: '',
    exclude_selectors: '',
    follow_links: false,
    max_depth: 1,
    allowed_paths: '',
    blocked_paths: '',
    delay_ms: 1000,
    max_pages: 100,
    custom_headers: ''
  });

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const response = await fetch(`${API}/rules`, { credentials: 'include' });
      if (response.ok) {
        setRules(await response.json());
      }
    } catch (error) {
      console.error('Error fetching rules:', error);
      toast.error('Failed to load crawl rules');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (rule = null) => {
    if (rule) {
      setEditingRule(rule);
      setFormData({
        domain: rule.domain,
        name: rule.name,
        title_selector: rule.title_selector || '',
        content_selector: rule.content_selector || '',
        description_selector: rule.description_selector || '',
        exclude_selectors: (rule.exclude_selectors || []).join('\n'),
        follow_links: rule.follow_links || false,
        max_depth: rule.max_depth || 1,
        allowed_paths: (rule.allowed_paths || []).join('\n'),
        blocked_paths: (rule.blocked_paths || []).join('\n'),
        delay_ms: rule.delay_ms || 1000,
        max_pages: rule.max_pages || 100,
        custom_headers: rule.custom_headers ? JSON.stringify(rule.custom_headers, null, 2) : ''
      });
    } else {
      setEditingRule(null);
      setFormData({
        domain: '',
        name: '',
        title_selector: '',
        content_selector: '',
        description_selector: '',
        exclude_selectors: '',
        follow_links: false,
        max_depth: 1,
        allowed_paths: '',
        blocked_paths: '',
        delay_ms: 1000,
        max_pages: 100,
        custom_headers: ''
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.domain.trim() || !formData.name.trim()) {
      toast.error('Please fill in domain and name');
      return;
    }

    try {
      const body = {
        domain: formData.domain,
        name: formData.name,
        title_selector: formData.title_selector || null,
        content_selector: formData.content_selector || null,
        description_selector: formData.description_selector || null,
        exclude_selectors: formData.exclude_selectors ? formData.exclude_selectors.split('\n').filter(s => s.trim()) : [],
        follow_links: formData.follow_links,
        max_depth: formData.max_depth,
        allowed_paths: formData.allowed_paths ? formData.allowed_paths.split('\n').filter(s => s.trim()) : [],
        blocked_paths: formData.blocked_paths ? formData.blocked_paths.split('\n').filter(s => s.trim()) : [],
        delay_ms: formData.delay_ms,
        max_pages: formData.max_pages,
        custom_headers: formData.custom_headers ? JSON.parse(formData.custom_headers) : {}
      };

      const url = editingRule ? `${API}/rules/${editingRule.rule_id}` : `${API}/rules`;
      const method = editingRule ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body)
      });

      if (response.ok) {
        fetchRules();
        setDialogOpen(false);
        toast.success(editingRule ? 'Rule updated' : 'Rule created');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save rule');
      }
    } catch (error) {
      console.error('Error saving rule:', error);
      toast.error('Failed to save rule');
    }
  };

  const handleDelete = async () => {
    if (!deleteRuleId) return;

    try {
      const response = await fetch(`${API}/rules/${deleteRuleId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        setRules(rules.filter(r => r.rule_id !== deleteRuleId));
        toast.success('Rule deleted');
      } else {
        toast.error('Failed to delete rule');
      }
    } catch (error) {
      console.error('Error deleting rule:', error);
      toast.error('Failed to delete rule');
    } finally {
      setDeleteRuleId(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="crawl-rules-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Crawl Rules</h1>
            <p className="text-muted-foreground mt-1">
              Define custom extraction rules for specific domains.
            </p>
          </div>
          <Button onClick={() => handleOpenDialog()} data-testid="add-rule-btn">
            <Plus className="w-4 h-4 mr-2" />
            Add Rule
          </Button>
        </div>

        {/* Rules List */}
        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : rules.length === 0 ? (
            <Card className="bg-card/50 border-border/50">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="w-16 h-16 rounded-xl bg-muted flex items-center justify-center mb-4">
                  <Settings2 className="w-8 h-8 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-center">No crawl rules yet</p>
                <p className="text-sm text-muted-foreground mt-1 text-center">
                  Create rules to customize how specific domains are crawled.
                </p>
                <Button className="mt-4" onClick={() => handleOpenDialog()}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Rule
                </Button>
              </CardContent>
            </Card>
          ) : (
            rules.map((rule) => (
              <Card 
                key={rule.rule_id} 
                className="bg-card/50 border-border/50"
                data-testid={`rule-card-${rule.rule_id}`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4 min-w-0 flex-1">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Settings2 className="w-5 h-5 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-semibold">{rule.name}</h3>
                          <Badge variant={rule.is_active ? 'default' : 'secondary'} className="text-xs">
                            {rule.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                        
                        <div className="flex items-center gap-2 mt-2">
                          <Globe className="w-3 h-3 text-muted-foreground" />
                          <code className="text-xs text-muted-foreground font-mono">
                            {rule.domain}
                          </code>
                        </div>

                        <div className="flex flex-wrap gap-3 mt-3 text-xs text-muted-foreground">
                          {rule.content_selector && (
                            <span className="flex items-center gap-1">
                              <Code2 className="w-3 h-3" />
                              Custom selectors
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {rule.delay_ms}ms delay
                          </span>
                          {rule.follow_links && (
                            <Badge variant="outline" className="text-xs">
                              Follows links (depth: {rule.max_depth})
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex gap-2 flex-shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleOpenDialog(rule)}
                        data-testid={`edit-rule-${rule.rule_id}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteRuleId(rule.rule_id)}
                        data-testid={`delete-rule-${rule.rule_id}`}
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

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingRule ? 'Edit Crawl Rule' : 'Create Crawl Rule'}</DialogTitle>
              <DialogDescription>
                Define custom extraction rules for a domain.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm uppercase tracking-wider text-muted-foreground">
                    Domain
                  </Label>
                  <Input
                    placeholder="docs.example.com"
                    value={formData.domain}
                    onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                    className="mt-2 font-mono"
                    disabled={!!editingRule}
                    data-testid="rule-domain-input"
                  />
                </div>
                <div>
                  <Label className="text-sm uppercase tracking-wider text-muted-foreground">
                    Name
                  </Label>
                  <Input
                    placeholder="Example Docs Rule"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="mt-2"
                    data-testid="rule-name-input"
                  />
                </div>
              </div>

              <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="selectors">
                  <AccordionTrigger>CSS Selectors</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-4">
                    <div>
                      <Label className="text-sm text-muted-foreground">Title Selector</Label>
                      <Input
                        placeholder="h1.article-title"
                        value={formData.title_selector}
                        onChange={(e) => setFormData({ ...formData, title_selector: e.target.value })}
                        className="mt-1 font-mono text-sm"
                      />
                    </div>
                    <div>
                      <Label className="text-sm text-muted-foreground">Content Selector</Label>
                      <Input
                        placeholder="article.main-content"
                        value={formData.content_selector}
                        onChange={(e) => setFormData({ ...formData, content_selector: e.target.value })}
                        className="mt-1 font-mono text-sm"
                      />
                    </div>
                    <div>
                      <Label className="text-sm text-muted-foreground">Description Selector</Label>
                      <Input
                        placeholder="meta[name='description']"
                        value={formData.description_selector}
                        onChange={(e) => setFormData({ ...formData, description_selector: e.target.value })}
                        className="mt-1 font-mono text-sm"
                      />
                    </div>
                    <div>
                      <Label className="text-sm text-muted-foreground">Exclude Selectors (one per line)</Label>
                      <Textarea
                        placeholder=".sidebar&#10;.ads&#10;footer"
                        value={formData.exclude_selectors}
                        onChange={(e) => setFormData({ ...formData, exclude_selectors: e.target.value })}
                        className="mt-1 font-mono text-sm min-h-[80px]"
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                <AccordionItem value="crawling">
                  <AccordionTrigger>Crawling Behavior</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <Label>Follow Links</Label>
                        <p className="text-xs text-muted-foreground">Crawl linked pages within the domain</p>
                      </div>
                      <Switch
                        checked={formData.follow_links}
                        onCheckedChange={(checked) => setFormData({ ...formData, follow_links: checked })}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-sm text-muted-foreground">Max Depth</Label>
                        <Input
                          type="number"
                          min="1"
                          max="5"
                          value={formData.max_depth}
                          onChange={(e) => setFormData({ ...formData, max_depth: parseInt(e.target.value) || 1 })}
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-sm text-muted-foreground">Max Pages</Label>
                        <Input
                          type="number"
                          min="1"
                          max="1000"
                          value={formData.max_pages}
                          onChange={(e) => setFormData({ ...formData, max_pages: parseInt(e.target.value) || 100 })}
                          className="mt-1"
                        />
                      </div>
                    </div>
                    <div>
                      <Label className="text-sm text-muted-foreground">Delay Between Requests (ms)</Label>
                      <Input
                        type="number"
                        min="100"
                        max="10000"
                        value={formData.delay_ms}
                        onChange={(e) => setFormData({ ...formData, delay_ms: parseInt(e.target.value) || 1000 })}
                        className="mt-1"
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                <AccordionItem value="paths">
                  <AccordionTrigger>URL Patterns</AccordionTrigger>
                  <AccordionContent className="space-y-4 pt-4">
                    <div>
                      <Label className="text-sm text-muted-foreground">Allowed Paths (one per line)</Label>
                      <Textarea
                        placeholder="/docs/*&#10;/api/*"
                        value={formData.allowed_paths}
                        onChange={(e) => setFormData({ ...formData, allowed_paths: e.target.value })}
                        className="mt-1 font-mono text-sm min-h-[80px]"
                      />
                    </div>
                    <div>
                      <Label className="text-sm text-muted-foreground">Blocked Paths (one per line)</Label>
                      <Textarea
                        placeholder="/admin/*&#10;/login"
                        value={formData.blocked_paths}
                        onChange={(e) => setFormData({ ...formData, blocked_paths: e.target.value })}
                        className="mt-1 font-mono text-sm min-h-[80px]"
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>

                <AccordionItem value="headers">
                  <AccordionTrigger>Custom Headers</AccordionTrigger>
                  <AccordionContent className="pt-4">
                    <div>
                      <Label className="text-sm text-muted-foreground">Headers (JSON)</Label>
                      <Textarea
                        placeholder='{"Authorization": "Bearer token"}'
                        value={formData.custom_headers}
                        onChange={(e) => setFormData({ ...formData, custom_headers: e.target.value })}
                        className="mt-1 font-mono text-sm min-h-[80px]"
                      />
                    </div>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSubmit} data-testid="save-rule-btn">
                {editingRule ? 'Save Changes' : 'Create Rule'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation */}
        <AlertDialog open={!!deleteRuleId} onOpenChange={() => setDeleteRuleId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Crawl Rule?</AlertDialogTitle>
              <AlertDialogDescription>
                This will remove the custom extraction rules for this domain.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                Delete Rule
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </DashboardLayout>
  );
};

export default CrawlRules;
