import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, CheckCircle2 } from 'lucide-react';
import confetti from 'canvas-confetti';
import { ThinkingOrb } from 'thinking-orbs';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { InterviewSession, ChatMessage } from '@/types';
import { apiStreamSendMessage } from '@/lib/api';
import { useLanguage } from '@/hooks/use-language';

interface ChatInterfaceProps {
  session: InterviewSession;
  onSessionUpdate: (updated: InterviewSession) => void;
  isEnding?: boolean;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  session,
  onSessionUpdate,
  isEnding = false,
}) => {
  const [inputText, setInputText] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const { t } = useLanguage();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [session.messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [inputText]);

  useEffect(() => {
    if (!isAiThinking && session.status !== 'completed') {
      const timer = setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isAiThinking, session.status]);

  const handleSendMessage = async (overrideText?: string) => {
    const text = (overrideText !== undefined ? overrideText : inputText).trim();
    if (!text || isAiThinking || session.status === 'completed') return;

    if (overrideText === undefined) {
      setInputText('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
    setStreamError(null);
    setIsAiThinking(true);

    const now = new Date().toISOString();
    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: 'user',
      content: text,
      createdAt: now,
    };

    const assistantTempId = Math.random().toString(36).substring(2, 9);
    let accumulatedText = '';
    let hasStartedStreaming = false;

    // Add user message if not retrying an existing message
    const messagesWithUser =
      overrideText !== undefined ? session.messages : [...session.messages, userMessage];

    if (overrideText === undefined) {
      onSessionUpdate({
        ...session,
        messages: messagesWithUser,
        updatedAt: now,
      });
    }

    try {
      await apiStreamSendMessage(
        session.id,
        text,
        (chunk: string) => {
          accumulatedText += chunk;

          if (!hasStartedStreaming) {
            hasStartedStreaming = true;
            setIsAiThinking(false);
          }

          const assistantMsg: ChatMessage = {
            id: assistantTempId,
            role: 'assistant',
            content: accumulatedText,
            createdAt: new Date().toISOString(),
          };

          onSessionUpdate({
            ...session,
            messages: [...messagesWithUser, assistantMsg],
            updatedAt: new Date().toISOString(),
          });
        },
        (data) => {
          const finalAssistantMsg: ChatMessage = {
            id: data.messageId || assistantTempId,
            role: 'assistant',
            content: accumulatedText.trim(),
            questionNumber: data.questionNumber,
            createdAt: new Date().toISOString(),
          };

          const finalSession: InterviewSession = {
            ...session,
            messages: [...messagesWithUser, finalAssistantMsg],
            status: data.isComplete ? 'completed' : 'active',
            updatedAt: new Date().toISOString(),
          };
          onSessionUpdate(finalSession);

          if (data.isComplete) {
            confetti({
              particleCount: 80,
              spread: 70,
              origin: { y: 0.6 },
            });
          }
        }
      );
    } catch (err: unknown) {
      console.error('Error in chat stream:', err);
      const errMsg =
        err instanceof Error ? err.message : 'Connection interrupted while waiting for response.';
      setStreamError(errMsg);
    } finally {
      setIsAiThinking(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Scrollable Message List */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-6">
        <div className="mx-auto max-w-3xl space-y-4 sm:space-y-6">
          {session.messages.map((msg) => {
            const isAssistant = msg.role === 'assistant';

            return (
              <div
                key={msg.id}
                className={`flex items-start gap-2.5 sm:gap-3 ${
                  isAssistant ? 'justify-start' : 'justify-end'
                }`}
              >
                {isAssistant && (
                  <div className="flex h-7 w-7 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-lg sm:rounded-xl bg-primary text-primary-foreground shadow-xs">
                    <Bot className="h-3.5 w-3.5 sm:h-5 sm:w-5" />
                  </div>
                )}

                <div
                  className={`flex max-w-[92%] sm:max-w-[80%] flex-col ${
                    isAssistant ? 'items-start' : 'items-end'
                  }`}
                >
                  <div className="mb-1 flex items-center gap-1.5 sm:gap-2">
                    <span className="text-xs font-semibold text-foreground">
                      {isAssistant ? t.chat.aiTitle : session.candidateName}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {msg.createdAt
                        ? new Date(msg.createdAt).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : ''}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <div
                      className={`rounded-2xl px-3.5 py-2.5 sm:px-4 sm:py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                        isAssistant
                          ? 'rounded-tl-xs bg-primary text-primary-foreground shadow-xs'
                          : 'rounded-tr-xs bg-muted/80 dark:bg-card text-foreground border border-border shadow-2xs'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                </div>

                {!isAssistant && (
                  <div className="flex h-7 w-7 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-lg sm:rounded-xl bg-secondary text-secondary-foreground border border-border">
                    <User className="h-3.5 w-3.5 sm:h-5 sm:w-5 text-foreground" />
                  </div>
                )}
              </div>
            );
          })}

          {/* AI Typing / Generating indicator with ThinkingOrb solving */}
          {isAiThinking && (
            <div className="flex items-start gap-2.5 sm:gap-3">
              <div className="flex h-7 w-7 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-lg sm:rounded-xl bg-primary text-primary-foreground shadow-xs">
                <Bot className="h-3.5 w-3.5 sm:h-5 sm:w-5" />
              </div>
              <div className="flex items-center gap-2 rounded-2xl rounded-tl-xs bg-primary text-primary-foreground shadow-xs px-3.5 py-2.5 sm:px-4 sm:py-3 text-xs">
                <div className="dark:invert">
                  <ThinkingOrb state="solving" size={20} />
                </div>
                <span>{t.chat.thinking}</span>
              </div>
            </div>
          )}

          {/* Completed Interview Banner */}
          {session.status === 'completed' && (
            <div className="my-4 sm:my-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 sm:p-5 text-center">
              <div className="mx-auto mb-2 flex h-9 w-9 sm:h-10 sm:w-10 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-600">
                <CheckCircle2 className="h-5 w-5 sm:h-6 sm:w-6" />
              </div>
              <h4 className="text-sm sm:text-base font-bold text-foreground">
                {t.chat.completedTitle}
              </h4>
              <p className="mt-1 text-xs text-muted-foreground">{t.chat.completedDesc}</p>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Docked Bottom Input Area */}
      <div className="border-t border-border bg-card/60 p-3 sm:p-4 backdrop-blur">
        <div className="mx-auto max-w-3xl">
          {isEnding ? (
            <div className="flex items-center justify-center gap-2.5 py-3 text-xs text-muted-foreground animate-pulse">
              <ThinkingOrb state="working" size={20} />
              <span>
                {t.header?.endingText || 'Generating final technical evaluation & hiring report...'}
              </span>
            </div>
          ) : session.status === 'completed' ? (
            <div className="flex items-center justify-center gap-2 py-3 text-xs text-muted-foreground">
              <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
              <span>{t.chat.concludedText}</span>
            </div>
          ) : (
            <div className="space-y-2">
              {streamError && (
                <div className="flex items-center justify-between gap-3 rounded-xl border border-destructive/40 bg-destructive/10 p-2.5 px-3 text-xs text-destructive">
                  <span className="truncate">Connection error: {streamError}</span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const lastUserMsg = [...session.messages]
                        .reverse()
                        .find((m) => m.role === 'user');
                      if (lastUserMsg) {
                        handleSendMessage(lastUserMsg.content);
                      }
                    }}
                    className="h-7 px-2.5 text-xs font-semibold border-destructive/40 hover:bg-destructive/20 text-destructive shrink-0 cursor-pointer"
                  >
                    Retry Response
                  </Button>
                </div>
              )}
              <div className="relative flex items-center">
                <Textarea
                  ref={textareaRef}
                  rows={1}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={t.chat.inputPlaceholder}
                  className="min-h-[48px] max-h-44 resize-none pr-12 py-3 sm:py-3.5 text-sm leading-relaxed [scrollbar-width:none] [&::-webkit-scrollbar]:hidden overflow-y-auto bg-background border-border/80 focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/30 shadow-xs transition-all"
                  disabled={isAiThinking}
                  autoFocus
                />
                <Button
                  onClick={() => handleSendMessage()}
                  disabled={!inputText.trim() || isAiThinking}
                  size="icon"
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 h-8 w-8 rounded-lg shadow-xs transition-all duration-150 hover:opacity-90 hover:scale-105 active:scale-95 cursor-pointer disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:opacity-40 disabled:opacity-40 select-none"
                >
                  {isAiThinking ? (
                    <ThinkingOrb state="working" size={20} />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
