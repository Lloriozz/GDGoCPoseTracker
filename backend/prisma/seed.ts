import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

/// <reference types="node" />

const prisma = new PrismaClient();

async function main() {
  console.log('Starting seed...');

  // Create users
  const passwordHash = await bcrypt.hash('password123', 10);
  
  const users = [
    {
      email: 'david@example.com',
      username: 'david_laid',
      passwordHash,
      firstName: 'David',
      lastName: 'Laid'
    },
    {
      email: 'alice@example.com',
      username: 'alice_fitness',
      passwordHash,
      firstName: 'Alice',
      lastName: 'Burberry'
    },
    {
      email: 'john@example.com',
      username: 'john_fit',
      passwordHash,
      firstName: 'John',
      lastName: 'Doe'
    }
  ];

  const createdUsers = [];
  for (const user of users) {
    const createdUser = await prisma.user.upsert({
      where: { email: user.email },
      update: {},
      create: user
    });
    createdUsers.push(createdUser);
  }

  // Create exercises
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

  // Create forum posts
  const forumPosts = [
    {
      userId: createdUsers[0].id,
      title: 'Morning Workout Routine',
      content: 'Just finished an amazing morning workout! Started with 30 minutes of cardio, followed by strength training. Feeling energized and ready to take on the day. #fitness #morningroutine',
      likes: 15
    },
    {
      userId: createdUsers[1].id,
      title: 'New PR on Squats!',
      content: 'Finally hit my personal record on squats today - 225 lbs for 5 reps! Been working towards this goal for months. Consistency really pays off. 💪',
      likes: 32
    },
    {
      userId: createdUsers[2].id,
      title: 'Need advice on form',
      content: 'Been struggling with my deadlift form lately. Any tips on keeping my back straight? I feel like I might be rounding too much.',
      likes: 8
    },
    {
      userId: createdUsers[0].id,
      title: 'Best supplements for beginners?',
      content: 'Just starting my fitness journey and wondering what supplements you guys recommend. Currently just taking protein powder after workouts.',
      likes: 12
    },
    {
      userId: createdUsers[1].id,
      title: 'Weekend hiking plans',
      content: 'Planning a hike this weekend! Anyone have recommendations for good trails in the area? Looking for something moderate difficulty with nice views.',
      likes: 5
    }
  ];

  const createdPosts = [];
  for (const post of forumPosts) {
    const createdPost = await prisma.forumPost.create({
      data: post
    });
    createdPosts.push(createdPost);
  }

  // Create forum comments
  const comments = [
    {
      userId: createdUsers[1].id,
      postId: createdPosts[2].id,
      content: 'Focus on engaging your lats and keeping your core tight. Record yourself from the side to check your form!'
    },
    {
      userId: createdUsers[2].id,
      postId: createdPosts[2].id,
      content: 'Definitely start with lighter weight to perfect form. Hip hinges are key!'
    },
    {
      userId: createdUsers[2].id,
      postId: createdPosts[0].id,
      content: 'Great job! Morning workouts are the best way to start the day.'
    },
    {
      userId: createdUsers[0].id,
      postId: createdPosts[1].id,
      content: 'Congratulations! Thats amazing progress. Keep pushing!'
    },
    {
      userId: createdUsers[2].id,
      postId: createdPosts[4].id,
      content: 'Check out the trails at Mountain Park - great views and moderate difficulty.'
    }
  ];

  for (const comment of comments) {
    await prisma.forumComment.create({
      data: comment
    });
  }

  console.log('Seed completed successfully!');
  console.log(`Created ${createdUsers.length} users`);
  console.log(`Created ${forumPosts.length} forum posts`);
  console.log(`Created ${comments.length} comments`);
}

main()
  .catch((e) => {
    console.error(e);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
