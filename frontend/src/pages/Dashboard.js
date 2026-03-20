import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Key,
  Bot,
  Webhook,
  BarChart3,
  ArrowRight,
  Activity,
  Clock,
  TrendingUp,
  Search
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [keys, setKeys] = useState([]);
  const [agents, setAgents] = useState([]);
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, keysRes, agentsRes, webhooksRes] = await Promise.all([
          fetch(`${API}/usage/stats`, { credentials: 'include' }),
          fetch(`${API}/keys`, { credentials: 'include' }),
          fetch(`${API}/agents`, { credentials: 'include' }),
          fetch(`${API}/webhooks`, { credentials: 'include' })
        ]);

        if (statsRes.ok) setStats(await statsRes.json());
        if (keysRes.ok) setKeys(await keysRes.json());
        if (agentsRes.ok) setAgents(await agentsRes.json());
        if (webhooksRes.ok) setWebhooks(await webhooksRes.json());
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const quickActions = [
    { label: 'Create API Key', href: '/keys', icon: Key },
    { label: 'Register Agent', href: '/agents', icon: Bot },
    { label: 'Add Webhook', href: '/webhooks', icon: Webhook },
    { label: 'Test Search', href: '/search', icon: Search }
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="dashboard-page">
        {/* Welcome Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Welcome back, {user?.name?.split(' ')[0]}
            </h1>
            <p className="text-muted-foreground mt-1">
              Here's what's happening with your API usage.
            </p>
          </div>
          <Badge variant="outline" className="w-fit px-4 py-1.5 text-xs font-mono uppercase tracking-wider bg-primary/10 text-primary border-primary/30">
            Free Plan
          </Badge>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">Today's Requests</p>
                  <p className="text-3xl font-bold mt-1">{stats?.today || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Activity className="w-6 h-6 text-primary" />
                </div>
              </div>
              {stats?.rate_limit && (
                <p className="text-xs text-muted-foreground mt-3">
                  Free plan • Unlimited
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">This Week</p>
                  <p className="text-3xl font-bold mt-1">{stats?.this_week || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">Avg Response</p>
                  <p className="text-3xl font-bold mt-1">{stats?.avg_response_time_ms || 0}ms</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Clock className="w-6 h-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">Total Requests</p>
                  <p className="text-3xl font-bold mt-1">{stats?.total || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Chart & Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Usage Chart */}
          <Card className="lg:col-span-2 bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Usage Trend</CardTitle>
              <CardDescription>API requests over the last 7 days</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={stats?.daily_breakdown || []}>
                    <defs>
                      <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(217, 91%, 60%)" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="hsl(217, 91%, 60%)" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis 
                      dataKey="date" 
                      stroke="hsl(240, 5%, 65%)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { weekday: 'short' })}
                    />
                    <YAxis 
                      stroke="hsl(240, 5%, 65%)"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip 
                      contentStyle={{
                        backgroundColor: 'hsl(0, 0%, 4%)',
                        border: '1px solid hsl(240, 4%, 16%)',
                        borderRadius: '8px',
                        fontSize: '12px'
                      }}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="requests" 
                      stroke="hsl(217, 91%, 60%)" 
                      fillOpacity={1} 
                      fill="url(#colorRequests)" 
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Quick Actions</CardTitle>
              <CardDescription>Common tasks to get started</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {quickActions.map((action) => {
                const Icon = action.icon;
                return (
                  <Button
                    key={action.href}
                    variant="outline"
                    className="w-full justify-between h-12"
                    onClick={() => navigate(action.href)}
                    data-testid={`quick-action-${action.label.toLowerCase().replace(' ', '-')}`}
                  >
                    <span className="flex items-center gap-2">
                      <Icon className="w-4 h-4" />
                      {action.label}
                    </span>
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                );
              })}
            </CardContent>
          </Card>
        </div>

        {/* Resources Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">API Keys</CardTitle>
                <Key className="w-4 h-4 text-muted-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{keys.length}</p>
              <p className="text-sm text-muted-foreground mt-1">Active keys</p>
              <Button 
                variant="link" 
                className="p-0 h-auto mt-3 text-primary"
                onClick={() => navigate('/keys')}
              >
                Manage keys <ArrowRight className="w-3 h-3 ml-1" />
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Registered Agents</CardTitle>
                <Bot className="w-4 h-4 text-muted-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{agents.length}</p>
              <p className="text-sm text-muted-foreground mt-1">Active agents</p>
              <Button 
                variant="link" 
                className="p-0 h-auto mt-3 text-primary"
                onClick={() => navigate('/agents')}
              >
                View agents <ArrowRight className="w-3 h-3 ml-1" />
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Webhooks</CardTitle>
                <Webhook className="w-4 h-4 text-muted-foreground" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{webhooks.length}</p>
              <p className="text-sm text-muted-foreground mt-1">Subscriptions</p>
              <Button 
                variant="link" 
                className="p-0 h-auto mt-3 text-primary"
                onClick={() => navigate('/webhooks')}
              >
                Manage webhooks <ArrowRight className="w-3 h-3 ml-1" />
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
