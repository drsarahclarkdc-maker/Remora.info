import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
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
import { toast } from 'sonner';
import { 
  ArrowUpDown, 
  Plus, 
  Trash2, 
  Edit2, 
  Star,
  TrendingUp,
  Globe,
  FileText
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SearchRanking = () => {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);
  const [deleteConfigId, setDeleteConfigId] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    title_weight: 2.0,
    description_weight: 1.5,
    content_weight: 1.0,
    recency_boost: true,
    recency_decay_days: 30,
    boosted_domains: '',
    penalized_domains: '',
    domain_boost_factor: 1.5,
    preferred_types: '',
    type_boost_factor: 1.3,
    is_default: false,
  });

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      const response = await fetch(`${API}/ranking`, { credentials: 'include' });
      if (response.ok) {
        setConfigs(await response.json());
      }
    } catch (error) {
      console.error('Error fetching ranking configs:', error);
      toast.error('Failed to load ranking configurations');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (config = null) => {
    if (config) {
      setEditingConfig(config);
      setFormData({
        name: config.name,
        title_weight: config.title_weight,
        description_weight: config.description_weight,
        content_weight: config.content_weight,
        recency_boost: config.recency_boost,
        recency_decay_days: config.recency_decay_days,
        boosted_domains: (config.boosted_domains || []).join('\n'),
        penalized_domains: (config.penalized_domains || []).join('\n'),
        domain_boost_factor: config.domain_boost_factor,
        preferred_types: (config.preferred_types || []).join('\n'),
        type_boost_factor: config.type_boost_factor,
        is_default: config.is_default,
      });
    } else {
      setEditingConfig(null);
      setFormData({
        name: '',
        title_weight: 2.0,
        description_weight: 1.5,
        content_weight: 1.0,
        recency_boost: true,
        recency_decay_days: 30,
        boosted_domains: '',
        penalized_domains: '',
        domain_boost_factor: 1.5,
        preferred_types: '',
        type_boost_factor: 1.3,
        is_default: false,
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.name.trim()) {
      toast.error('Please enter a configuration name');
      return;
    }

    try {
      const body = {
        name: formData.name,
        title_weight: formData.title_weight,
        description_weight: formData.description_weight,
        content_weight: formData.content_weight,
        recency_boost: formData.recency_boost,
        recency_decay_days: formData.recency_decay_days,
        boosted_domains: formData.boosted_domains ? formData.boosted_domains.split('\n').filter(s => s.trim()) : [],
        penalized_domains: formData.penalized_domains ? formData.penalized_domains.split('\n').filter(s => s.trim()) : [],
        domain_boost_factor: formData.domain_boost_factor,
        preferred_types: formData.preferred_types ? formData.preferred_types.split('\n').filter(s => s.trim()) : [],
        type_boost_factor: formData.type_boost_factor,
        is_default: formData.is_default,
      };

      const url = editingConfig ? `${API}/ranking/${editingConfig.config_id}` : `${API}/ranking`;
      const method = editingConfig ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });

      if (response.ok) {
        fetchConfigs();
        setDialogOpen(false);
        toast.success(editingConfig ? 'Configuration updated' : 'Configuration created');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to save configuration');
      }
    } catch (error) {
      console.error('Error saving config:', error);
      toast.error('Failed to save configuration');
    }
  };

  const handleDelete = async () => {
    if (!deleteConfigId) return;

    try {
      const response = await fetch(`${API}/ranking/${deleteConfigId}`, {
        method: 'DELETE',
        credentials: 'include',
      });

      if (response.ok) {
        setConfigs(configs.filter(c => c.config_id !== deleteConfigId));
        toast.success('Configuration deleted');
      } else {
        toast.error('Failed to delete configuration');
      }
    } catch (error) {
      console.error('Error deleting config:', error);
      toast.error('Failed to delete configuration');
    } finally {
      setDeleteConfigId(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="search-ranking-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Search Ranking</h1>
            <p className="text-muted-foreground mt-1">
              Fine-tune how search results are ranked and scored.
            </p>
          </div>
          <Button onClick={() => handleOpenDialog()} data-testid="add-ranking-config-btn">
            <Plus className="w-4 h-4 mr-2" />
            New Configuration
          </Button>
        </div>

        {/* Configs List */}
        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : configs.length === 0 ? (
            <Card className="bg-card/50 border-border/50">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="w-16 h-16 rounded-xl bg-muted flex items-center justify-center mb-4">
                  <ArrowUpDown className="w-8 h-8 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-center">No ranking configurations</p>
                <p className="text-sm text-muted-foreground mt-1 text-center">
                  Create a configuration to customize how search results are ranked.
                </p>
                <Button className="mt-4" onClick={() => handleOpenDialog()}>
                  <Plus className="w-4 h-4 mr-2" />
                  New Configuration
                </Button>
              </CardContent>
            </Card>
          ) : (
            configs.map((config) => (
              <Card
                key={config.config_id}
                className={`bg-card/50 border-border/50 ${config.is_default ? 'ring-1 ring-primary/30' : ''}`}
                data-testid={`ranking-card-${config.config_id}`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4 min-w-0 flex-1">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <ArrowUpDown className="w-5 h-5 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-semibold">{config.name}</h3>
                          {config.is_default && (
                            <Badge className="bg-primary/10 text-primary border-primary/20 text-xs">
                              <Star className="w-3 h-3 mr-1" />
                              Default
                            </Badge>
                          )}
                        </div>

                        <div className="flex flex-wrap gap-4 mt-3 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <FileText className="w-3 h-3" />
                            Title: {config.title_weight}x
                          </span>
                          <span className="flex items-center gap-1">
                            <FileText className="w-3 h-3" />
                            Content: {config.content_weight}x
                          </span>
                          {config.recency_boost && (
                            <span className="flex items-center gap-1">
                              <TrendingUp className="w-3 h-3" />
                              Recency: {config.recency_decay_days}d decay
                            </span>
                          )}
                          {config.boosted_domains?.length > 0 && (
                            <span className="flex items-center gap-1">
                              <Globe className="w-3 h-3" />
                              {config.boosted_domains.length} boosted domain{config.boosted_domains.length > 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-2 flex-shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleOpenDialog(config)}
                        data-testid={`edit-ranking-${config.config_id}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteConfigId(config.config_id)}
                        data-testid={`delete-ranking-${config.config_id}`}
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
              <DialogTitle>{editingConfig ? 'Edit Ranking Config' : 'New Ranking Config'}</DialogTitle>
              <DialogDescription>
                Configure weights and boosts for search result ranking.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 py-4">
              {/* Name & Default */}
              <div className="flex items-end gap-4">
                <div className="flex-1">
                  <Label className="text-sm uppercase tracking-wider text-muted-foreground">Name</Label>
                  <Input
                    placeholder="My Ranking Profile"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="mt-2"
                    data-testid="ranking-name-input"
                  />
                </div>
                <div className="flex items-center gap-2 pb-2">
                  <Switch
                    checked={formData.is_default}
                    onCheckedChange={(checked) => setFormData({ ...formData, is_default: checked })}
                    data-testid="ranking-default-switch"
                  />
                  <Label className="text-sm">Default</Label>
                </div>
              </div>

              {/* Field Weights */}
              <Card className="bg-muted/30 border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">Field Weights</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Title Weight</span>
                      <span className="font-mono text-muted-foreground">{formData.title_weight}x</span>
                    </div>
                    <Slider
                      value={[formData.title_weight]}
                      onValueChange={([v]) => setFormData({ ...formData, title_weight: v })}
                      min={0.1}
                      max={5}
                      step={0.1}
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Description Weight</span>
                      <span className="font-mono text-muted-foreground">{formData.description_weight}x</span>
                    </div>
                    <Slider
                      value={[formData.description_weight]}
                      onValueChange={([v]) => setFormData({ ...formData, description_weight: v })}
                      min={0.1}
                      max={5}
                      step={0.1}
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Content Weight</span>
                      <span className="font-mono text-muted-foreground">{formData.content_weight}x</span>
                    </div>
                    <Slider
                      value={[formData.content_weight]}
                      onValueChange={([v]) => setFormData({ ...formData, content_weight: v })}
                      min={0.1}
                      max={5}
                      step={0.1}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Recency Boost */}
              <Card className="bg-muted/30 border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">Recency Boost</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Enable Recency Boost</Label>
                      <p className="text-xs text-muted-foreground">Boost newer content in results</p>
                    </div>
                    <Switch
                      checked={formData.recency_boost}
                      onCheckedChange={(checked) => setFormData({ ...formData, recency_boost: checked })}
                    />
                  </div>
                  {formData.recency_boost && (
                    <div>
                      <Label className="text-sm text-muted-foreground">Decay Period (days)</Label>
                      <Input
                        type="number"
                        min={1}
                        max={365}
                        value={formData.recency_decay_days}
                        onChange={(e) => setFormData({ ...formData, recency_decay_days: parseInt(e.target.value) || 30 })}
                        className="mt-1"
                      />
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Domain Preferences */}
              <Card className="bg-muted/30 border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">Domain Preferences</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-sm text-muted-foreground">Boosted Domains (one per line)</Label>
                    <Textarea
                      placeholder={"docs.python.org\nmdn.mozilla.org"}
                      value={formData.boosted_domains}
                      onChange={(e) => setFormData({ ...formData, boosted_domains: e.target.value })}
                      className="mt-1 font-mono text-sm min-h-[80px]"
                    />
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">Penalized Domains (one per line)</Label>
                    <Textarea
                      placeholder={"spam-site.com\nlow-quality.net"}
                      value={formData.penalized_domains}
                      onChange={(e) => setFormData({ ...formData, penalized_domains: e.target.value })}
                      className="mt-1 font-mono text-sm min-h-[80px]"
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Domain Boost Factor</span>
                      <span className="font-mono text-muted-foreground">{formData.domain_boost_factor}x</span>
                    </div>
                    <Slider
                      value={[formData.domain_boost_factor]}
                      onValueChange={([v]) => setFormData({ ...formData, domain_boost_factor: v })}
                      min={0.1}
                      max={5}
                      step={0.1}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Content Type Preferences */}
              <Card className="bg-muted/30 border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">Content Type Preferences</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-sm text-muted-foreground">Preferred Types (one per line)</Label>
                    <Textarea
                      placeholder={"documentation\ntutorial\napi"}
                      value={formData.preferred_types}
                      onChange={(e) => setFormData({ ...formData, preferred_types: e.target.value })}
                      className="mt-1 font-mono text-sm min-h-[80px]"
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-2">
                      <span>Type Boost Factor</span>
                      <span className="font-mono text-muted-foreground">{formData.type_boost_factor}x</span>
                    </div>
                    <Slider
                      value={[formData.type_boost_factor]}
                      onValueChange={([v]) => setFormData({ ...formData, type_boost_factor: v })}
                      min={0.1}
                      max={5}
                      step={0.1}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSubmit} data-testid="save-ranking-btn">
                {editingConfig ? 'Save Changes' : 'Create Configuration'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation */}
        <AlertDialog open={!!deleteConfigId} onOpenChange={() => setDeleteConfigId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Ranking Configuration?</AlertDialogTitle>
              <AlertDialogDescription>
                This will remove this ranking configuration. Search results will use the default ranking.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                Delete Configuration
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </DashboardLayout>
  );
};

export default SearchRanking;
