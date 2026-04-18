import React, { createContext, ReactNode, useContext, useRef, useState } from 'react';
import { CHAT_QUICK_ACTIONS } from '../constants/chat';
import { ChatServiceError, sendChatMessage } from '../services/chat';
import { ChatUiMessage } from '../types/chat';
import { useAuth } from './AuthContext';

type ChatbotContextValue = {
  input: string;
  loading: boolean;
  messages: ChatUiMessage[];
  quickActions: typeof CHAT_QUICK_ACTIONS;
  resetConversation: () => void;
  sendMessage: (rawText?: string) => Promise<void>;
  setInput: (value: string) => void;
};

const DEFAULT_CONNECTION_ERROR =
  'Mình chưa kết nối được với trợ lý lúc này. Bạn thử lại sau ít phút nhé.';

const ChatbotContext = createContext<ChatbotContextValue | undefined>(undefined);

function createSessionId() {
  return `mobile-session-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function createGuestUserId() {
  return `guest-user-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function buildMessage(role: 'assistant' | 'user', text: string, meta?: string): ChatUiMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    meta,
  };
}

export function ChatbotProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [guestUserId] = useState(createGuestUserId);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [sessionId, setSessionId] = useState(createSessionId);
  const conversationRevisionRef = useRef(0);
  const requestControllerRef = useRef<AbortController | null>(null);

  const userId = user?.id || guestUserId;

  const resetConversation = () => {
    conversationRevisionRef.current += 1;
    requestControllerRef.current?.abort();
    requestControllerRef.current = null;
    setInput('');
    setLoading(false);
    setMessages([]);
    setSessionId(createSessionId());
  };

  const sendMessage = async (rawText?: string) => {
    const nextText = (rawText ?? input).trim();
    if (!nextText || loading) {
      return;
    }

    const requestController = new AbortController();
    const revisionAtRequestStart = conversationRevisionRef.current;
    const requestSessionId = sessionId;

    requestControllerRef.current = requestController;
    setMessages((current) => [...current, buildMessage('user', nextText)]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendChatMessage(
        {
          user_id: userId,
          session_id: requestSessionId,
          message: nextText,
        },
        { signal: requestController.signal }
      );

      if (
        requestController.signal.aborted ||
        conversationRevisionRef.current !== revisionAtRequestStart
      ) {
        return;
      }

      const meta = response.missing_fields.length
        ? `Cần thêm: ${response.missing_fields.join(', ')}`
        : response.intent.replaceAll('_', ' ');

      setMessages((current) => [...current, buildMessage('assistant', response.reply, meta)]);
    } catch (error) {
      if (
        requestController.signal.aborted ||
        (error instanceof Error && error.name === 'AbortError')
      ) {
        return;
      }

      const userMessage =
        error instanceof ChatServiceError ? error.userMessage : DEFAULT_CONNECTION_ERROR;

      console.warn(
        '[chatbot] request failed',
        error instanceof ChatServiceError ? error.technicalDetail ?? error.message : error
      );

      if (conversationRevisionRef.current !== revisionAtRequestStart) {
        return;
      }

      setMessages((current) => [
        ...current,
        buildMessage('assistant', userMessage, 'Lỗi kết nối'),
      ]);
    } finally {
      if (requestControllerRef.current === requestController) {
        requestControllerRef.current = null;
      }
      if (conversationRevisionRef.current === revisionAtRequestStart) {
        setLoading(false);
      }
    }
  };

  const value: ChatbotContextValue = {
    input,
    loading,
    messages,
    quickActions: CHAT_QUICK_ACTIONS,
    resetConversation,
    sendMessage,
    setInput,
  };

  return <ChatbotContext.Provider value={value}>{children}</ChatbotContext.Provider>;
}

export function useChatbot() {
  const context = useContext(ChatbotContext);
  if (!context) {
    throw new Error('useChatbot must be used within a ChatbotProvider');
  }
  return context;
}
