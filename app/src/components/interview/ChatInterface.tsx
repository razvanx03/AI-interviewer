import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, CheckCircle2 } from 'lucide-react';
import confetti from 'canvas-confetti';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { InterviewSession, ChatMessage } from '@/types';
import { generateMockAiResponse } from '@/lib/mockAi';
import { saveInterview } from '@/lib/storage';

interface ChatInterfaceProps {
  session: InterviewSession;
  onSessionUpdate: (updated: InterviewSession) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ session, onSessionUpdate }) => {
  const [inputText, setInputText] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [session.messages, isAiThinking]);

  const handleSendMessage = async () => {
    const text = inputText.trim();
    if (!text || isAiThinking || session.status === 'completed') return;

    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...session.messages, userMessage];
    const updatedSession: InterviewSession = {
      ...session,
      messages: updatedMessages,
      updatedAt: new Date().toISOString(),
    };

    onSessionUpdate(updatedSession);
    saveInterview(updatedSession);
    setInputText('');
    setIsAiThinking(true);

    try {
      const aiResponse = await generateMockAiResponse(updatedSession, text);

      const aiMessage: ChatMessage = {
        id: Math.random().toString(36).substring(2, 9),
        role: 'assistant',
        content: aiResponse.reply,
        timestamp: new Date().toISOString(),
        questionNumber: updatedMessages.filter((m) => m.role === 'assistant').length + 1,
      };

      const finalSession: InterviewSession = {
        ...updatedSession,
        messages: [...updatedMessages, aiMessage],
        status: aiResponse.isComplete ? 'completed' : 'active',
        updatedAt: new Date().toISOString(),
      };

      onSessionUpdate(finalSession);
      saveInterview(finalSession);

      if (aiResponse.isComplete) {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 },
        });
      }
    } catch (err) {
      console.error('Error generating AI response:', err);
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
    <div className="flex h-full flex-col rounded-xl border border-border/80 bg-card shadow-sm">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {session.messages.map((msg, index) => {
          const isAssistant = msg.role === 'assistant';
          return (
            <div
              key={msg.id || index}
              className={`flex items-start gap-3 sm:gap-4 ${
                isAssistant ? 'justify-start' : 'justify-end'
              }`}
            >
              {isAssistant && (
                <div className="flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-xs">
                  <Bot className="h-4 w-4 sm:h-5 sm:w-5" />
                </div>
              )}

              <div
                className={`flex max-w-[85%] sm:max-w-[75%] flex-col ${
                  isAssistant ? 'items-start' : 'items-end'
                }`}
              >
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-xs font-semibold text-foreground">
                    {isAssistant ? 'AI Interviewer' : session.candidateName}
                  </span>
                  {isAssistant && msg.questionNumber && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                      Question #{msg.questionNumber}
                    </Badge>
                  )}
                  <span className="text-[10px] text-muted-foreground">
                    {new Date(msg.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>

                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                    isAssistant
                      ? 'rounded-tl-xs bg-muted/60 text-foreground border border-border/60 shadow-2xs'
                      : 'rounded-tr-xs bg-primary text-primary-foreground shadow-xs'
                  }`}
                >
                  {msg.content}
                </div>
              </div>

              {!isAssistant && (
                <div className="flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-xl bg-secondary text-secondary-foreground border border-border/60">
                  <User className="h-4 w-4 sm:h-5 sm:w-5 text-foreground" />
                </div>
              )}
            </div>
          );
        })}

        {/* AI Typing / Generating indicator */}
        {isAiThinking && (
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground animate-pulse">
              <Bot className="h-4 w-4 sm:h-5 sm:w-5" />
            </div>
            <div className="flex items-center gap-2 rounded-2xl rounded-tl-xs bg-muted/60 border border-border/60 px-4 py-3 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
              <span>Interviewer is evaluating and formulating question...</span>
            </div>
          </div>
        )}

        {/* Completed Interview Banner */}
        {session.status === 'completed' && (
          <div className="my-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5 text-center">
            <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-600">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <h4 className="text-base font-bold text-foreground">Interview Session Completed</h4>
            <p className="mt-1 text-xs text-muted-foreground">
              All questions have been completed. This transcript is preserved locally in your
              browser.
            </p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border/80 bg-background/50 p-4">
        {session.status === 'completed' ? (
          <div className="flex items-center justify-between py-2 text-xs text-muted-foreground">
            <span>Interview has concluded. Thank you for participating!</span>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="relative flex items-end gap-2">
              <Textarea
                ref={textareaRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your response... (Press Enter to send, Shift+Enter for new line)"
                className="min-h-[70px] resize-none pr-12 text-sm"
                disabled={isAiThinking}
              />
              <Button
                onClick={handleSendMessage}
                disabled={!inputText.trim() || isAiThinking}
                size="icon"
                className="absolute bottom-2.5 right-2.5 h-8 w-8 rounded-lg shadow-sm"
              >
                {isAiThinking ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="flex items-center justify-between text-[11px] text-muted-foreground px-1">
              <span>💡 Be concise and specific with examples from your experience</span>
              <span>Enter ↵ to send</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
