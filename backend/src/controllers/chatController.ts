import { Request, Response } from 'express';
import prisma from '../config/prisma';

// GET /api/chat/history
// Returns the authenticated user's full chat history, grouped by session.
export const getChatHistory = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const limit = parseInt(req.query.limit as string) || 50;
    const sessionId = req.query.session_id as string | undefined;

    const where: any = { userId };
    if (sessionId) where.sessionId = sessionId;

    const turns = await prisma.chatTurn.findMany({
      where,
      orderBy: { createdAt: 'asc' },
      take: limit,
      select: {
        id: true,
        sessionId: true,
        userMessage: true,
        assistantMessage: true,
        createdAt: true,
      },
    });

    res.json({ turns });
  } catch (error) {
    console.error('Get chat history error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// GET /api/chat/sessions
// Returns a list of distinct sessions for the authenticated user,
// with message count, last message timestamp, and first-message preview.
export const getChatSessions = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // Fetch all turns for the user (ascending so first message = preview)
    const turns = await prisma.chatTurn.findMany({
      where: { userId },
      select: { sessionId: true, userMessage: true, createdAt: true },
      orderBy: { createdAt: 'asc' },
    });

    // Aggregate sessions in memory
    const sessionMap: Record<string, {
      sessionId: string;
      messageCount: number;
      lastMessageAt: Date;
      preview: string;
    }> = {};

    for (const turn of turns) {
      if (!sessionMap[turn.sessionId]) {
        sessionMap[turn.sessionId] = {
          sessionId: turn.sessionId,
          messageCount: 0,
          lastMessageAt: turn.createdAt,
          preview: turn.userMessage, // first message in the session
        };
      }
      sessionMap[turn.sessionId].messageCount++;
      sessionMap[turn.sessionId].lastMessageAt = turn.createdAt; // keep updating to last
    }

    // Sort by most recent session first
    const sessions = Object.values(sessionMap).sort(
      (a, b) => b.lastMessageAt.getTime() - a.lastMessageAt.getTime()
    );

    res.json({ sessions });
  } catch (error) {
    console.error('Get chat sessions error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// DELETE /api/chat/sessions/:sessionId
// Deletes all turns for a given session belonging to the authenticated user.
export const deleteChatSession = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { sessionId } = req.params;

    const { count } = await prisma.chatTurn.deleteMany({
      where: { userId, sessionId },
    });

    if (count === 0) {
      return res.status(404).json({ error: 'Session not found' });
    }

    res.json({ message: 'Chat session deleted successfully', deletedTurns: count });
  } catch (error) {
    console.error('Delete chat session error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};
