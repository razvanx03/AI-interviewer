import React, { useState, useMemo, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Bot,
  Plus,
  MessageSquare,
  Trash2,
  CheckCircle2,
  Clock,
  X,
  Search,
  PanelLeftClose,
  PanelLeftOpen,
  ChevronLeft,
  LogOut,
  UserCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { SettingsMenu } from '@/components/settings/SettingsMenu';
import { DeleteConfirmDialog } from '@/components/dialogs/DeleteConfirmDialog';
import { useLanguage } from '@/hooks/use-language';
import { useInterviews } from '@/hooks/use-interviews';
import { useAdminAuth } from '@/hooks/use-admin-auth';
import { InterviewSession } from '@/types';
import { cn } from '@/lib/utils';
import { apiClearEntireDatabase } from '@/lib/api';
import { clearAllStoredInterviewIds } from '@/lib/storage';

interface SwipeableHistoryItemProps {
  item: InterviewSession;
  isActive: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string, e: React.MouseEvent | React.TouchEvent) => void;
}

const SwipeableHistoryItem: React.FC<SwipeableHistoryItemProps> = ({
  item,
  isActive,
  onSelect,
  onDelete,
}) => {
  const [isSwiped, setIsSwiped] = useState(false);
  const touchStartX = useRef(0);
  const touchStartY = useRef(0);
  const isCompleted = item.status === 'completed';

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const deltaX = e.changedTouches[0].clientX - touchStartX.current;
    const deltaY = e.changedTouches[0].clientY - touchStartY.current;

    // Only trigger horizontal swipe when horizontal distance exceeds vertical
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 30) {
      if (deltaX < -30) {
        setIsSwiped(true);
      } else if (deltaX > 30) {
        setIsSwiped(false);
      }
    }
  };

  const handleChevronClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsSwiped((prev) => !prev);
  };

  return (
    <div className="relative overflow-hidden rounded-lg">
      {/* Background Revealed Red Delete Action: only visible when swiped, preventing 1px border bleed */}
      <div
        className={cn(
          'absolute inset-y-0 right-0 flex w-16 items-center justify-center bg-destructive text-destructive-foreground rounded-r-lg transition-opacity duration-150',
          isSwiped ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
      >
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(item.id, e);
            setIsSwiped(false);
          }}
          className="flex h-full w-full items-center justify-center text-destructive-foreground hover:opacity-90 active:scale-95 transition-transform"
          title="Delete interview"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Foreground Item Card */}
      <div
        onClick={() => {
          if (isSwiped) {
            setIsSwiped(false);
          } else {
            onSelect(item.id);
          }
        }}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        className={cn(
          'group relative flex cursor-pointer items-center justify-between px-3 py-2.5 text-xs transition-all duration-200 ease-out bg-card z-10',
          isSwiped ? 'rounded-l-lg rounded-r-none -translate-x-16' : 'rounded-lg translate-x-0',
          isActive
            ? 'bg-accent text-accent-foreground font-medium'
            : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
        )}
      >
        <div className="flex min-w-0 items-center gap-2.5 flex-1 mr-1">
          <div className="shrink-0 text-muted-foreground group-hover:text-foreground">
            {isCompleted ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            ) : (
              <Clock className="h-4 w-4 text-amber-500" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium text-foreground">{item.jobTitle}</p>
            <p className="truncate text-[11px] text-muted-foreground">
              {item.candidateName} •{' '}
              {new Date(item.createdAt).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
              })}
            </p>
          </div>
        </div>

        {/* Right side: Chevron trigger for mobile slide + Desktop hover trash */}
        <div className="flex items-center gap-1 shrink-0">
          {/* Mobile slide trigger arrow */}
          <button
            type="button"
            onClick={handleChevronClick}
            className="flex md:hidden p-1 text-muted-foreground/60 hover:text-foreground active:scale-90 transition-transform cursor-pointer"
            title="Slide to delete"
          >
            <ChevronLeft
              className={cn(
                'h-3.5 w-3.5 transition-transform duration-200',
                isSwiped && 'rotate-180 text-foreground'
              )}
            />
          </button>

          {/* Desktop Hover Delete button */}
          <button
            type="button"
            onClick={(e) => onDelete(item.id, e)}
            title="Delete interview"
            className="ml-2 hidden rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive md:group-hover:inline-flex cursor-pointer"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

