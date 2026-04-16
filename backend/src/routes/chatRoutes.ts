import { Router } from 'express';
import { getChatHistory, getChatSessions, deleteChatSession } from '../controllers/chatController';
import { authenticate } from '../utils/auth';

const router = Router();

// All chat routes require authentication
router.use(authenticate);

// GET /api/chat/sessions            — list all sessions with message count + preview
router.get('/sessions', getChatSessions);

// GET /api/chat/history             — all turns for the user (optional ?session_id=xxx)
router.get('/history', getChatHistory);

// DELETE /api/chat/sessions/:sessionId  — delete a full session
router.delete('/sessions/:sessionId', deleteChatSession);

export default router;
