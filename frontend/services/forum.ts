import { API_BASE_URL } from '../config/api';

interface ForumPost {
  id: string;
  userId: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
  likes: number;
  user: {
    username: string;
  };
  comments?: Comment[];
}

interface Comment {
  id: string;
  postId: string;
  userId: string;
  content: string;
  createdAt: string;
  user: {
    username: string;
  };
}

export const forumAPI = {
  async getAllPosts(): Promise<ForumPost[]> {
    const response = await fetch(`${API_BASE_URL}/forum`);
    if (!response.ok) throw new Error('Failed to fetch posts');
    const data = await response.json();
    // Handle paginated response
    return data.posts || data;
  },

  async getPostById(id: string): Promise<ForumPost> {
    const response = await fetch(`${API_BASE_URL}/forum/${id}`);
    if (!response.ok) throw new Error('Failed to fetch post');
    return response.json();
  },

  async createPost(token: string, data: { title: string; content: string }): Promise<ForumPost> {
    const response = await fetch(`${API_BASE_URL}/forum`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to create post');
    return response.json();
  },

  async addComment(token: string, postId: string, data: { content: string }): Promise<Comment> {
    const response = await fetch(`${API_BASE_URL}/forum/${postId}/comments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('Add comment error:', errorData);
      throw new Error(errorData.error || 'Failed to add comment');
    }
    return response.json();
  },

  async getPostComments(postId: string): Promise<Comment[]> {
    const response = await fetch(`${API_BASE_URL}/forum/${postId}/comments`);
    if (!response.ok) throw new Error('Failed to fetch comments');
    return response.json();
  },

  async likePost(token: string, postId: string) {
    const response = await fetch(`${API_BASE_URL}/forum/${postId}/like`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to like post');
    return response.json();
  },
};
