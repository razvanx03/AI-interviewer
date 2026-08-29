import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, CheckCircle2, ShieldCheck } from 'lucide-react';
import confetti from 'canvas-confetti';
import { ThinkingOrb } from 'thinking-orbs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { InterviewSession, ChatMessage } from '@/types';
import { apiStreamSendMessage } from '@/lib/api';
import { useLanguage } from '@/hooks/use-language';
import { useAdminAuth } from '@/hooks/use-admin-auth';

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
  const { isAdmin } = useAdminAuth();
  const [inputText, setInputText] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const { t } = useLanguage();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const parseMessageEvaluation = (msg: ChatMessage) => {
    const EVAL_MARKERS = ['**Overall AI Assessment:', '**Evaluare Generală AI:'];
    for (const marker of EVAL_MARKERS) {
      if (msg.content.includes(marker)) {
        const parts = msg.content.split(marker);
        const speech = parts[0].trim();
        const evalBody = marker + parts.slice(1).join(marker);
        return { hasEvaluation: true, speech, evalBody };
      }
    }
    return { hasEvaluation: false, speech: msg.content, evalBody: '' };
  };

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
          accumulatedText += chunk.replace(/\[INTERVIEW_COMPLETE\]/g, '');

          if (!hasStartedStreaming) {
            hasStartedStreaming = true;
            setIsAiThinking(false);
          }

          const assistantMsg: ChatMessage = {
            id: assistantTempId,
            role: 'assistant',
            content: accumulatedText.replace(/\[INTERVIEW_COMPLETE\]/g, '').trimEnd(),
            createdAt: new Date().toISOString(),
          };

          onSessionUpdate({
            ...session,
            messages: [...messagesWithUser, assistantMsg],
            updatedAt: new Date().toISOString(),
          });
        },
        (data) => {
          const cleanFinalText = accumulatedText.replace(/\[INTERVIEW_COMPLETE\]/g, '').trim();
          const finalAssistantMsg: ChatMessage = {
            id: data.messageId || assistantTempId,
            role: 'assistant',
            content: cleanFinalText,
            questionNumber: data.questionNumber,
            createdAt: new Date().toISOString(),
          };

          const isSessionDone = Boolean(
            data.isComplete || accumulatedText.includes('[INTERVIEW_COMPLETE]')
          );
          const finalSession: InterviewSession = {
            ...session,
            messages: [...messagesWithUser, finalAssistantMsg],
            status: isSessionDone ? 'completed' : 'active',
            updatedAt: new Date().toISOString(),
          };
          onSessionUpdate(finalSession);

          if (isSessionDone) {
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
            const { hasEvaluation, speech, evalBody } = parseMessageEvaluation(msg);

            let bubbleContent = msg.content;
            if (isAssistant && hasEvaluation) {
              if (isAdmin) {
                // For admin, bubble contains the spoken conclusion only, because the evaluation is displayed in the dedicated Admin Card below!
                bubbleContent = speech || t.chat.concludedText;
              } else {
                // For guest candidate, show spoken conclusion + candidate friendly wrap-up
                bubbleContent =
                  (speech ? `${speech}\n\n` : '') +
                  (session.language === 'ro'
                    ? `Îți mulțumim pentru participarea la interviu, ${session.candidateName}!\n\nRăspunsurile tale și transcrierea au fost înregistrate și trimise către echipa de recrutare pentru analiză.\nEchipa de HR te va contacta în curând cu următorii pași.`
                    : `Thank you for completing your interview, ${session.candidateName}!\n\nYour responses and interview transcript have been recorded and submitted to the hiring team for evaluation.\nThe recruitment team will review your application and get in touch with you regarding next steps.`);
              }
            }

            return (
              <React.Fragment key={msg.id}>
                <div
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

                    <div className="flex items-center gap-2 max-w-full">
                      <div
                        className={`rounded-2xl px-3.5 py-2.5 sm:px-4 sm:py-3 text-sm leading-relaxed max-w-full overflow-hidden ${
                          isAssistant
                            ? 'rounded-tl-xs bg-primary text-primary-foreground shadow-xs'
                            : 'rounded-tr-xs bg-muted/80 dark:bg-card text-foreground border border-border shadow-2xs'
                        }`}
                      >
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => (
                              <p className="mb-2 last:mb-0 leading-relaxed whitespace-pre-wrap">
                                {children}
                              </p>
                            ),
                            strong: ({ children }) => (
                              <strong className="font-semibold">{children}</strong>
                            ),
                            ul: ({ children }) => (
                              <ul className="my-2 ml-4 list-disc space-y-1">{children}</ul>
                            ),
                            ol: ({ children }) => (
                              <ol className="my-2 ml-4 list-decimal space-y-1">{children}</ol>
                            ),
                            li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                          }}
                        >
                          {bubbleContent}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>

                  {!isAssistant && (
                    <div className="flex h-7 w-7 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-lg sm:rounded-xl bg-secondary text-secondary-foreground border border-border">
                      <User className="h-3.5 w-3.5 sm:h-5 sm:w-5 text-foreground" />
                    </div>
                  )}
                </div>

                {/* Dedicated Admin Evaluation Card: Displayed strictly for Admin */}
                {isAdmin && isAssistant && hasEvaluation && evalBody && (
                  <div className="w-full my-4 rounded-xl border border-primary/40 bg-card p-4 sm:p-5 shadow-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="h-5 w-5 text-primary" />
                        <span className="text-sm font-semibold text-foreground tracking-tight">
                          {t.chat.adminEvalTitle}
                        </span>
                      </div>
                      <Badge
                        variant="outline"
                        className="text-[11px] bg-primary/10 text-primary border-primary/30 font-medium"
                      >
                        {t.chat.adminEvalBadge}
                      </Badge>
                    </div>

                    <div className="text-xs sm:text-sm text-foreground leading-relaxed">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({ children }) => (
                            <p className="mb-2.5 last:mb-0 leading-relaxed text-foreground/90">
                              {children}
                            </p>
                          ),
                          strong: ({ children }) => (
                            <strong className="font-semibold text-foreground">{children}</strong>
                          ),
                          ul: ({ children }) => (
                            <ul className="my-2 ml-4 list-disc space-y-1.5 text-foreground/90">
                              {children}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="my-2 ml-4 list-decimal space-y-1.5 text-foreground/90">
                              {children}
                            </ol>
                          ),
                          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                          table: ({ children }) => (
                            <div className="my-3 overflow-x-auto rounded-lg border border-border bg-muted/20">
                              <table className="min-w-full text-xs text-left divide-y divide-border">
                                {children}
                              </table>
                            </div>
                          ),
                          thead: ({ children }) => (
                            <thead className="bg-muted/70 font-semibold text-foreground">
                              {children}
                            </thead>
                          ),
                          tbody: ({ children }) => (
                            <tbody className="divide-y divide-border/60 bg-card/60">
                              {children}
                            </tbody>
                          ),
                          tr: ({ children }) => (
                            <tr className="transition-colors hover:bg-muted/30">{children}</tr>
                          ),
                          th: ({ children }) => (
                            <th className="px-3.5 py-2.5 font-semibold text-foreground align-top">
                              {children}
                            </th>
                          ),
                          td: ({ children }) => (
                            <td className="px-3.5 py-2.5 text-foreground/90 align-top break-words whitespace-normal leading-relaxed">
                              {children}
                            </td>
                          ),
                        }}
                      >
                        {evalBody}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}
              </React.Fragment>
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

          {/* Completed Interview Banner or Admin Generating Card */}
          {session.status === 'completed' &&
            (isAdmin &&
            (isEnding || !session.messages.some((m) => parseMessageEvaluation(m).hasEvaluation)) ? (
              <div className="my-4 sm:my-6 rounded-xl border border-primary/40 bg-card p-5 sm:p-6 shadow-sm space-y-3 text-center animate-pulse">
                <div className="mx-auto mb-2 flex items-center justify-center">
                  <ThinkingOrb state="working" size={64} />
                </div>
                <h4 className="text-sm sm:text-base font-bold text-foreground">
                  {session.language === 'ro'
                    ? 'Sesiune Finalizată • Se generează raportul de evaluare...'
                    : 'Session Completed • Generating Evaluation Report...'}
                </h4>
                <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                  {session.language === 'ro'
                    ? 'AI-ul analizează transcrierea completă a răspunsurilor și sintetizează scorurile tehnice, punctele forte și ariile de îmbunătățire.'
                    : 'The AI is analyzing the full interview transcript and synthesizing technical scores, strengths, and areas for improvement.'}
                </p>
              </div>
            ) : (
              <div className="my-4 sm:my-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 sm:p-5 text-center">
                <div className="mx-auto mb-2 flex h-9 w-9 sm:h-10 sm:w-10 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-600">
                  <CheckCircle2 className="h-5 w-5 sm:h-6 sm:w-6" />
                </div>
                <h4 className="text-sm sm:text-base font-bold text-foreground">
                  {t.chat.completedTitle}
                </h4>
                <p className="mt-1 text-xs text-muted-foreground">{t.chat.completedDesc}</p>
              </div>
            ))}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Docked Bottom Area */}
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
          ) : isAdmin ? (
            /* RECRUITER / ADMIN VIEW: READ-ONLY OBSERVATION */
            <div className="flex items-center justify-center gap-2.5 py-3 px-4 rounded-xl border border-primary/20 bg-primary/5 text-xs text-muted-foreground font-medium select-none">
              <ShieldCheck className="h-4 w-4 text-primary shrink-0" />
              <span>
                Recruiter Observation Mode: You are viewing the live transcript. The candidate has
                active interactive access.
              </span>
            </div>
          ) : (
            /* CANDIDATE INTERACTIVE INPUT */
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
