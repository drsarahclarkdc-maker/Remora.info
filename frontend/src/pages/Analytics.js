import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  BarChart3,
  TrendingUp,
  Clock,
  Activity,
  Zap
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Analytics = () => {
  const [stats, setStats] = useState(null);
  const [recentUsage, setRecentUsage] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, recentRes] = await Promise.all([
          fetch(`${API}/usage/stats`, { credentials: 'include' }),
          fetch(`${API}/usage/recent?limit=50`, { credentials: 'include' })
        ]);

        if (statsRes.ok) setStats(await statsRes.json());
        if (recentRes.ok) setRecentUsage(await recentRes.json());
      } catch (error) {
        console.error('Error fetching analytics:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Group recent usage by endpoint
  const endpointStats = recentUsage.reduce((acc, record) => {
    const endpoint = record.endpoint.replace('/api/', '');
    acc[endpoint] = (acc[endpoint] || 0) + 1;
    return acc;
  }, {});

  const endpointChartData = Object.entries(endpointStats).map(([name, value]) => ({
    name,
    value
  }));

  const COLORS = ['hsl(217, 91%, 60%)', 'hsl(160, 60%, 45%)', 'hsl(30, 80%, 55%)', 'hsl(280, 65%, 60%)'];

  // Response time distribution
  const responseTimeRanges = {
    'Fast (<50ms)': 0,
    'Normal (50-200ms)': 0,
    'Slow (>200ms)': 0
  };

  recentUsage.forEach(record => {
    const time = record.response_time_ms;
    if (time < 50) responseTimeRanges['Fast (<50ms)']++;
    else if (time <= 200) responseTimeRanges['Normal (50-200ms)']++;
    else responseTimeRanges['Slow (>200ms)']++;
  });

  const responseTimeData = Object.entries(responseTimeRanges).map(([name, value]) => ({
    name,
    value
  }));

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
      <div className="space-y-8" data-testid="analytics-page">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground mt-1">
            Monitor your API usage and performance metrics.
          </p>
        </div>

        {/* Plan Status Card */}
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="p-6">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold">Free Plan</h3>
                  <Badge className="bg-primary text-primary-foreground">Active</Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Unlimited requests • Full API access • We're just tracking usage
                </p>
              </div>
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Zap className="w-6 h-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">Today</p>
                  <p className="text-3xl font-bold mt-1">{stats?.today || 0}</p>
                </div>
                <Activity className="w-8 h-8 text-primary/50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">This Week</p>
                  <p className="text-3xl font-bold mt-1">{stats?.this_week || 0}</p>
                </div>
                <TrendingUp className="w-8 h-8 text-primary/50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground uppercase tracking-wider">This Month</p>
                  <p className="text-3xl font-bold mt-1">{stats?.this_month || 0}</p>
                </div>
                <BarChart3 className="w-8 h-8 text-primary/50" />
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
                <Clock className="w-8 h-8 text-primary/50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Usage Trend */}
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">7-Day Usage Trend</CardTitle>
              <CardDescription>API requests over the last week</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
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
                      labelFormatter={(value) => new Date(value).toLocaleDateString('en-US', { 
                        weekday: 'long', 
                        month: 'short', 
                        day: 'numeric' 
                      })}
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

          {/* Endpoint Distribution */}
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Endpoint Distribution</CardTitle>
              <CardDescription>Requests by endpoint</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                {endpointChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={endpointChartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {endpointChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{
                          backgroundColor: 'hsl(0, 0%, 4%)',
                          border: '1px solid hsl(240, 4%, 16%)',
                          borderRadius: '8px',
                          fontSize: '12px'
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    No data available
                  </div>
                )}
              </div>
              {endpointChartData.length > 0 && (
                <div className="flex flex-wrap justify-center gap-4 mt-4">
                  {endpointChartData.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-2 text-sm">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <span className="text-muted-foreground">{entry.name}</span>
                      <span className="font-medium">{entry.value}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Response Time Distribution */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-lg">Response Time Distribution</CardTitle>
            <CardDescription>Performance breakdown of recent requests</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={responseTimeData} layout="vertical">
                  <XAxis type="number" stroke="hsl(240, 5%, 65%)" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis dataKey="name" type="category" stroke="hsl(240, 5%, 65%)" fontSize={12} tickLine={false} axisLine={false} width={120} />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: 'hsl(0, 0%, 4%)',
                      border: '1px solid hsl(240, 4%, 16%)',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                  />
                  <Bar dataKey="value" fill="hsl(217, 91%, 60%)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-lg">Recent Activity</CardTitle>
            <CardDescription>Latest API requests</CardDescription>
          </CardHeader>
          <CardContent>
            {recentUsage.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No recent activity
              </div>
            ) : (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {recentUsage.slice(0, 20).map((record, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/30 text-sm"
                  >
                    <div className="flex items-center gap-3">
                      <Badge variant={record.status_code < 400 ? 'default' : 'destructive'} className="text-xs">
                        {record.status_code}
                      </Badge>
                      <span className="font-mono text-muted-foreground">{record.method}</span>
                      <span className="font-mono">{record.endpoint}</span>
                    </div>
                    <div className="flex items-center gap-4 text-muted-foreground">
                      <span>{record.response_time_ms}ms</span>
                      <span className="text-xs">
                        {new Date(record.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
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

export default Analytics;
