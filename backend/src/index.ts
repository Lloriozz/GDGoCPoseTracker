import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import authRoutes from './routes/authRoutes';
import workoutRoutes from './routes/workoutRoutes';
import forumRoutes from './routes/forumRoutes';
import mediaRoutes from './routes/mediaRoutes';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'PoseTracker Backend is running' });
});

// API routes
app.use('/api/auth', authRoutes);
app.use('/api/workouts', workoutRoutes);
app.use('/api/forum', forumRoutes);
app.use('/api/media', mediaRoutes);

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port http://localhost:${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV}`);
});
