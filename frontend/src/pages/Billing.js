import { useState, useEffect, useCallback } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import {
  CreditCard,
  Zap,
  TrendingUp,
  Check,
  AlertTriangle,
  ArrowRight,
  Clock,
  Search,
  Globe,
  FileText,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PLAN_FEATURES = {
  free: ['3,000 credits/month', 'Basic search', 'Single URL crawl', 'Community support'],
  starter: ['10,000 credits/month', 'Bulk crawl (100 URLs)', 'Scheduled crawling', 'Webhook deliveries', 'Email support'],
  growth: ['40,000 credits/month', 'Everything in Starter', 'Custom crawl rules', 'Search ranking configs', 'Priority support'],
  scale: ['200,000 credits/month', 'Everything in Growth', 'Organization & teams', 'Dedicated support', 'SLA guarantee'],
};

const OPERATION_ICONS = {
  search: Search,
  crawl: Globe,
  content_extract: FileText,
};

const Billing = () => {
  const [usage, setUsage] = useState(null);
  const [plans, setPlans] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(null);

  const fetchUsage = useCallback(async () => {
    try {
      const res = await fetch(`${API}/billing/usage`, { credentials: 'include' });
      if (res.ok) setUsage(await res.json());
    } catch (e) {
      console.error('Error fetching usage:', e);
    }
  }, []);

  const fetchPlans = useCallback(async () => {
    try {
      const res = await fetch(`${API}/billing/plans`);
      if (res.ok) setPlans(await res.json());
    } catch (e) {
      console.error('Error fetching plans:', e);
    }
  }, []);

  const fetchTransactions = useCallback(async () => {
    try {
      const res = await fetch(`${API}/billing/transactions`, { credentials: 'include' });
      if (res.ok) setTransactions(await res.json());
    } catch (e) {
      console.error('Error fetching transactions:', e);
    }
  }, []);

  useEffect(() => {
    Promise.all([fetchUsage(), fetchPlans(), fetchTransactions()]).finally(() => setLoading(false));
  }, [fetchUsage, fetchPlans, fetchTransactions]);

  // Poll for payment status if returning from Stripe
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    if (!sessionId) return;

    let attempts = 0;
    const maxAttempts = 8;

    const poll = async () => {
      try {
        const res = await fetch(`${API}/billing/checkout/status/${sessionId}`, { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();

        if (data.payment_status === 'paid') {
          toast.success('Payment successful! Your plan has been upgraded.');
          window.history.replaceState({}, '', '/billing');
          fetchUsage();
          fetchTransactions();
          return;
        }
        if (data.status === 'expired') {
          toast.error('Payment session expired. Please try again.');
          window.history.replaceState({}, '', '/billing');
          return;
        }
        attempts++;
        if (attempts < maxAttempts) setTimeout(poll, 2000);
      } catch {
        attempts++;
        if (attempts < maxAttempts) setTimeout(poll, 2000);
      }
    };

    toast.info('Checking payment status...');
    poll();
  }, [fetchUsage, fetchTransactions]);

  const handleCheckout = async (planId) => {
    setCheckoutLoading(planId);
    try {
      const res = await fetch(`${API}/billing/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          plan_id: planId,
          origin_url: window.location.origin,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.url) window.location.href = data.url;
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to start checkout');
      }
    } catch {
      toast.error('Failed to start checkout');
    } finally {
      setCheckoutLoading(null);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </DashboardLayout>
    );
  }

  const currentPlan = usage?.plan || 'free';

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="billing-page">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
          <p className="text-muted-foreground mt-1">Manage your plan, credits, and payment history.</p>
        </div>

        {/* Usage Alert */}
        {usage?.alert && (
          <Card className="border-yellow-500/30 bg-yellow-500/5">
            <CardContent className="flex items-center gap-3 py-4">
              <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0" />
              <p className="text-sm">
                You've used <strong>{usage.usage_percentage}%</strong> of your monthly credits.
                {currentPlan === 'free' ? ' Upgrade to get more.' : ' Consider upgrading your plan.'}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Current Usage */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <CreditCard className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Current Plan</p>
                  <p className="font-semibold text-lg" data-testid="current-plan">{usage?.plan_name || 'Free'}</p>
                </div>
              </div>
              {usage?.plan_price > 0 && (
                <p className="text-sm text-muted-foreground">${usage.plan_price}/month</p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-emerald-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Credits Remaining</p>
                  <p className="font-semibold text-lg" data-testid="credits-remaining">
                    {(usage?.credits_remaining || 0).toLocaleString()}
                  </p>
                </div>
              </div>
              <Progress
                value={100 - (usage?.usage_percentage || 0)}
                className="h-2"
              />
              <p className="text-xs text-muted-foreground mt-2">
                {(usage?.credits_used || 0).toLocaleString()} / {(usage?.credits_total || 0).toLocaleString()} used
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Billing Period</p>
                  <p className="font-semibold text-sm" data-testid="billing-period">
                    {usage?.period_end
                      ? `Resets ${new Date(usage.period_end).toLocaleDateString()}`
                      : 'N/A'}
                  </p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Credits reset at the start of each billing cycle</p>
            </CardContent>
          </Card>
        </div>

        {/* Plans */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Plans</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {plans.map((plan) => {
              const isCurrent = plan.plan_id === currentPlan;
              const isPopular = plan.plan_id === 'growth';
              const features = PLAN_FEATURES[plan.plan_id] || [];

              return (
                <Card
                  key={plan.plan_id}
                  className={`relative bg-card/50 border-border/50 ${
                    isPopular ? 'ring-1 ring-primary/40' : ''
                  } ${isCurrent ? 'ring-1 ring-emerald-500/40' : ''}`}
                  data-testid={`plan-card-${plan.plan_id}`}
                >
                  {isPopular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <Badge className="bg-primary text-primary-foreground text-xs">Popular</Badge>
                    </div>
                  )}
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">{plan.name}</CardTitle>
                    <CardDescription>
                      {plan.price === 0 ? (
                        <span className="text-2xl font-bold text-foreground">Free</span>
                      ) : (
                        <>
                          <span className="text-2xl font-bold text-foreground">${plan.price}</span>
                          <span className="text-muted-foreground">/mo</span>
                        </>
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <ul className="space-y-2">
                      {features.map((f, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <Check className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                          <span className="text-muted-foreground">{f}</span>
                        </li>
                      ))}
                    </ul>
                    {isCurrent ? (
                      <Button variant="outline" className="w-full" disabled data-testid={`plan-btn-${plan.plan_id}`}>
                        Current Plan
                      </Button>
                    ) : plan.plan_id === 'free' ? (
                      <Button variant="outline" className="w-full" disabled>
                        Included
                      </Button>
                    ) : (
                      <Button
                        className="w-full"
                        onClick={() => handleCheckout(plan.plan_id)}
                        disabled={!!checkoutLoading}
                        data-testid={`plan-btn-${plan.plan_id}`}
                      >
                        {checkoutLoading === plan.plan_id ? (
                          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                        ) : (
                          <ArrowRight className="w-4 h-4 mr-2" />
                        )}
                        {currentPlan === 'free' ? 'Get Started' : 'Upgrade'}
                      </Button>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Credit Costs */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-lg">Credit Costs</CardTitle>
            <CardDescription>How credits are consumed per operation</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { op: 'search', label: 'Search Query', cost: 1, icon: Search },
                { op: 'crawl', label: 'URL Crawl', cost: 1, icon: Globe },
                { op: 'content_extract', label: 'Content Extract', cost: 1, icon: FileText },
                { op: 'bulk_crawl', label: 'Bulk Crawl (per URL)', cost: 1, icon: TrendingUp },
              ].map(({ op, label, cost, icon: Icon }) => (
                <div key={op} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30">
                  <Icon className="w-4 h-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{label}</p>
                    <p className="text-xs text-muted-foreground">{cost} credit</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Usage */}
        {usage?.recent_usage?.length > 0 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Recent Credit Usage</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {usage.recent_usage.slice(0, 10).map((item, i) => {
                  const Icon = OPERATION_ICONS[item.operation] || Zap;
                  return (
                    <div key={i} className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/30">
                      <div className="flex items-center gap-3">
                        <Icon className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm capitalize">{item.operation.replace('_', ' ')}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <Badge variant="outline" className="text-xs">-{item.credits}</Badge>
                        <span className="text-xs text-muted-foreground w-32 text-right">
                          {new Date(item.timestamp).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Payment History */}
        {transactions.length > 0 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Payment History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {transactions.map((txn, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                    <div>
                      <p className="text-sm font-medium capitalize">{txn.plan_id} Plan</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(txn.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-mono">${txn.amount}</span>
                      <Badge
                        variant={txn.payment_status === 'paid' ? 'default' : 'secondary'}
                        className={`text-xs ${
                          txn.payment_status === 'paid'
                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                            : ''
                        }`}
                      >
                        {txn.payment_status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
};

export default Billing;
