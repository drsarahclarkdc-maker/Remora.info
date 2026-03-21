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
  ArrowDown,
  Clock,
  Search,
  Globe,
  FileText,
  XCircle,
  RefreshCw,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PLAN_FEATURES = {
  free: ['1,000 credits/month', 'Basic search', 'Single URL crawl', 'Community support'],
  starter: ['10,000 credits/month', 'Bulk crawl (100 URLs)', 'Scheduled crawling', 'Webhook deliveries', 'Email support'],
  growth: ['40,000 credits/month', 'Everything in Starter', 'Custom crawl rules', 'Search ranking configs', 'Priority support'],
  scale: ['200,000 credits/month', 'Everything in Growth', 'Organization & teams', 'Dedicated support', 'SLA guarantee'],
  enterprise: ['Custom credit volume', 'Everything in Scale', 'Dedicated API endpoints', 'Private deployment', 'Custom SLAs', '24/7 support'],
};

const PLAN_ORDER = ['free', 'starter', 'growth', 'scale', 'enterprise'];

const Billing = () => {
  const [usage, setUsage] = useState(null);
  const [plans, setPlans] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [billingSettings, setBillingSettings] = useState(null);
  const [rechargePacks, setRechargePacks] = useState([]);

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

  const fetchBillingSettings = useCallback(async () => {
    try {
      const res = await fetch(`${API}/billing/settings`, { credentials: 'include' });
      if (res.ok) setBillingSettings(await res.json());
    } catch (e) {
      console.error('Error fetching billing settings:', e);
    }
  }, []);

  const fetchRechargePacks = useCallback(async () => {
    try {
      const res = await fetch(`${API}/billing/recharge-packs`);
      if (res.ok) setRechargePacks(await res.json());
    } catch (e) {
      console.error('Error fetching recharge packs:', e);
    }
  }, []);

  useEffect(() => {
    Promise.all([fetchUsage(), fetchPlans(), fetchTransactions(), fetchBillingSettings(), fetchRechargePacks()]).finally(() => setLoading(false));
  }, [fetchUsage, fetchPlans, fetchTransactions, fetchBillingSettings, fetchRechargePacks]);

  // Poll for payment status if returning from Stripe
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    if (!sessionId) return;

    let attempts = 0;
    const maxAttempts = 10;

    const poll = async () => {
      try {
        const res = await fetch(`${API}/billing/checkout/status/${sessionId}`, { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();

        if (data.payment_status === 'paid') {
          toast.success('Payment successful! Your subscription is active.');
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

    toast.info('Verifying payment...');
    poll();
  }, [fetchUsage, fetchTransactions]);

  const handleSubscribe = async (planId) => {
    setActionLoading(planId);
    try {
      const res = await fetch(`${API}/billing/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ plan_id: planId, origin_url: window.location.origin }),
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
      setActionLoading(null);
    }
  };

  const handleChangePlan = async (planId) => {
    setActionLoading(planId);
    try {
      const res = await fetch(`${API}/billing/change-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ plan_id: planId }),
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        fetchUsage();
        fetchTransactions();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to change plan');
      }
    } catch {
      toast.error('Failed to change plan');
    } finally {
      setActionLoading(null);
    }
  };

  const handleCancel = async () => {
    setActionLoading('cancel');
    try {
      const res = await fetch(`${API}/billing/cancel`, {
        method: 'POST',
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        setCancelConfirm(false);
        fetchUsage();
        fetchTransactions();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to cancel subscription');
      }
    } catch {
      toast.error('Failed to cancel subscription');
    } finally {
      setActionLoading(null);
    }
  };

  const handleAutoRechargeToggle = async (enabled, packId) => {
    try {
      const res = await fetch(`${API}/billing/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ enabled, pack_id: packId || billingSettings?.recharge_pack_id || 'medium' }),
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.message);
        fetchBillingSettings();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to update settings');
      }
    } catch {
      toast.error('Failed to update settings');
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
  const hasSubscription = usage?.has_subscription || false;
  const currentPlanIdx = PLAN_ORDER.indexOf(currentPlan);

  const getPlanAction = (planId) => {
    if (planId === currentPlan) return 'current';
    if (planId === 'free') return hasSubscription ? 'cancel' : 'included';
    if (planId === 'enterprise') return 'contact';

    const targetIdx = PLAN_ORDER.indexOf(planId);
    if (hasSubscription) {
      return targetIdx > currentPlanIdx ? 'upgrade' : 'downgrade';
    }
    return 'subscribe';
  };

  return (
    <DashboardLayout>
      <div className="space-y-8" data-testid="billing-page">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
          <p className="text-muted-foreground mt-1">Manage your subscription, credits, and payment history.</p>
        </div>

        {usage?.alert && (
          <Card className="border-yellow-500/30 bg-yellow-500/5">
            <CardContent className="flex items-center gap-3 py-4">
              <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0" />
              <p className="text-sm">
                You've used <strong>{usage.usage_percentage}%</strong> of your monthly credits.
                {currentPlan === 'free' ? ' Subscribe to get more.' : ' Consider upgrading your plan.'}
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
              <div className="flex items-center gap-2">
                {usage?.plan_price > 0 && (
                  <p className="text-sm text-muted-foreground">${usage.plan_price}/month</p>
                )}
                {hasSubscription && (
                  <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                    Active Subscription
                  </Badge>
                )}
              </div>
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
              <Progress value={100 - (usage?.usage_percentage || 0)} className="h-2" />
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
              <p className="text-xs text-muted-foreground">
                {hasSubscription ? 'Auto-renews monthly via Stripe' : 'Credits reset at the start of each billing cycle'}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Plans */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Plans</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {plans.map((plan) => {
              const action = getPlanAction(plan.plan_id);
              const isCurrent = action === 'current';
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
                      ) : plan.price < 0 ? (
                        <span className="text-2xl font-bold text-foreground">Custom</span>
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
                    <PlanButton
                      action={action}
                      planId={plan.plan_id}
                      loading={actionLoading}
                      onSubscribe={handleSubscribe}
                      onChangePlan={handleChangePlan}
                      onCancelClick={() => setCancelConfirm(true)}
                    />
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Cancel Confirmation */}
        {cancelConfirm && (
          <Card className="border-red-500/30 bg-red-500/5">
            <CardContent className="py-5">
              <div className="flex items-start gap-3">
                <XCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-medium text-sm">Cancel your subscription?</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    You'll immediately revert to the Free plan with 1,000 credits/month. Any prorated credit will be applied to your Stripe balance.
                  </p>
                  <div className="flex gap-3 mt-4">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleCancel}
                      disabled={actionLoading === 'cancel'}
                      data-testid="confirm-cancel-btn"
                    >
                      {actionLoading === 'cancel' ? (
                        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
                      ) : null}
                      Yes, cancel subscription
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setCancelConfirm(false)}>
                      Keep my plan
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Auto-Recharge Settings */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <RefreshCw className="w-4 h-4" />
                  Auto-Recharge
                </CardTitle>
                <CardDescription>Automatically add credits when you run out</CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleAutoRechargeToggle(!billingSettings?.auto_recharge_enabled)}
                disabled={!billingSettings?.has_payment_method && !billingSettings?.auto_recharge_enabled}
                data-testid="auto-recharge-toggle"
              >
                {billingSettings?.auto_recharge_enabled ? (
                  <ToggleRight className="w-8 h-8 text-emerald-500" />
                ) : (
                  <ToggleLeft className="w-8 h-8 text-muted-foreground" />
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {!billingSettings?.has_payment_method ? (
              <p className="text-sm text-muted-foreground">Subscribe to a paid plan first to enable auto-recharge.</p>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  {billingSettings?.auto_recharge_enabled
                    ? 'When credits run out, your payment method will be charged automatically.'
                    : 'Enable to automatically purchase credits when your balance reaches zero.'}
                </p>
                {billingSettings?.auto_recharge_enabled && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" data-testid="recharge-pack-options">
                    {rechargePacks.map((pack) => {
                      const isSelected = pack.pack_id === (billingSettings?.recharge_pack_id || 'medium');
                      return (
                        <button
                          key={pack.pack_id}
                          onClick={() => handleAutoRechargeToggle(true, pack.pack_id)}
                          className={`p-3 rounded-lg border text-left transition-colors ${
                            isSelected
                              ? 'border-primary bg-primary/5'
                              : 'border-border hover:border-primary/40'
                          }`}
                          data-testid={`recharge-pack-${pack.pack_id}`}
                        >
                          <p className="text-sm font-medium">{pack.name}</p>
                          <p className="text-lg font-bold mt-1">${pack.price}</p>
                          <p className="text-xs text-muted-foreground">{pack.credits.toLocaleString()} credits</p>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

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
                  const icons = { search: Search, crawl: Globe, content_extract: FileText };
                  const Icon = icons[item.operation] || Zap;
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
                      <p className="text-sm font-medium capitalize">
                        {txn.type === 'cancellation' ? 'Cancelled' : txn.type === 'plan_change' ? `Changed to ${txn.plan_id}` : `${txn.plan_id} Plan`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(txn.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {txn.amount > 0 && <span className="text-sm font-mono">${txn.amount}</span>}
                      <Badge
                        variant={txn.payment_status === 'paid' ? 'default' : 'secondary'}
                        className={`text-xs ${
                          txn.payment_status === 'paid'
                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                            : txn.type === 'cancellation'
                            ? 'bg-red-500/10 text-red-500 border-red-500/20'
                            : ''
                        }`}
                      >
                        {txn.type === 'cancellation' ? 'cancelled' : txn.payment_status}
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

const PlanButton = ({ action, planId, loading, onSubscribe, onChangePlan, onCancelClick }) => {
  const isLoading = loading === planId;
  const Spinner = () => (
    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
  );

  switch (action) {
    case 'current':
      return (
        <Button variant="outline" className="w-full" disabled data-testid={`plan-btn-${planId}`}>
          Current Plan
        </Button>
      );
    case 'included':
      return (
        <Button variant="outline" className="w-full" disabled>
          Included
        </Button>
      );
    case 'contact':
      return (
        <Button
          variant="outline"
          className="w-full"
          onClick={() => window.location.href = 'mailto:enterprise@remora.info?subject=Enterprise%20Plan%20Inquiry'}
          data-testid={`plan-btn-${planId}`}
        >
          Contact Us
        </Button>
      );
    case 'subscribe':
      return (
        <Button
          className="w-full"
          onClick={() => onSubscribe(planId)}
          disabled={!!loading}
          data-testid={`plan-btn-${planId}`}
        >
          {isLoading ? <Spinner /> : <ArrowRight className="w-4 h-4 mr-2" />}
          Subscribe
        </Button>
      );
    case 'upgrade':
      return (
        <Button
          className="w-full"
          onClick={() => onChangePlan(planId)}
          disabled={!!loading}
          data-testid={`plan-btn-${planId}`}
        >
          {isLoading ? <Spinner /> : <ArrowRight className="w-4 h-4 mr-2" />}
          Upgrade
        </Button>
      );
    case 'downgrade':
      return (
        <Button
          variant="outline"
          className="w-full"
          onClick={() => onChangePlan(planId)}
          disabled={!!loading}
          data-testid={`plan-btn-${planId}`}
        >
          {isLoading ? <Spinner /> : <ArrowDown className="w-4 h-4 mr-2" />}
          Downgrade
        </Button>
      );
    case 'cancel':
      return (
        <Button
          variant="outline"
          className="w-full text-red-500 hover:text-red-600 hover:bg-red-500/5"
          onClick={onCancelClick}
          disabled={!!loading}
          data-testid={`plan-btn-${planId}`}
        >
          <XCircle className="w-4 h-4 mr-2" />
          Cancel to Free
        </Button>
      );
    default:
      return null;
  }
};

export default Billing;
