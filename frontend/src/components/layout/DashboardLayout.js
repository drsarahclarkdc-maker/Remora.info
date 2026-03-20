import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  LayoutDashboard,
  Key,
  Bot,
  Webhook,
  Search,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  Globe,
  History,
  Send,
  Settings2,
  Building2,
  ArrowUpDown,
  CreditCard,
  Zap,
  Bell
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'API Keys', href: '/keys', icon: Key },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: 'Sources', href: '/sources', icon: Globe },
  { name: 'Crawl Rules', href: '/crawl-rules', icon: Settings2 },
  { name: 'Webhooks', href: '/webhooks', icon: Webhook },
  { name: 'Deliveries', href: '/webhooks/deliveries', icon: Send },
  { name: 'Search Test', href: '/search', icon: Search },
  { name: 'Ranking', href: '/ranking', icon: ArrowUpDown },
  { name: 'Crawl History', href: '/history', icon: History },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Billing', href: '/billing', icon: CreditCard },
  { name: 'Organizations', href: '/organizations', icon: Building2 },
];

const DashboardLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [credits, setCredits] = useState(null);
  const [notifications, setNotifications] = useState({ notifications: [], unread_count: 0 });
  const [notifOpen, setNotifOpen] = useState(false);

  const isActive = (href) => location.pathname === href;

  const fetchCredits = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/billing/usage`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setCredits(data);
      }
    } catch {}
  }, []);

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/notifications`, { credentials: 'include' });
      if (res.ok) setNotifications(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    if (user) {
      fetchCredits();
      fetchNotifications();
      const interval = setInterval(() => { fetchCredits(); fetchNotifications(); }, 30000);
      return () => clearInterval(interval);
    }
  }, [user, fetchCredits, fetchNotifications]);

  const markAllRead = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/notifications/read-all`, { method: 'POST', credentials: 'include' });
      fetchNotifications();
    } catch {}
  };

  const creditPct = credits ? Math.max(0, 100 - (credits.usage_percentage || 0)) : 100;
  const creditColor = creditPct > 50 ? 'bg-emerald-500' : creditPct > 20 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar - Desktop */}
      <aside className="fixed left-0 top-0 z-40 hidden lg:flex h-screen w-64 flex-col border-r border-border bg-card">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 border-b border-border px-6">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Search className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-semibold text-lg tracking-tight">Remora</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link
                key={item.name}
                to={item.href}
                data-testid={`nav-${item.name.toLowerCase().replace(' ', '-')}`}
                className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Credit Counter */}
        {credits && (
          <div className="px-4 pb-2">
            <Link to="/billing" className="block p-3 rounded-lg bg-muted/40 hover:bg-muted/60 transition-colors" data-testid="sidebar-credit-counter">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Credits</span>
                <span className="text-xs font-medium text-muted-foreground">{credits.plan_name}</span>
              </div>
              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-lg font-bold tabular-nums" data-testid="sidebar-credits-remaining">
                  {(credits.credits_remaining || 0).toLocaleString()}
                </span>
                <span className="text-xs text-muted-foreground">/ {(credits.credits_total || 0).toLocaleString()}</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
                <div className={`h-full rounded-full transition-all ${creditColor}`} style={{ width: `${creditPct}%` }} />
              </div>
              {credits.alert && (
                <p className="text-xs text-yellow-500 mt-1.5 font-medium">Running low — upgrade plan</p>
              )}
            </Link>
          </div>
        )}

        {/* User section */}
        <div className="border-t border-border p-4">
          <div className="flex items-center gap-3">
            <Avatar className="w-9 h-9">
              <AvatarImage src={user?.picture} alt={user?.name} />
              <AvatarFallback className="bg-primary/10 text-primary text-sm">
                {user?.name?.charAt(0) || 'U'}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.tier} tier</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 h-16 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <div className="flex h-full items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Search className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-lg tracking-tight">Remora</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            data-testid="mobile-menu-btn"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </Button>
        </div>
      </header>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-background/95 backdrop-blur pt-16">
          <nav className="p-4 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 rounded-md px-3 py-3 text-base font-medium transition-colors ${
                    active
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {item.name}
                </Link>
              );
            })}
            <div className="pt-4 border-t border-border mt-4">
              <Link
                to="/settings"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 rounded-md px-3 py-3 text-base font-medium text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                <Settings className="w-5 h-5" />
                Settings
              </Link>
              <button
                onClick={() => { setMobileMenuOpen(false); logout(); }}
                className="w-full flex items-center gap-3 rounded-md px-3 py-3 text-base font-medium text-destructive hover:bg-destructive/10"
              >
                <LogOut className="w-5 h-5" />
                Logout
              </button>
            </div>
          </nav>
        </div>
      )}

      {/* Main content */}
      <main className="lg:pl-64 pt-16 lg:pt-0">
        {/* Top header - Desktop */}
        <header className="hidden lg:flex sticky top-0 z-30 h-16 items-center justify-between border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80 px-6">
          <div />
          <div className="flex items-center gap-4">
            {/* Notification bell */}
            <div className="relative">
              <Button
                variant="ghost"
                size="icon"
                className="relative"
                onClick={() => { setNotifOpen(!notifOpen); if (notifications.unread_count > 0) markAllRead(); }}
                data-testid="notification-bell"
              >
                <Bell className="w-4 h-4" />
                {notifications.unread_count > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-[10px] font-bold text-white flex items-center justify-center">
                    {notifications.unread_count > 9 ? '9+' : notifications.unread_count}
                  </span>
                )}
              </Button>
              {notifOpen && (
                <div className="absolute right-0 mt-2 w-80 rounded-lg border border-border bg-card shadow-lg z-50" data-testid="notification-dropdown">
                  <div className="p-3 border-b border-border">
                    <p className="text-sm font-semibold">Notifications</p>
                  </div>
                  <div className="max-h-64 overflow-y-auto">
                    {notifications.notifications.length === 0 ? (
                      <p className="p-4 text-sm text-muted-foreground text-center">No notifications</p>
                    ) : (
                      notifications.notifications.slice(0, 10).map((n) => (
                        <div
                          key={n.notification_id}
                          className={`p-3 border-b border-border/50 last:border-0 ${!n.read ? 'bg-primary/5' : ''}`}
                        >
                          <p className="text-sm font-medium">{n.title}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">{n.message}</p>
                          <p className="text-[10px] text-muted-foreground mt-1">{new Date(n.created_at).toLocaleString()}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
            {/* Credit counter in header */}
            {credits && (
              <Link
                to="/billing"
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/40 hover:bg-muted/60 transition-colors"
                data-testid="header-credit-counter"
              >
                <Zap className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-sm font-medium tabular-nums" data-testid="header-credits-remaining">
                  {(credits.credits_remaining || 0).toLocaleString()}
                </span>
                <span className="text-xs text-muted-foreground">credits</span>
              </Link>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-9 w-9 rounded-full" data-testid="user-menu-btn">
                  <Avatar className="h-9 w-9">
                    <AvatarImage src={user?.picture} alt={user?.name} />
                    <AvatarFallback className="bg-primary/10 text-primary">
                      {user?.name?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="flex items-center justify-start gap-2 p-2">
                  <div className="flex flex-col space-y-0.5">
                    <p className="text-sm font-medium">{user?.name}</p>
                    <p className="text-xs text-muted-foreground">{user?.email}</p>
                  </div>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/settings" className="cursor-pointer">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="text-destructive cursor-pointer">
                  <LogOut className="mr-2 h-4 w-4" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page content */}
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
};

export default DashboardLayout;
