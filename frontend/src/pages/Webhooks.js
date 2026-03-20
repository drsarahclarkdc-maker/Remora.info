import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
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
import { Webhook, Plus, Trash2, Edit2, Link, Bell, Copy } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const EVENT_OPTIONS = [
  { value: 'search.complete', label: 'Search Complete' },
  { value: 'content.updated', label: 'Content Updated' },
  { value: 'content.new', label: 'New Content' },
  { value: 'agent.registered', label: 'Agent Registered' },
  { value: 'rate_limit.warning', label: 'Rate Limit Warning' }
];

const Webhooks = () => {
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState(null);
  const [deleteWebhookId, setDeleteWebhookId] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    events: []
  });

  useEffect(() => {
    fetchWebhooks();
  }, []);

  const fetchWebhooks = async () => {
    try {
      const response = await fetch(`${API}/webhooks`, { credentials: 'include' });
      if (response.ok) {
        setWebhooks(await response.json());
      }
    } catch (error) {
      console.error('Error fetching webhooks:', error);
      toast.error('Failed to load webhooks');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (webhook = null) => {
    if (webhook) {
      setEditingWebhook(webhook);
      setFormData({
        name: webhook.name,
        url: webhook.url,
        events: webhook.events || []
      });
    } else {
      setEditingWebhook(null);
      setFormData({
        name: '',
        url: '',
        events: []
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formData.name.trim() || !formData.url.trim()) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      const url = editingWebhook 
        ? `${API}/webhooks/${editingWebhook.webhook_id}`
        : `${API}/webhooks`;
      
      const response = await fetch(url, {
        method: editingWebhook ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        fetchWebhooks();
        setDialogOpen(false);
        toast.success(editingWebhook ? 'Webhook updated' : 'Webhook created');
      } else {
        toast.error('Failed to save webhook');
      }
    } catch (error) {
      console.error('Error saving webhook:', error);
      toast.error('Failed to save webhook');
    }
  };

  const handleDelete = async () => {
    if (!deleteWebhookId) return;

    try {
      const response = await fetch(`${API}/webhooks/${deleteWebhookId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        setWebhooks(webhooks.filter(w => w.webhook_id !== deleteWebhookId));
        toast.success('Webhook deleted');
      } else {
        toast.error('Failed to delete webhook');
      }
    } catch (error) {
      console.error('Error deleting webhook:', error);
      toast.error('Failed to delete webhook');
    } finally {
      setDeleteWebhookId(null);
    }
  };

  const toggleEvent = (event) => {
    setFormData(prev => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter(e => e !== event)
        : [...prev.events, event]
    }));
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="webhooks-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Webhooks</h1>
            <p className="text-muted-foreground mt-1">
              Subscribe to events and receive real-time notifications.
            </p>
          </div>
          <Button onClick={() => handleOpenDialog()} data-testid="create-webhook-btn">
            <Plus className="w-4 h-4 mr-2" />
            Add Webhook
          </Button>
        </div>

        {/* Webhooks List */}
        <div className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : webhooks.length === 0 ? (
            <Card className="bg-card/50 border-border/50">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="w-16 h-16 rounded-xl bg-muted flex items-center justify-center mb-4">
                  <Webhook className="w-8 h-8 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-center">No webhooks configured</p>
                <p className="text-sm text-muted-foreground mt-1 text-center">
                  Add a webhook to receive event notifications.
                </p>
                <Button className="mt-4" onClick={() => handleOpenDialog()}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Webhook
                </Button>
              </CardContent>
            </Card>
          ) : (
            webhooks.map((webhook) => (
              <Card 
                key={webhook.webhook_id} 
                className="bg-card/50 border-border/50"
                data-testid={`webhook-card-${webhook.webhook_id}`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4 min-w-0 flex-1">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Webhook className="w-5 h-5 text-primary" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">{webhook.name}</h3>
                          <Badge 
                            variant={webhook.is_active ? 'default' : 'secondary'}
                            className="text-xs"
                          >
                            {webhook.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                        
                        <div className="flex items-center gap-2 mt-2">
                          <Link className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                          <code className="text-xs text-muted-foreground font-mono truncate">
                            {webhook.url}
                          </code>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-6 w-6"
                            onClick={() => copyToClipboard(webhook.url)}
                          >
                            <Copy className="w-3 h-3" />
                          </Button>
                        </div>

                        {webhook.events?.length > 0 && (
                          <div className="flex flex-wrap gap-2 mt-3">
                            {webhook.events.map((event) => (
                              <Badge key={event} variant="outline" className="text-xs">
                                <Bell className="w-3 h-3 mr-1" />
                                {EVENT_OPTIONS.find(e => e.value === event)?.label || event}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex gap-1 flex-shrink-0">
                      <Button 
                        variant="ghost" 
                        size="icon"
                        onClick={() => handleOpenDialog(webhook)}
                        data-testid={`edit-webhook-${webhook.webhook_id}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteWebhookId(webhook.webhook_id)}
                        data-testid={`delete-webhook-${webhook.webhook_id}`}
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
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editingWebhook ? 'Edit Webhook' : 'Add Webhook'}</DialogTitle>
              <DialogDescription>
                {editingWebhook 
                  ? 'Update your webhook configuration.'
                  : 'Configure a webhook to receive event notifications.'}
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="name" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Webhook Name
                </Label>
                <Input
                  id="name"
                  placeholder="e.g., Production Notifications"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="mt-2"
                  data-testid="webhook-name-input"
                />
              </div>

              <div>
                <Label htmlFor="url" className="text-sm uppercase tracking-wider text-muted-foreground">
                  Endpoint URL
                </Label>
                <Input
                  id="url"
                  type="url"
                  placeholder="https://your-server.com/webhook"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  className="mt-2"
                  data-testid="webhook-url-input"
                />
              </div>

              <div>
                <Label className="text-sm uppercase tracking-wider text-muted-foreground">
                  Events
                </Label>
                <p className="text-xs text-muted-foreground mt-1 mb-3">
                  Select which events should trigger this webhook.
                </p>
                <div className="space-y-2">
                  {EVENT_OPTIONS.map((event) => (
                    <div
                      key={event.value}
                      className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/50 cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => toggleEvent(event.value)}
                    >
                      <div className="flex items-center gap-2">
                        <Bell className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm">{event.label}</span>
                      </div>
                      <Switch 
                        checked={formData.events.includes(event.value)}
                        onCheckedChange={() => toggleEvent(event.value)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSubmit} data-testid="save-webhook-btn">
                {editingWebhook ? 'Save Changes' : 'Create Webhook'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation */}
        <AlertDialog open={!!deleteWebhookId} onOpenChange={() => setDeleteWebhookId(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Webhook?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. You will stop receiving notifications for this webhook.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                Delete Webhook
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </DashboardLayout>
  );
};

export default Webhooks;
