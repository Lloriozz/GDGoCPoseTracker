import { Request, Response } from 'express';
import prisma from '../config/prisma';

// Get all forum posts
export const getAllPosts = async (req: Request, res: Response) => {
  try {
    const page = parseInt(req.query.page as string) || 1;
    const limit = parseInt(req.query.limit as string) || 10;
    const skip = (page - 1) * limit;

    const posts = await prisma.forumPost.findMany({
      include: {
        user: {
          select: {
            id: true,
            username: true,
            avatarUrl: true
          }
        },
        comments: {
          include: {
            user: {
              select: {
                id: true,
                username: true,
                avatarUrl: true
              }
            },
            media: true
          },
          orderBy: {
            createdAt: 'asc'
          }
        },
        media: true,
        _count: {
          select: {
            comments: true
          }
        }
      },
      orderBy: {
        createdAt: 'desc'
      },
      skip,
      take: limit
    });

    const total = await prisma.forumPost.count();

    res.json({
      posts,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit)
      }
    });
  } catch (error) {
    console.error('Get posts error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Get post by ID
export const getPostById = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const post = await prisma.forumPost.findUnique({
      where: { id },
      include: {
        user: {
          select: {
            id: true,
            username: true,
            avatarUrl: true,
            bio: true
          }
        },
        comments: {
          include: {
            user: {
              select: {
                id: true,
                username: true,
                avatarUrl: true
              }
            },
            media: true
          },
          orderBy: {
            createdAt: 'desc'
          }
        },
        media: true
      }
    });

    if (!post) {
      return res.status(404).json({ error: 'Post not found' });
    }

    res.json(post);
  } catch (error) {
    console.error('Get post error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Create new post
export const createPost = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { title, content } = req.body;

    const post = await prisma.forumPost.create({
      data: {
        userId,
        title,
        content,
        likes: 0
      },
      include: {
        user: {
          select: {
            id: true,
            username: true,
            avatarUrl: true
          }
        }
      }
    });

    res.status(201).json({
      message: 'Post created successfully',
      post
    });
  } catch (error) {
    console.error('Create post error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Add comment to post
export const addComment = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id: postId } = req.params;
    const { content } = req.body;

    console.log('Adding comment:', { userId, postId, content });

    const comment = await prisma.forumComment.create({
      data: {
        userId,
        postId,
        content
      },
      include: {
        user: {
          select: {
            id: true,
            username: true,
            avatarUrl: true
          }
        },
        media: true
      }
    });

    res.status(201).json({
      message: 'Comment added successfully',
      comment
    });
  } catch (error: any) {
    console.error('Add comment error:', error);
    console.error('Error details:', error.message);
    console.error('Error code:', error.code);
    res.status(500).json({ error: 'Internal server error', message: error.message });
  }
};

// Get comments for a post
export const getPostComments = async (req: Request, res: Response) => {
  try {
    const { id: postId } = req.params;

    const comments = await prisma.forumComment.findMany({
      where: { postId },
      include: {
        user: {
          select: {
            id: true,
            username: true,
            avatarUrl: true
          }
        },
        media: true
      },
      orderBy: {
        createdAt: 'asc'
      }
    });

    res.json(comments);
  } catch (error) {
    console.error('Get comments error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

// Like post
export const likePost = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const post = await prisma.forumPost.update({
      where: { id },
      data: {
        likes: {
          increment: 1
        }
      }
    });

    res.json({
      message: 'Post liked successfully',
      likes: post.likes
    });
  } catch (error) {
    console.error('Like post error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};
