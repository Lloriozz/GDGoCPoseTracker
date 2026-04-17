import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

/// <reference types="node" />

const prisma = new PrismaClient();

async function main() {
  console.log('Starting seed...');

  // Seed exercises (required for workout functionality)
  const exercises = [
    {
      name: 'Bicep Curl',
      type: 'bicep_curl',
      description: 'Bicep curl exercise for arm strength',
      difficulty: 'beginner',
      duration: 180
    },
    {
      name: 'Squat',
      type: 'squat',
      description: 'Squat exercise for leg strength',
      difficulty: 'beginner',
      duration: 240
    },
    {
      name: 'Plank',
      type: 'plank',
      description: 'Plank exercise for core strength',
      difficulty: 'intermediate',
      duration: 120
    },
    {
      name: 'Lunge',
      type: 'lunge',
      description: 'Lunge exercise for leg strength',
      difficulty: 'intermediate',
      duration: 200
    }
  ];

  for (const exercise of exercises) {
    await prisma.exercise.upsert({
      where: { name: exercise.name },
      update: {},
      create: exercise
    });
  }

  // Seed admin user (for system administration)
  const passwordHash = await bcrypt.hash('admin123', 10);
  const adminUser = await prisma.userProfile.upsert({
    where: { email: 'admin@posetracker.com' },
    update: {},
    create: {
      email: 'admin@posetracker.com',
      username: 'admin',
      passwordHash,
      firstName: 'System',
      lastName: 'Admin'
    }
  });

  // Seed sample workout for admin user
  const bicepCurl = await prisma.exercise.findUnique({ where: { name: 'Bicep Curl' } });
  if (bicepCurl) {
    await prisma.workout.upsert({
      where: { id: 'sample-workout-id' },
      update: {},
      create: {
        id: 'sample-workout-id',
        userId: adminUser.id,
        exerciseId: bicepCurl.id,
        duration: 180,
        completed: true,
        score: 85.5,
        startedAt: new Date(),
        completedAt: new Date()
      }
    });
  }

  // Seed sample forum post
  await prisma.forumPost.upsert({
    where: { id: 'welcome-post-id' },
    update: {},
    create: {
      id: 'welcome-post-id',
      userId: adminUser.id,
      title: 'Welcome to PoseTracker Community',
      content: 'Welcome to our fitness community! Share your workout progress and connect with other fitness enthusiasts.',
      likes: 0
    }
  });

  // Seed sample media reference
  await prisma.media.upsert({
    where: { id: 'sample-media-id' },
    update: {},
    create: {
      id: 'sample-media-id',
      userId: adminUser.id,
      type: 'video',
      usage: 'training',
      url: 'https://example.com/sample-video.mp4',
      mimeType: 'video/mp4',
      exerciseType: 'bicep_curl'
    }
  });

  // Seed sample pose vector
  await prisma.poseVector.upsert({
    where: { id: 'sample-pose-vector-id' },
    update: {},
    create: {
      id: 'sample-pose-vector-id',
      userId: adminUser.id,
      exerciseType: 'bicep_curl',
      vectorData: JSON.stringify([0.1, 0.2, 0.3, 0.4])
    }
  });

  console.log('Seed completed successfully!');
  console.log(`Created ${exercises.length} exercises`);
  console.log('Created admin user');
  console.log('Created sample workout, forum post, media, and pose vector');
}

main()
  .catch((e) => {
    console.error(e);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
