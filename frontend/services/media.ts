import { API_BASE_URL } from '../config/api';

export const mediaAPI = {
  async uploadImage(
    token: string,
    file: any,
    usage: 'post' | 'comment' = 'post',
    postId?: string,
    commentId?: string
  ) {
    // Convert file to base64 using fetch
    const response = await fetch(file.uri);
    const blob = await response.blob();
    const reader = new FileReader();
    
    const base64 = await new Promise((resolve, reject) => {
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });

    const uploadResponse = await fetch(`${API_BASE_URL}/media/image`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        image: base64,
        usage,
        postId,
        commentId,
      }),
    });

    if (!uploadResponse.ok) {
      const errorData = await uploadResponse.json().catch(() => ({}));
      console.error('Upload error:', errorData);
      throw new Error(errorData.error || 'Failed to upload image');
    }

    return uploadResponse.json();
  },

  async uploadVideo(
    token: string,
    file: any,
    usage: 'training' = 'training',
    exerciseType?: string
  ) {
    const formData = new FormData();
    formData.append('file', {
      uri: file.uri,
      type: file.type || 'video/mp4',
      name: file.fileName || 'video.mp4',
    } as any);
    formData.append('usage', usage);
    if (exerciseType) formData.append('exerciseType', exerciseType);

    const response = await fetch(`${API_BASE_URL}/media/video`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData as any,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('Upload error:', errorData);
      throw new Error(errorData.error || 'Failed to upload video');
    }

    return response.json();
  },

  async getPostMedia(postId: string) {
    const response = await fetch(`${API_BASE_URL}/media/post/${postId}`);
    if (!response.ok) throw new Error('Failed to get post media');
    return response.json();
  },

  async getCommentMedia(commentId: string) {
    const response = await fetch(`${API_BASE_URL}/media/comment/${commentId}`);
    if (!response.ok) throw new Error('Failed to get comment media');
    return response.json();
  },

  async getUserTrainingVideos(token: string, exerciseType?: string) {
    const url = exerciseType
      ? `${API_BASE_URL}/media/user/training?exerciseType=${exerciseType}`
      : `${API_BASE_URL}/media/user/training`;
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) throw new Error('Failed to get training videos');
    return response.json();
  },

  async deleteMedia(token: string, mediaId: string) {
    const response = await fetch(`${API_BASE_URL}/media/${mediaId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) throw new Error('Failed to delete media');
    return response.json();
  },
};
