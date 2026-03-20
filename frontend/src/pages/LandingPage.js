import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Zap,
  Code2,
  Bot,
  Webhook,
  Shield,
  ArrowRight,
  Check,
  Terminal
} from 'lucide-react';

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 }
};

const stagger = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

const LandingPage = () => {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  const handleGetStarted = () => {
    if (user) {
      navigate('/dashboard');
    } else {
      login();
    }
  };

  const features = [
    {
      icon: Code2,
      title: 'Agent Query API',
      description: 'Accept structured JSON queries and return JSON results. Built for machines, not humans.',
      code: '{"query": "python async", "intent": "documentation"}'
    },
    {
      icon: Zap,
      title: 'Translation Layer',
      description: 'Crawls human websites, extracts structured data, and serves it as clean JSON.',
      code: '{"title": "...", "content": "...", "structured_data": {...}}'
    },
    {
      icon: Bot,
      title: 'Agent Registry',
      description: 'Register your agents with capabilities, endpoints, and authentication info.',
      code: '{"capabilities": ["search", "summarize"], "auth_type": "api_key"}'
    },
    {
      icon: Shield,
      title: 'API Key Auth',
      description: 'No cookies. Just API keys for secure agent identity and access control.',
      code: 'X-API-Key: rmr_aBc123...'
    },
    {
      icon: Webhook,
      title: 'Webhook Subscriptions',
      description: 'Agents subscribe to result updates and get notified in real-time.',
      code: '{"events": ["search.complete", "content.updated"]}'
    },
    {
      icon: Search,
      title: 'Tiered Rate Limiting',
      description: 'Free, Pro, and Enterprise tiers with flexible rate limits.',
      code: 'X-RateLimit-Remaining: 9542'
    }
  ];

  const pricingTiers = [
    {
      name: 'Free',
      price: '$0',
      period: '/month',
      requests: '100 requests/day',
      features: ['Basic search API', 'Agent registration', 'Community support'],
      cta: 'Get Started',
      popular: false
    },
    {
      name: 'Pro',
      price: '$49',
      period: '/month',
      requests: '10K requests/day',
      features: ['Everything in Free', 'Webhook subscriptions', 'Priority support', 'Advanced analytics'],
      cta: 'Start Free Trial',
      popular: true
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: '',
      requests: 'Unlimited requests',
      features: ['Everything in Pro', 'Custom integrations', 'SLA guarantee', 'Dedicated support'],
      cta: 'Contact Sales',
      popular: false
    }
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.08)_0%,rgba(0,0,0,0)_70%)]" />
        
        {/* Navigation */}
        <nav className="relative z-10 flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <Search className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-xl tracking-tight">Remora</span>
          </div>
          <div className="flex items-center gap-4">
            {user ? (
              <Button onClick={() => navigate('/dashboard')} data-testid="dashboard-btn">
                Dashboard
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            ) : (
              <Button onClick={login} data-testid="sign-in-btn">
                Sign In
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            )}
          </div>
        </nav>

        {/* Hero Content */}
        <motion.div 
          className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-32"
          initial="initial"
          animate="animate"
          variants={stagger}
        >
          <motion.div variants={fadeInUp} className="text-center max-w-4xl mx-auto">
            <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-xs font-mono tracking-wider">
              API-FIRST SEARCH ENGINE
            </Badge>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-none mb-6">
              The Search Engine
              <br />
              <span className="text-primary">for AI Agents</span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
              Give your AI agents structured access to the world's knowledge. 
              JSON in, JSON out. No HTML parsing required.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="lg" onClick={handleGetStarted} className="px-8 glow" data-testid="get-started-btn">
                Get Started Free
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
              <Button variant="outline" size="lg" className="px-8" data-testid="docs-btn">
                <Terminal className="mr-2 w-4 h-4" />
                View API Docs
              </Button>
            </div>
          </motion.div>

          {/* Code Example */}
          <motion.div 
            variants={fadeInUp}
            className="mt-16 max-w-3xl mx-auto"
          >
            <Card className="bg-card/50 border-border/50 overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-border/50 bg-muted/30">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-destructive/50" />
                  <div className="w-3 h-3 rounded-full bg-warning/50" />
                  <div className="w-3 h-3 rounded-full bg-success/50" />
                </div>
                <span className="text-xs text-muted-foreground font-mono ml-2">example_request.json</span>
              </div>
              <CardContent className="p-0">
                <pre className="p-6 text-sm overflow-x-auto bg-transparent">
                  <code className="text-foreground">
{`// Request
POST /api/search
X-API-Key: rmr_aBc123...

{
  "query": "python async patterns",
  "intent": "documentation",
  "max_results": 5
}

// Response
{
  "results": [
    {
      "title": "asyncio — Asynchronous I/O",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "structured_data": {
        "language": "python",
        "type": "documentation"
      }
    }
  ],
  "total": 42,
  "processing_time_ms": 23
}`}
                  </code>
                </pre>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6 bg-muted/20">
        <div className="max-w-7xl mx-auto">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
          >
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight mb-4">
              Built for Machines
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Every endpoint designed with AI agents in mind. Structured data, predictable responses, and zero parsing overhead.
            </p>
          </motion.div>

          {/* Bento Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: index * 0.1 }}
                >
                  <Card className="h-full bg-card/50 border-border/50 hover:border-primary/30 transition-colors duration-300">
                    <CardContent className="p-6">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                        <Icon className="w-5 h-5 text-primary" />
                      </div>
                      <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                      <p className="text-sm text-muted-foreground mb-4">{feature.description}</p>
                      <code className="text-xs text-primary bg-muted/50 px-2 py-1 rounded font-mono block overflow-x-auto">
                        {feature.code}
                      </code>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4 }}
          >
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight mb-4">
              Simple Pricing
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Start free, scale as you grow. No hidden fees.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {pricingTiers.map((tier, index) => (
              <motion.div
                key={tier.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
              >
                <Card className={`h-full ${tier.popular ? 'border-primary/50 glow' : 'border-border/50'}`}>
                  <CardContent className="p-6">
                    {tier.popular && (
                      <Badge className="mb-4 bg-primary text-primary-foreground">Most Popular</Badge>
                    )}
                    <h3 className="text-xl font-semibold mb-2">{tier.name}</h3>
                    <div className="mb-4">
                      <span className="text-4xl font-bold">{tier.price}</span>
                      <span className="text-muted-foreground">{tier.period}</span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-6">{tier.requests}</p>
                    <ul className="space-y-3 mb-6">
                      {tier.features.map((feature) => (
                        <li key={feature} className="flex items-center gap-2 text-sm">
                          <Check className="w-4 h-4 text-primary" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    <Button 
                      className="w-full" 
                      variant={tier.popular ? 'default' : 'outline'}
                      onClick={handleGetStarted}
                      data-testid={`pricing-${tier.name.toLowerCase()}-btn`}
                    >
                      {tier.cta}
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 bg-muted/20">
        <motion.div 
          className="max-w-3xl mx-auto text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <h2 className="text-3xl md:text-5xl font-semibold tracking-tight mb-4">
            Ready to Connect Your Agents?
          </h2>
          <p className="text-lg text-muted-foreground mb-8">
            Get your API key in seconds and start querying structured data.
          </p>
          <Button size="lg" onClick={handleGetStarted} className="px-8 glow" data-testid="cta-get-started-btn">
            Get Started Free
            <ArrowRight className="ml-2 w-4 h-4" />
          </Button>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Search className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold tracking-tight">Remora</span>
          </div>
          <p className="text-sm text-muted-foreground">
            © 2026 Remora. The Search Engine for AI Agents.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
