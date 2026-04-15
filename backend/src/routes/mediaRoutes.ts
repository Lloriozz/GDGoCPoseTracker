import { Router } from 'express';
import {
  uploadImage,
  uploadVideo,
  getMediaById,
  deleteMedia,
  getPostMedia,
  getCommentMedia,
  getUserTrainingVideos,
} from '../controllers/mediaController';
import { authenticate } from '../utils/auth';
import multer from 'multer';

// Configure multer for video uploads (still using file upload for videos)
const upload = multer({
  dest: 'uploads/',
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB limit for videos
  },
  fileFilter: (req, file, cb) => {
    // Allow all file types for now
    cb(null, true);
  },
});

const router = Router();

// Protected routes
router.post('/image', authenticate, uploadImage); // No multer for base64 image uploads
router.post('/video', authenticate, upload.single('file'), uploadVideo);
router.get('/user/training', authenticate, getUserTrainingVideos);

// Public routes - specific routes first to avoid conflicts
router.get('/post/:postId', getPostMedia);
router.get('/comment/:commentId', getCommentMedia);
router.get('/:id', getMediaById);

// Protected routes
router.delete('/:id', authenticate, deleteMedia);

export default router;
