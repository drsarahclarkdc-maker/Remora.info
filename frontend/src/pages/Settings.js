import DashboardLayout from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/context/AuthContext';
import { 
  User, 
  Mail, 
  Shield, 
  LogOut, 
  ExternalLink,
  Crown,
  Zap
} from 'lucide-react';

const RATE_LIMITS = {
  free: { limit: 100, price: 'Free' },
  pro: { limit: 10000, price: '$49/mo' },
  enterprise: { limit: -1, price: 'Custom' }
};

const Settings = () => {
  const { user, logout } = useAuth();

  const currentPlan = RATE_LIMITS[user?.tier || 'free'];

  return (
    <DashboardLayout>
      <div className="space-y-8 max-w-3xl" data-testid="settings-page">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground mt-1">
            Manage your account and subscription.
          </p>
        </div>

        {/* Profile Card */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <User className="w-5 h-5" />
              Profile
            </CardTitle>
            <CardDescription>Your account information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center gap-6">
              <Avatar className="w-20 h-20">
                <AvatarImage src={user?.picture} alt={user?.name} />
                <AvatarFallback className="bg-primary/10 text-primary text-2xl">
                  {user?.name?.charAt(0) || 'U'}
                </AvatarFallback>
              </Avatar>
              <div>
                <h3 className="text-xl font-semibold">{user?.name}</h3>
                <p className="text-muted-foreground flex items-center gap-2 mt-1">
                  <Mail className="w-4 h-4" />
                  {user?.email}
                </p>
              </div>
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-wider text-muted-foreground">User ID</p>
                <code className="text-sm font-mono mt-1">{user?.user_id}</code>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Subscription Card */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Crown className="w-5 h-5" />
              Subscription
            </CardTitle>
            <CardDescription>Your current plan and usage limits</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold capitalize">{user?.tier} Plan</h4>
                    <Badge variant={user?.tier === 'enterprise' ? 'default' : 'outline'}>
                      Current
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    {currentPlan.limit === -1 
                      ? 'Unlimited requests per day'
                      : `${currentPlan.limit.toLocaleString()} requests per day`}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-bold text-lg">{currentPlan.price}</p>
              </div>
            </div>

            {user?.tier !== 'enterprise' && (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Need more requests? Upgrade your plan to unlock higher limits and more features.
                </p>
                <div className="flex gap-3">
                  {user?.tier === 'free' && (
                    <Button data-testid="upgrade-pro-btn">
                      Upgrade to Pro
                      <ExternalLink className="w-4 h-4 ml-2" />
                    </Button>
                  )}
                  <Button variant="outline" data-testid="contact-sales-btn">
                    Contact Sales
                    <ExternalLink className="w-4 h-4 ml-2" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Security Card */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Security
            </CardTitle>
            <CardDescription>Manage your session</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Sign Out</p>
                <p className="text-sm text-muted-foreground mt-0.5">
                  End your current session and sign out of all devices.
                </p>
              </div>
              <Button 
                variant="destructive" 
                onClick={logout}
                data-testid="logout-btn"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default Settings;
