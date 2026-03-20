import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { Bot, Plus, Trash2, Edit2, Globe, Shield, Zap } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CAPABILITY_OPTIONS = [
  'search',
  'summarize',
  'translate',
  'analyze',
  'extract',
  'generate',
  'classify',
  'compare'
];

const Agents = () => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState(null);
  const [deleteAgentId, setDeleteAgentId] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    capabilities: [],
    endpoint_url: '',
    auth_type: 'api_key'
  });

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await fetch(`${API}/agents`, { credentials: 'include' });
      if (response.ok) {
        setAgents(await response.json());
      }
    } catch (error) {
      console.error('Error fetching agents:', error);
      toast.error('Failed to load agents');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (agent = null) => {
    if (agent) {
      setEditingAgent(agent);
      setFormData({
        name: agent.name,
        description: agent.description || '',
        capabilities: agent.capabilities || [],
        endpoint_url: agent.endpoint_url || '',
        auth_type: agent.auth_type || 'api_key'
      });
    } else {
      setEditingAgent(null);
      setFormData({
        name: '',
        description: '',
        capabilities: [],
        endpoint_url: '',
        auth_type: 'api_key'
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.name.trim()) {
      toast.error('Please enter an agent name');
      return;
    }

    try {
      const url = editingAgent 
        ? `${API}/agents/${editingAgent.agent_id}`
        : `${API}/agents`;
      
      const response = await fetch(url, {
        method: editingAgent ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        fetchAgents();
        setDialogOpen(false);
        toast.success(editingAgent ? 'Agent updated' : 'Agent registered');
      } else {
        toast.error('Failed to save agent');
      }
    } catch (error) {
      console.error('Error saving agent:', error);
      toast.error('Failed to save agent');
    }
  };

  const handleDelete = async () => {
    if (!deleteAgentId) return;

    try {
      const response = await fetch(`${API}/agents/${deleteAgentId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        setAgents(agents.filter(a => a.agent_id !== deleteAgentId));
        toast.success('Agent deleted');
      } else {
        toast.error('Failed to delete agent');
      }
    } catch (error) {
      console.error('Error deleting agent:', error);
      toast.error('Failed to delete agent');
    } finally {
      setDeleteAgentId(null);
    }
  };

  const toggleCapability = (cap) => {
    setFormData(prev => ({
      ...prev,
      capabilities: prev.capabilities.includes(cap)
        ? prev.capabilities.filter(c => c !== cap)
        : [...prev.capabilities, cap]
    }));
  };

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="agents-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Agent Registry</h1>
            <p className="text-muted-foreground mt-1">
              Register and manage your AI agents with their capabilities.
            </p>
          </div>
          <Button onClick={() => handleOpenDialog()} data-testid="register-agent-btn">
            <Plus className="w-4 h-4 mr-2" />
            Register Agent
          </Button>
        </div>

        {/* Agents Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {loading ? (
            <div className="col-span-full flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : agents.length === 0 ? (
            <div className="col-span-full">
              <Card className="bg-card/50 border-border/50">
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <div className="w-16 h-16 rounded-xl bg-muted flex items-center justify-center mb-4">
                    <Bot className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <p className="text-muted-foreground text-center">No agents registered yet</p>
                  <p className="text-sm text-muted-foreground mt-1 text-center">
                    Register your first agent to start using the API.
                  </p>
                  <Button className="mt-4" onClick={() => handleOpenDialog()}>
                    <Plus className="w-4 h-4 mr-2" />
                    Register Agent
                  </Button>
                </CardContent>
              </Card>
            </div>
          ) : (
            agents.map((agent) => (
              <Card 
                key={agent.agent_id} 
                className="bg-card/50 border-border/50 hover:border-primary/30 transition-colors"
                data-testid={`agent-card-${agent.agent_id}`}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Bot className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-base">{agent.name}</CardTitle>
                        <Badge 
                          variant={agent.is_active ? 'default' : 'secondary'} 
                          className="mt-1 text-xs"
                        >
                          {agent.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        onClick={() => handleOpenDialog(agent)}
                        data-testid={`edit-agent-${agent.agent_id}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteAgentId(agent.agent_id)}
                        data-testid={`delete-agent-${agent.agent_id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {agent.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {agent.description}
                    </p>
                  )}
                  
                  {agent.capabilities?.length > 0 && (
                    <div>
                      <p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">
                        Capabilities
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {agent.capabilities.map((cap) => (
                          <Badge key={cap} variant="outline" className="text-xs">
                            {cap}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/50">
                    {agent.endpoint_url && (
                      <span className="flex items-center gap-1">
                        <Globe className="w-3 h-3" />
                        Endpoint configured
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Shield className="w-3 h-3" />
                      {agent.auth_type}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        {/* Create/Edit Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editingAgent ? 'Edit Agent' : 'Register Agent'}</DialogTitle>
              <DialogDescription>
                {editingAgent 
                  ? 'Update your agent configuration.'
                  : 'Register a new agent with its capabilities and endpoint.'}
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="name" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Agent Name
                </Label>
                <Input
                  id="name"
                  placeholder="e.g., Research Assistant"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="mt-2"
                  data-testid="agent-name-input"
                />
              </div>

              <div>
                <Label htmlFor="description" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Description
                </Label>
                <Textarea
                  id="description"
                  placeholder="What does this agent do?"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="mt-2 min-h-[80px]"
                  data-testid="agent-description-input"
                />
              </div>

              <div>
                <Label className="text-sm uppercase tracking-wider text-muted-foreground">
                  Capabilities
                </Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {CAPABILITY_OPTIONS.map((cap) => (
                    <Badge
                      key={cap}
                      variant={formData.capabilities.includes(cap) ? 'default' : 'outline'}
                      className="cursor-pointer"
                      onClick={() => toggleCapability(cap)}
                    >
                      {cap}
                    </Badge>
                  ))}
                </div>
              </div>

              <div>
                <Label htmlFor="endpoint" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Endpoint URL (Optional)
                </Label>
                <Input
                  id="endpoint"
                  type="url"
                  placeholder="https://api.youragent.com/webhook"
                  value={formData.endpoint_url}
                  onChange={(e) => setFormData({ ...formData, endpoint_url: e.target.value })}
                  className="mt-2"
                  data-testid="agent-endpoint-input"
                />
              </div>

              <div>
                <Label htmlFor="authType" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Auth Type
                </Label>
                <Select 
                  value={formData.auth_type} 
                  onValueChange={(value) => setFormData({ ...formData, auth_type: value })}
                >
                  <SelectTrigger className="mt-2" data-testid="agent-auth-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="api_key">API Key</SelectItem>
                    <SelectItem value="bearer_token">Bearer Token</SelectItem>
                    <SelectItem value="oauth2">OAuth 2.0</SelectItem>
                    <SelectItem value="none">None</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSubmit} data-testid="save-agent-btn">
                {editingAgent ? 'Save Changes' : 'Register Agent'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation */}
        <AlertDialog open={!!deleteAgentId} onOpenChange={() => setDeleteAgentId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Agent?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. The agent will be removed from your registry.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                Delete Agent
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </DashboardLayout>
  );
};

export default Agents;
