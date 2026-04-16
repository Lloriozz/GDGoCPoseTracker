export type ChatRole = 'assistant' | 'user';

export interface ChatApiRequest {
  user_id: string;
  session_id: string;
  message: string;
  profile_patch?: Record<string, unknown>;
}

export interface ChatApiResponse {
  session_id: string;
  reply: string;
  intent: string;
  safety_flag: boolean;
  missing_fields: string[];
  tool_results: Record<string, unknown>;
}

export interface ChatUiMessage {
  id: string;
  role: ChatRole;
  text: string;
  meta?: string;
}
