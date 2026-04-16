const rawBaseUrl = process.env.EXPO_PUBLIC_POSE_API_BASE_URL?.trim() ?? '';

export const POSE_API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

export function getPoseAnalyzeUrl(exercise: string, sessionId?: string) {
  const url = new URL(`/api/pose/analyze/`, ensureBaseUrl());
  url.searchParams.set('type', exercise);

  if (sessionId) {
    url.searchParams.set('session_id', sessionId);
  }

  return url.toString();
}

export function getPoseCloseUrl(sessionId?: string) {
  const url = new URL(`/api/pose/close/`, ensureBaseUrl());

  if (sessionId) {
    url.searchParams.set('session_id', sessionId);
  }

  return url.toString();
}

function ensureBaseUrl() {
  if (!POSE_API_BASE_URL) {
    throw new Error(
      'Missing EXPO_PUBLIC_POSE_API_BASE_URL. Point it to your deployed pose backend.',
    );
  }

  return POSE_API_BASE_URL.endsWith('/') ? POSE_API_BASE_URL : `${POSE_API_BASE_URL}/`;
}
