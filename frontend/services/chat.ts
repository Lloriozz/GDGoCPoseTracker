import { CHAT_API_BASE_URL } from '../config/api';
import { ChatApiRequest, ChatApiResponse } from '../types/chat';

type ChatErrorKind = 'network' | 'server';

export class ChatServiceError extends Error {
  readonly kind: ChatErrorKind;
  readonly status?: number;
  readonly technicalDetail?: string;
  readonly userMessage: string;

  constructor(
    kind: ChatErrorKind,
    userMessage: string,
    technicalDetail?: string,
    status?: number
  ) {
    super(technicalDetail ?? userMessage);
    this.kind = kind;
    this.name = 'ChatServiceError';
    this.status = status;
    this.technicalDetail = technicalDetail;
    this.userMessage = userMessage;
  }
}

function buildServerError(status: number, detail: string) {
  if (status >= 500) {
    return new ChatServiceError(
      'server',
      'Backend chat đang gặp lỗi. Bạn thử lại sau ít phút nhé.',
      detail,
      status
    );
  }

  return new ChatServiceError(
    'server',
    'Yêu cầu chat chưa hợp lệ hoặc phiên hiện tại đã lỗi. Bạn thử bắt đầu lại nhé.',
    detail,
    status
  );
}

export async function sendChatMessage(
  payload: ChatApiRequest,
  options: { signal?: AbortSignal } = {}
): Promise<ChatApiResponse> {
  let response: Response;

  try {
    response = await fetch(`${CHAT_API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: options.signal,
      body: JSON.stringify(payload),
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw error;
    }

    const message =
      error instanceof Error && error.message ? error.message : 'Failed to fetch';

    throw new ChatServiceError(
      'network',
      'Mình chưa kết nối được với trợ lý lúc này. Hãy kiểm tra mạng hoặc backend chat rồi thử lại nhé.',
      `Request to ${CHAT_API_BASE_URL}/chat failed: ${message}`
    );
  }

  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw buildServerError(response.status, detail || `Backend responded with ${response.status}.`);
  }

  return response.json();
}
