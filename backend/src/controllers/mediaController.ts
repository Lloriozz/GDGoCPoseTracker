import { Request, Response } from 'express';
import prisma from '../config/prisma';
import cloudinary from '../config/cloudinary';
import fs from 'fs';
import path from 'path';

// Upload image to Cloudinary and create media record
export const uploadImage = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;
    const { image, usage, postId, commentId } = req.body;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    if (!image) {
      return res.status(400).json({ error: 'No image provided' });
    }

    // Upload base64 to Cloudinary
    const result = await cloudinary.uploader.upload(image, {
      folder: 'pose-tracker',
      resource_type: 'image',
    });

    // Create media record
    const media = await prisma.media.create({
      data: {
        userId,
        type: 'image',
        usage: usage || 'post',
        cloudinaryId: result.public_id,
        url: result.secure_url,
        mimeType: 'image/jpeg',
        size: 0, // Can't determine size from base64 easily
        postId: postId || null,
        commentId: commentId || null,
      },
    });

    res.status(201).json({
      message: 'Image uploaded successfully',
      media,
    });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: 'Failed to upload image' });
  }
};

// Upload video to Cloudinary and create media record
export const uploadVideo = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;
    const { usage, exerciseType } = req.body;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    // Upload to Cloudinary
    const result = await cloudinary.uploader.upload(req.file.path, {
      folder: 'pose-tracker/training',
      resource_type: 'video',
    });

    // Create media record
    const media = await prisma.media.create({
      data: {
        userId,
        type: 'video',
        usage: usage || 'training',
        cloudinaryId: result.public_id,
        url: result.secure_url,
        mimeType: req.file.mimetype,
        size: req.file.size,
        exerciseType: exerciseType || null,
      },
    });

    res.status(201).json({
      message: 'Video uploaded successfully',
      media,
    });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: 'Failed to upload video' });
  }
};

// Get media by ID
export const getMediaById = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const media = await prisma.media.findUnique({
      where: { id },
      include: {
        user: {
          select: {
            id: true,
            username: true,
          },
        },
      },
    });

    if (!media) {
      return res.status(404).json({ error: 'Media not found' });
    }

    res.json(media);
  } catch (error) {
    console.error('Get media error:', error);
    res.status(500).json({ error: 'Failed to get media' });
  }
};

// Delete media
export const deleteMedia = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;
    const { id } = req.params;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const media = await prisma.media.findUnique({
      where: { id },
    });

    if (!media) {
      return res.status(404).json({ error: 'Media not found' });
    }

    // Check ownership
    if (media.userId !== userId) {
      return res.status(403).json({ error: 'Forbidden' });
    }

    // Delete from Cloudinary
    if (media.cloudinaryId) {
      await cloudinary.uploader.destroy(media.cloudinaryId);
    }

    // Delete from database
    await prisma.media.delete({
      where: { id },
    });

    res.json({ message: 'Media deleted successfully' });
  } catch (error) {
    console.error('Delete media error:', error);
    res.status(500).json({ error: 'Failed to delete media' });
  }
};

// Get media for a post
export const getPostMedia = async (req: Request, res: Response) => {
  try {
    const { postId } = req.params;

    const media = await prisma.media.findMany({
      where: { postId, usage: 'post' },
      include: {
        user: {
          select: {
            id: true,
            username: true,
          },
        },
      },
      orderBy: { createdAt: 'desc' },
    });

    res.json(media);
  } catch (error) {
    console.error('Get post media error:', error);
    res.status(500).json({ error: 'Failed to get post media' });
  }
};

// Get media for a comment
export const getCommentMedia = async (req: Request, res: Response) => {
  try {
    const { commentId } = req.params;

    const media = await prisma.media.findMany({
      where: { commentId, usage: 'comment' },
      include: {
        user: {
          select: {
            id: true,
            username: true,
          },
        },
      },
      orderBy: { createdAt: 'desc' },
    });

    res.json(media);
  } catch (error) {
    console.error('Get comment media error:', error);
    res.status(500).json({ error: 'Failed to get comment media' });
  }
};

// Get training videos for a user
export const getUserTrainingVideos = async (req: Request, res: Response) => {
  try {
    const userId = req.user?.userId;
    const { exerciseType } = req.query;

    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const where: any = {
      userId,
      usage: 'training',
    };

    if (exerciseType) {
      where.exerciseType = exerciseType as string;
    }

    const media = await prisma.media.findMany({
      where,
      orderBy: { createdAt: 'desc' },
    });

    res.json(media);
  } catch (error) {
    console.error('Get training videos error:', error);
    res.status(500).json({ error: 'Failed to get training videos' });
  }
};
