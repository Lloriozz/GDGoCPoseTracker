import { Router } from 'express';
import {
  getAllPosts,
  getPostById,
  createPost,
  addComment,
  getPostComments,
  likePost
} from '../controllers/forumController';
import { authenticate } from '../utils/auth';

const router = Router();

// Public routes
router.get('/', getAllPosts);
router.get('/:id', getPostById);
router.get('/:id/comments', getPostComments);

// Protected routes
router.post('/', authenticate, createPost);
router.post('/:id/comments', authenticate, addComment);
router.post('/:id/like', authenticate, likePost);

export default router;
