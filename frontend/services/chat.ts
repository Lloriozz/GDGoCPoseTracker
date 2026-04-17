import { CHAT_API_BASE_URL } from '../config/api';
import { ChatApiRequest, ChatApiResponse } from '../types/chat';

export async function sendChatMessage(payload: ChatApiRequest): Promise<ChatApiResponse> {
  let response: Response;

  try {
    response = await fetch(`${CHAT_API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    const message =
      error instanceof Error && error.message
        ? error.message
        : 'Failed to fetch';

    throw new Error(
      `Không gọi được backend tại ${CHAT_API_BASE_URL}/chat. ` +
      `Hãy kiểm tra backend đã chạy ở cổng 8000 chưa và có cho phép CORS chưa. Chi tiết: ${message}`
    );
  }

  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(detail || `Backend trả lỗi ${response.status}.`);
  }

  return response.json();
}
