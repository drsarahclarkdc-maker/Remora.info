import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Send,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  RefreshCw,
  Webhook,
  ArrowRight
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const WebhookDeliveries = () => {
  const [deliveries, setDeliveries] = useState([]);
  const [stats, setStats] = useState(null);
  const [webhooks, setWebhooks] = useState([]);
  const [selectedWebhook, setSelectedWebhook] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [selectedWebhook]);

  const fetchData = async () => {
    try {
      const [deliveriesRes, statsRes, webhooksRes] = await Promise.all([
        selectedWebhook === 'all' 
          ? fetch(`${API}/webhooks/deliveries?limit=50`, { credentials: 'include' })
          : fetch(`${API}/webhooks/${selectedWebhook}/deliveries?limit=50`, { credentials: 'include' }),
        fetch(`${API}/webhooks/deliveries/stats`, { credentials: 'include' }),
        fetch(`${API}/webhooks`, { credentials: 'include' })
      ]);

      if (deliveriesRes.ok) setDeliveries(await deliveriesRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
      if (webhooksRes.ok) setWebhooks(await webhooksRes.json());
    } catch (error) {
      console.error('Error fetching deliveries:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-destructive" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'retrying':
        return <AlertCircle className="w-4 h-4 text-orange-500" />;
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'success':
        return <Badge className="bg-green-500/10 text-green-500 border-green-500/20">Success</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">Pending</Badge>;
      case 'retrying':
        return <Badge className="bg-orange-500/10 text-orange-500 border-orange-500/20">Retrying</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="webhook-deliveries-page">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Webhook Deliveries</h1>
            <p className="text-muted-foreground mt-1">
              Monitor webhook delivery status and troubleshoot failures.
            </p>
          </div>
          <Button variant="outline" onClick={fetchData} data-testid="refresh-deliveries-btn">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">Total</p>
                  <p className="text-3xl font-bold mt-1">{stats?.total || 0}</p>
                </div>
                <Send className="w-8 h-8 text-primary/50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">Success</p>
                  <p className="text-3xl font-bold mt-1 text-green-500">{stats?.success || 0}</p>
                </div>
                <CheckCircle2 className="w-8 h-8 text-green-500/50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">Failed</p>
                  <p className="text-3xl font-bold mt-1 text-destructive">{stats?.failed || 0}</p>
                </div>
                <XCircle className="w-8 h-8 text-destructive/50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">Pending</p>
                  <p className="text-3xl font-bold mt-1 text-yellow-500">{stats?.pending || 0}</p>
                </div>
                <Clock className="w-8 h-8 text-yellow-500/50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">Success Rate</p>
                  <p className="text-3xl font-bold mt-1">{stats?.success_rate || 0}%</p>
                </div>
                <Webhook className="w-8 h-8 text-primary/50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filter by Webhook */}
        {webhooks.length > 0 && (
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">Filter by webhook:</span>
            <Tabs value={selectedWebhook} onValueChange={setSelectedWebhook}>
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                {webhooks.map((webhook) => (
                  <TabsTrigger key={webhook.webhook_id} value={webhook.webhook_id}>
                    {webhook.name}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>
        )}

        {/* Deliveries List */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-lg">Delivery Log</CardTitle>
            <CardDescription>Recent webhook delivery attempts</CardDescription>
          </CardHeader>
          <CardContent>
            {deliveries.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Send className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No webhook deliveries yet</p>
                <p className="text-sm mt-1">Deliveries will appear here when webhooks are triggered.</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {deliveries.map((delivery) => (
                  <div
                    key={delivery.delivery_id}
                    className="p-4 rounded-lg bg-muted/30 border border-border/50"
                    data-testid={`delivery-${delivery.delivery_id}`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 min-w-0 flex-1">
                        {getStatusIcon(delivery.status)}
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="outline" className="font-mono text-xs">
                              {delivery.event}
                            </Badge>
                            {getStatusBadge(delivery.status)}
                            {delivery.status_code && (
                              <span className="text-xs text-muted-foreground">
                                HTTP {delivery.status_code}
                              </span>
                            )}
                          </div>
                          <code className="text-xs text-muted-foreground font-mono mt-2 block truncate">
                            {delivery.url}
                          </code>
                          {delivery.error_message && (
                            <p className="text-xs text-destructive mt-2">
                              {delivery.error_message}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <span className="text-xs text-muted-foreground block">
                          {formatDate(delivery.created_at)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          Attempts: {delivery.attempts}
                        </span>
                      </div>
                    </div>
                    
                    {/* Payload Preview */}
                    <details className="mt-3">
                      <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                        View payload
                      </summary>
                      <pre className="mt-2 p-3 bg-muted/50 rounded text-xs overflow-x-auto">
                        <code>{JSON.stringify(delivery.payload, null, 2)}</code>
                      </pre>
                    </details>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default WebhookDeliveries;
