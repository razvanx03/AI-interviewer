import React from 'react';
import { Settings, Sun, Moon, Laptop, Globe, Check, Palette } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/hooks/use-theme';
import { useLanguage } from '@/hooks/use-language';

export const SettingsMenu: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const { language, setLanguage, t } = useLanguage();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-lg text-muted-foreground hover:bg-accent/60 hover:text-foreground"
          title={t.settings.title}
        >
          <Settings className="h-4 w-4" />
          <span className="sr-only">{t.settings.title}</span>
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        side="top"
        align="start"
        sideOffset={8}
        className="w-56 rounded-xl border border-border bg-popover/95 p-1.5 shadow-xl backdrop-blur"
      >
        <DropdownMenuLabel className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {t.settings.title}
        </DropdownMenuLabel>

        {/* 1. Theme Submenu */}
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium cursor-pointer">
            <Palette className="h-3.5 w-3.5 text-muted-foreground" />
            <span>{t.settings.themeLabel}</span>
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent
            sideOffset={6}
            className="w-36 rounded-xl border border-border bg-popover/95 p-1 shadow-xl backdrop-blur"
          >
            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setTheme('light');
              }}
              className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <Sun className="h-3.5 w-3.5 text-amber-500" />
                {t.settings.themeLight}
              </span>
              {theme === 'light' && <Check className="h-3.5 w-3.5 text-primary" />}
            </DropdownMenuItem>

            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setTheme('dark');
              }}
              className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <Moon className="h-3.5 w-3.5 text-blue-400" />
                {t.settings.themeDark}
              </span>
              {theme === 'dark' && <Check className="h-3.5 w-3.5 text-primary" />}
            </DropdownMenuItem>

            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setTheme('system');
              }}
              className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <Laptop className="h-3.5 w-3.5 text-muted-foreground" />
                {t.settings.themeSystem}
              </span>
              {theme === 'system' && <Check className="h-3.5 w-3.5 text-primary" />}
            </DropdownMenuItem>
          </DropdownMenuSubContent>
        </DropdownMenuSub>

        {/* 2. Language Submenu */}
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium cursor-pointer">
            <Globe className="h-3.5 w-3.5 text-muted-foreground" />
            <span>{t.settings.languageLabel}</span>
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent
            sideOffset={6}
            className="w-36 rounded-xl border border-border bg-popover/95 p-1 shadow-xl backdrop-blur"
          >
            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setLanguage('en');
              }}
              className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <span className="font-semibold text-[11px] text-muted-foreground w-4">EN</span>
                {t.settings.langEn}
              </span>
              {language === 'en' && <Check className="h-3.5 w-3.5 text-primary" />}
            </DropdownMenuItem>

            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                setLanguage('ro');
              }}
              className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium cursor-pointer"
            >
              <span className="flex items-center gap-2">
                <span className="font-semibold text-[11px] text-muted-foreground w-4">RO</span>
                {t.settings.langRo}
              </span>
              {language === 'ro' && <Check className="h-3.5 w-3.5 text-primary" />}
            </DropdownMenuItem>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