interface SidebarProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isCollapsed,
  onToggleCollapse,
  mobileOpen,
  onMobileClose,
}) => {
  const { interviews, deleteInterview, refreshInterviews } = useInterviews();
  const { isAdmin, adminEmail, logout } = useAdminAuth();
  const { id: activeId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useLanguage();

  const [searchOpen, setSearchOpen] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [clearModalOpen, setClearModalOpen] = useState(false);
  const [isClearing, setIsClearing] = useState(false);

  // ==============================================================================
  // [DEV ONLY - TEMPORARY TESTING HANDLER TO BE REMOVED LATER]
  // ==============================================================================
  const handleConfirmClearDatabase = async () => {
    setIsClearing(true);
    try {
      await apiClearEntireDatabase();
      clearAllStoredInterviewIds();
      await refreshInterviews();
      setClearModalOpen(false);
      navigate('/');
    } catch (err) {
      console.error('Failed to clear database:', err);
    } finally {
      setIsClearing(false);
    }
  };

  const filteredInterviews = useMemo(() => {
    if (!searchTerm.trim()) return interviews;
    const query = searchTerm.toLowerCase();
    return interviews.filter(
      (item) =>
        item.jobTitle.toLowerCase().includes(query) ||
        (item.companyName && item.companyName.toLowerCase().includes(query)) ||
        item.candidateName.toLowerCase().includes(query)
    );
  }, [interviews, searchTerm]);

  const handleSelect = (id: string) => {
    navigate(`/interview/${id}`);
    onMobileClose();
  };

  const handleNewInterview = () => {
    if (isAdmin) {
      navigate('/');
      onMobileClose();
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleDeleteClick = (id: string, e: React.MouseEvent | React.TouchEvent) => {
    e.stopPropagation();
    setPendingDeleteId(id);
  };

  const handleConfirmDelete = async () => {
    if (!pendingDeleteId) return;
    const idToDelete = pendingDeleteId;
    setPendingDeleteId(null);

    await deleteInterview(idToDelete);
    if (activeId === idToDelete) {
      navigate('/');
    }
  };

  const handleCollapseClick = () => {
    if (window.innerWidth < 768) {
      onMobileClose();
    } else {
      onToggleCollapse();
    }
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          onClick={onMobileClose}
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-xs md:hidden"
        />
      )}

      {/* Sidebar Container with Smooth Width Transition */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border bg-card/95 backdrop-blur overflow-hidden transition-[width,transform] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]',
          /* Mobile behavior: full 72 width slide-in */
          'w-72',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
          /* Desktop behavior: static in flow, collapsible rail */
          'md:static md:translate-x-0',
          isCollapsed ? 'md:w-16' : 'md:w-72'
        )}
      >
        {/* COLLAPSED STATE (Desktop only - ChatGPT Style Narrow Rail) */}
        <div
          className={cn(
            'hidden md:flex absolute inset-0 w-16 flex-col items-center justify-between py-3 transition-opacity duration-200 ease-in-out',
            isCollapsed
              ? 'opacity-100 pointer-events-auto z-10'
              : 'opacity-0 pointer-events-none z-0'
          )}
        >
          {/* Top Icons */}
          <div className="flex flex-col items-center gap-3">
            {/* App Logo */}
            <div
              onClick={handleNewInterview}
              className={`flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-xs transition-opacity ${
                isAdmin ? 'cursor-pointer hover:opacity-90' : 'cursor-default'
              }`}
              title={t.brand.name}
            >
              <Bot className="h-5 w-5" />
            </div>

            {isAdmin && (
              <>
                {/* [DEV ONLY] Collapsed Clear DB Button */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setClearModalOpen(true)}
                  className="h-9 w-9 rounded-lg text-red-500 hover:bg-red-500/10 hover:text-red-600"
                  title="[DEV ONLY] Clear Entire Database"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>

                {/* New Interview Button */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleNewInterview}
                  className="h-9 w-9 rounded-lg text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                  title={t.sidebar.newInterview}
                >
                  <Plus className="h-4.5 w-4.5" />
                </Button>

                {/* Search Button (expands sidebar and opens search) */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    onToggleCollapse();
                    setSearchOpen(true);
                  }}
                  className="h-9 w-9 rounded-lg text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                  title="Search interviews"
                >
                  <Search className="h-4 w-4" />
                </Button>
              </>
            )}

            {!isAdmin && (
              <div
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground"
                title="Candidate Guest Mode"
              >
                <UserCheck className="h-4 w-4" />
              </div>
            )}
          </div>

          {/* Bottom Actions: Settings & Logout on top, Expand Sidebar Button on bottom */}
          <div className="flex flex-col items-center gap-2 pt-2">
            {isAdmin && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                className="h-8 w-8 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                title="Sign Out"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            )}
            <SettingsMenu />
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleCollapse}
              className="h-8 w-8 rounded-lg text-muted-foreground hover:bg-accent/60 hover:text-foreground"
              title="Expand sidebar"
            >
              <PanelLeftOpen className="h-4 w-4" />
              <span className="sr-only">Expand sidebar</span>
            </Button>
          </div>
        </div>

        {/* EXPANDED FULL SIDEBAR (Always on Mobile, or when not collapsed on Desktop) */}
        <div
          className={cn(
            'flex h-full w-72 min-w-[18rem] flex-col transition-opacity duration-200 ease-in-out',
            isCollapsed
              ? 'opacity-0 pointer-events-none md:invisible'
              : 'opacity-100 pointer-events-auto'
          )}
        >
          {/* Top Header & Brand */}
          <div className="flex h-16 shrink-0 items-center justify-between border-b border-border px-4">
            <div
              onClick={handleNewInterview}
              className={`flex items-center gap-2.5 transition-opacity ${
                isAdmin ? 'cursor-pointer hover:opacity-90' : 'cursor-default'
              }`}
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-bold tracking-tight text-foreground">
                    {t.brand.name}
                  </span>
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  {isAdmin ? (
                    <Badge
                      variant="outline"
                      className="text-[9px] px-1.5 py-0 h-3.5 border-primary/40 text-primary font-semibold"
                    >
                      Recruiter Admin
                    </Badge>
                  ) : (
                    <Badge
                      variant="outline"
                      className="text-[9px] px-1.5 py-0 h-3.5 border-muted-foreground/40 text-muted-foreground font-medium"
                    >
                      Candidate Guest
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            {/* Mobile Close Button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={onMobileClose}
              className="h-8 w-8 text-muted-foreground hover:text-foreground md:hidden"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* ADMIN ONLY CONTROLS & INTERVIEW HISTORY */}
          {isAdmin ? (
            <>
              {/* ================================================================= */}
              {/* [DEV ONLY - TEMPORARY CLEAR DB BUTTON TO BE REMOVED LATER]       */}
              {/* ================================================================= */}
              <div className="px-3 pt-3 pb-0 shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setClearModalOpen(true)}
                  className="w-full justify-start gap-2 border-red-500/30 text-red-500 hover:bg-red-500/10 hover:text-red-600 shadow-2xs text-xs font-medium"
                  title="[DEV ONLY] Truncate and clear all database tables"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Clear Entire DB (Dev)</span>
                </Button>
              </div>

              {/* Action: New Interview Button */}
              <div className="p-3 pb-2 shrink-0">
                <Button
                  onClick={handleNewInterview}
                  className="w-full justify-start gap-2 shadow-xs"
                  size="sm"
                >
                  <Plus className="h-4 w-4" />
                  <span>{t.sidebar.newInterview}</span>
                </Button>
              </div>

              {/* Search Bar Toggle & Animated Input Accordion */}
              <div className="px-3 shrink-0">
                <div className="flex items-center justify-between px-1 pt-1 pb-0.5 text-xs text-muted-foreground">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">
                    {t.sidebar.historyTitle}
                  </span>
                  <button
                    type="button"
                    onClick={() => setSearchOpen(!searchOpen)}
                    className="rounded p-1 text-muted-foreground hover:bg-accent/60 hover:text-foreground cursor-pointer transition-colors"
                    title="Search"
                  >
                    <Search className="h-3.5 w-3.5" />
                  </button>
                </div>

                <div
                  className={cn(
                    'grid transition-all duration-200 ease-out',
                    searchOpen
                      ? 'grid-rows-[1fr] opacity-100 mt-1 mb-1.5'
                      : 'grid-rows-[0fr] opacity-0 m-0'
                  )}
                >
                  <div className="overflow-hidden">
                    <Input
                      type="text"
                      placeholder={t.sidebar.searchPlaceholder}
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="h-8 text-xs bg-background/50 focus-visible:ring-1 focus-visible:ring-ring"
                    />
                  </div>
                </div>
              </div>

              {/* History List */}
              <div className="flex-1 overflow-y-auto px-3 pt-0.5 pb-1">
                {interviews.length === 0 ? (
                  <div className="px-3 py-8 text-center text-xs text-muted-foreground">
                    <MessageSquare className="mx-auto mb-2 h-6 w-6 opacity-40" />
                    {t.sidebar.noInterviews}
                    <br />
                    {t.sidebar.startPrompt}
                  </div>
                ) : filteredInterviews.length === 0 ? (
                  <div className="px-3 py-6 text-center text-xs text-muted-foreground">
                    {t.sidebar.noSearchResults}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {filteredInterviews.map((item) => (
                      <SwipeableHistoryItem
                        key={item.id}
                        item={item}
                        isActive={item.id === activeId}
                        onSelect={handleSelect}
                        onDelete={handleDeleteClick}
                      />
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            /* CANDIDATE GUEST VIEW: NO OTHER CHATS, NO NEW INTERVIEW BUTTON */
            <div className="flex-1 flex flex-col justify-center items-center px-4 py-8 text-center space-y-4">
              <div className="h-12 w-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-xs">
                <UserCheck className="h-6 w-6" />
              </div>
              <div className="space-y-1.5 max-w-[220px]">
                <h4 className="text-xs font-bold text-foreground">Candidate Interview Room</h4>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  You are in a live technical interview session. Please respond directly in the chat
                  to proceed.
                </p>
              </div>
            </div>
          )}

          {/* Sidebar Footer: User info / Sign out on Left, Settings & Collapse button on Right */}
          <div className="flex shrink-0 items-center justify-between border-t border-border p-3">
            {isAdmin ? (
              <div className="flex items-center gap-1.5 min-w-0 pr-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  className="h-7 px-2 gap-1 text-[11px] text-muted-foreground hover:bg-destructive/10 hover:text-destructive cursor-pointer truncate"
                  title={`Sign out (${adminEmail || 'admin'})`}
                >
                  <LogOut className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">Sign Out</span>
                </Button>
              </div>
            ) : (
              <span className="text-[11px] text-muted-foreground pl-1">
                {t.sidebar.themeAndPrefs}
              </span>
            )}
            <div className="flex items-center gap-1 shrink-0">
              <SettingsMenu />
              <Button
                variant="ghost"
                size="icon"
                onClick={handleCollapseClick}
                className="h-8 w-8 text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                title="Collapse sidebar"
              >
                <PanelLeftClose className="h-4 w-4" />
                <span className="sr-only">Collapse sidebar</span>
              </Button>
            </div>
          </div>
        </div>
      </aside>

      {/* Custom Accessible shadcn Delete Confirmation Modal */}
      <DeleteConfirmDialog
        open={Boolean(pendingDeleteId)}
        onOpenChange={(open) => {
          if (!open) setPendingDeleteId(null);
        }}
        onConfirm={handleConfirmDelete}
      />

      {/* ================================================================= */}
      {/* [DEV ONLY - TEMPORARY CLEAR DB CONFIRMATION MODAL TO BE REMOVED]  */}
      {/* ================================================================= */}
      <Dialog open={clearModalOpen} onOpenChange={setClearModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="h-5 w-5" />
              Clear Entire Database (Dev)
            </DialogTitle>
            <DialogDescription>
              This is a development testing utility. It will permanently truncate all interviews,
              candidates, and chat transcripts in PostgreSQL. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0 mt-2">
            <Button
              variant="outline"
              onClick={() => setClearModalOpen(false)}
              disabled={isClearing}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmClearDatabase}
              disabled={isClearing}
              className="gap-2"
            >
              {isClearing ? 'Clearing Database...' : 'Yes, Truncate Database'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
