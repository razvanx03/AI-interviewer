import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Bot,
  Lock,
  Mail,
  AlertCircle,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  Globe,
  Check,
} from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ModeToggle } from '@/components/mode-toggle';
import { useAdminAuth } from '@/hooks/use-admin-auth';
import { useLanguage } from '@/hooks/use-language';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAdminAuth();
  const { language, setLanguage } = useLanguage();

  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const success = await login(usernameOrEmail, password);
      if (success) {
        navigate(from, { replace: true });
      } else {
        setError(
          import.meta.env.DEV
            ? 'Invalid username/email or password. Default is admin / admin.'
            : 'Invalid username/email or password.'
        );
      }
    } catch {
      setError('Connection failed. Please ensure the backend server is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemoFill = () => {
    setUsernameOrEmail('admin@ai-interviewer.com');
    setPassword('admin');
    setError(null);
  };

  return (
    <div className="relative flex min-h-screen w-screen items-center justify-center bg-background px-4 py-8">
      {/* Top Bar for Language & Theme Switcher */}
      <div className="absolute top-4 right-4 sm:top-6 sm:right-6 flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-8.5 gap-1.5 px-2.5 text-xs font-medium bg-card/60 backdrop-blur"
            >
              <Globe className="h-3.5 w-3.5 text-muted-foreground" />
              <span>{language === 'ro' ? 'RO' : 'EN'}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-36">
            <DropdownMenuItem
              onClick={() => setLanguage('en')}
              className="flex items-center justify-between text-xs cursor-pointer"
            >
              <span>English</span>
              {language === 'en' && <Check className="h-3.5 w-3.5 text-primary" />}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => setLanguage('ro')}
              className="flex items-center justify-between text-xs cursor-pointer"
            >
              <span>Română</span>
              {language === 'ro' && <Check className="h-3.5 w-3.5 text-primary" />}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <ModeToggle />
      </div>

      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-md">
            <Bot className="h-6 w-6" />
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            AI Interviewer Portal
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Recruiter & Administrator Control Hub
          </p>
        </div>

        <Card className="border-border/80 bg-card shadow-sm">
          <CardHeader className="space-y-1 pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base sm:text-lg font-semibold">Admin Sign In</CardTitle>
              <Badge
                variant="outline"
                className="text-[10px] gap-1 px-2 py-0.5 border-primary/40 text-primary"
              >
                <ShieldCheck className="h-3 w-3" />
                <span>Protected</span>
              </Badge>
            </div>
            <CardDescription className="text-xs">
              Access candidate screening, interview wizards, and full hiring reports.
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4 pt-0">
              {error && (
                <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs font-medium text-destructive">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="usernameOrEmail" className="text-xs font-medium">
                  Username or Email
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="usernameOrEmail"
                    type="text"
                    placeholder="admin or admin@ai-interviewer.com"
                    value={usernameOrEmail}
                    onChange={(e) => setUsernameOrEmail(e.target.value)}
                    className="pl-9 h-9 text-xs"
                    autoFocus
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-xs font-medium">
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-9 h-9 text-xs"
                    required
                  />
                </div>
              </div>

              {/* Demo Fill Helper (Development only) */}
              {import.meta.env.DEV && (
                <div className="rounded-lg bg-muted/40 border border-border/50 p-2.5 flex items-center justify-between text-xs">
                  <div className="space-y-0.5">
                    <span className="font-semibold text-foreground text-[11px] block">
                      Demo Credentials:
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      admin / admin
                    </span>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleQuickDemoFill}
                    className="h-7 text-[11px] px-2.5 gap-1 border-border/70 hover:bg-primary/10 hover:text-primary cursor-pointer"
                  >
                    <Sparkles className="h-3 w-3" />
                    <span>Auto Fill</span>
                  </Button>
                </div>
              )}
            </CardContent>

            <CardFooter className="flex flex-col gap-3 pt-2">
              <Button
                type="submit"
                disabled={isLoading || !usernameOrEmail.trim() || !password.trim()}
                className="w-full h-9 text-xs font-semibold gap-1.5 cursor-pointer shadow-2xs"
              >
                <span>{isLoading ? 'Authenticating...' : 'Sign In as Admin'}</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
};
