import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { forumAPI } from '../../services/forum';
import { mediaAPI } from '../../services/media';
import { useAuth } from '../../contexts/AuthContext';

const PRIMARY = '#FF7A22';

export default function PostDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { token } = useAuth();
  
  const [post, setPost] = useState<any>(null);
  const [comments, setComments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [newComment, setNewComment] = useState('');
  const [selectedImages, setSelectedImages] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsMultipleSelection: true,
      allowsEditing: false,
      quality: 0.8,
    });

    if (!result.canceled) {
      setSelectedImages([...selectedImages, ...result.assets]);
    }
  };

  useEffect(() => {
    loadPost();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const loadPost = async () => {
    try {
      const postData = await forumAPI.getPostById(id);
      setPost(postData);
      setComments(postData.comments || []);
      
      const postComments = await forumAPI.getPostComments(id);
      setComments(postComments);
    } catch (error) {
      console.error('Failed to load post:', error);
      Alert.alert('Error', 'Failed to load post');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddComment = async () => {
    if (!token) {
      Alert.alert('Login Required', 'Please login to comment');
      return;
    }

    if (!newComment.trim()) {
      Alert.alert('Error', 'Please enter a comment');
      return;
    }

    setIsUploading(true);
    try {
      // Create comment first
      const response: any = await forumAPI.addComment(token, id, {
        content: newComment,
      });
      const comment = response.comment || response;

      // Upload all images with commentId if selected
      if (selectedImages.length > 0) {
        for (const image of selectedImages) {
          await mediaAPI.uploadImage(token, image, 'comment', undefined, comment.id);
        }
      }

      // Refresh comments to get the updated data with media
      const updatedPost = await forumAPI.getPostById(id);
      setComments(updatedPost.comments || []);
      
      setNewComment('');
      setSelectedImages([]);
    } catch (error) {
      console.error('Failed to add comment:', error);
      Alert.alert('Error', 'Failed to add comment');
    } finally {
      setIsUploading(false);
    }
  };

  const renderComment = ({ item }: { item: any }) => (
    <View style={styles.commentItem}>
      <View style={styles.commentAvatar}>
        <Text style={styles.commentAvatarText}>
          {item.user?.username?.[0] || 'U'}
        </Text>
      </View>
      <View style={styles.commentContent}>
        <Text style={styles.commentAuthor}>{item.user?.username || 'Anonymous'}</Text>
        <Text style={styles.commentText}>{item.content}</Text>
        {item.media && item.media.length > 0 && (
          <View style={styles.commentImagesContainer}>
            {item.media.map((media: any, index: number) => (
              <Image
                key={media.id || index}
                source={{ uri: media.url }}
                style={styles.commentImage}
              />
            ))}
          </View>
        )}
      </View>
    </View>
  );

  if (isLoading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={PRIMARY} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color="#000" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Post</Text>
        <View style={{ width: 24 }} />
      </View>

      <FlatList
        data={comments}
        renderItem={renderComment}
        keyExtractor={(item, index) => item.id || `comment-${index}`}
        ListHeaderComponent={
          <View style={styles.postDetail}>
            <View style={styles.postHeader}>
              <View style={styles.postAvatar}>
                <Text style={styles.avatarText}>
                  {post?.user?.username?.[0] || 'U'}
                </Text>
              </View>
              <View>
                <Text style={styles.authorName}>{post?.user?.username || 'Anonymous'}</Text>
                <Text style={styles.postDate}>
                  {new Date(post?.createdAt).toLocaleDateString()}
                </Text>
              </View>
            </View>
            <Text style={styles.postContent}>{post?.content}</Text>
            
            {/* Post Images */}
            {post?.media && post.media.length > 0 && (
              <View style={styles.postImagesContainer}>
                {post.media.map((media: any, index: number) => (
                  <Image
                    key={media.id || index}
                    source={{ uri: media.url }}
                    style={styles.postImage}
                  />
                ))}
              </View>
            )}
            
            <View style={styles.postStats}>
              <Text style={styles.statText}>{post?.likes || 0} likes</Text>
              <Text style={styles.statText}>{comments.length} comments</Text>
            </View>
          </View>
        }
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ paddingBottom: 80 }}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No comments yet</Text>
          </View>
        }
      />

      {/* Comment Input */}
      <View style={styles.commentInputContainer}>
        <View style={styles.commentInputWrapper}>
          <TextInput
            style={styles.commentInput}
            placeholder="Add a comment..."
            placeholderTextColor="#888"
            value={newComment}
            onChangeText={setNewComment}
            multiline
          />
          <TouchableOpacity style={styles.addImageIcon} onPress={pickImage}>
            <Ionicons name="image-outline" size={20} color="#666" />
          </TouchableOpacity>
        </View>

        {selectedImages.length > 0 && (
          <View style={styles.commentImagePreviewContainer}>
            <View style={styles.commentImagePreviewRow}>
              {selectedImages.map((image, index) => (
                <View key={index} style={styles.commentImagePreviewWrapper}>
                  <Image source={{ uri: image.uri }} style={styles.commentImagePreview} />
                  <TouchableOpacity
                    style={styles.commentRemoveImageButton}
                    onPress={() => setSelectedImages(selectedImages.filter((_, i) => i !== index))}
                  >
                    <Ionicons name="close-circle" size={16} color="#fff" />
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          </View>
        )}

        <TouchableOpacity
          style={styles.sendButton}
          onPress={handleAddComment}
          disabled={isUploading || !newComment.trim()}
        >
          {isUploading ? (
            <ActivityIndicator size={20} color="#fff" />
          ) : (
            <Ionicons name="send" size={20} color="#fff" />
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: '#fff',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  postDetail: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  postHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  postAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: PRIMARY,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  avatarText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  authorName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
  },
  postDate: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },
  postContent: {
    fontSize: 16,
    color: '#333',
    lineHeight: 22,
    marginBottom: 12,
  },
  postImagesContainer: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  postImage: {
    width: 100,
    height: 100,
    borderRadius: 8,
  },
  postStats: {
    flexDirection: 'row',
    gap: 16,
  },
  statText: {
    fontSize: 14,
    color: '#888',
  },
  commentImagesContainer: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 8,
  },
  commentImage: {
    width: 80,
    height: 80,
    borderRadius: 6,
  },
  commentItem: {
    flexDirection: 'row',
    padding: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#eee',
  },
  commentAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#E0E0E0',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  commentAvatarText: {
    color: '#666',
    fontSize: 14,
    fontWeight: '600',
  },
  commentContent: {
    flex: 1,
  },
  commentAuthor: {
    fontSize: 14,
    fontWeight: '600',
    color: '#000',
    marginBottom: 4,
  },
  commentText: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
  },
  emptyContainer: {
    padding: 40,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#888',
  },
  commentInputContainer: {
    flexDirection: 'column',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#eee',
    backgroundColor: '#fff',
    paddingBottom: 24,
  },
  commentInputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  commentInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginRight: 8,
    maxHeight: 100,
    fontSize: 14,
  },
  addImageIcon: {
    padding: 8,
  },
  commentImagePreviewContainer: {
    position: 'relative',
    marginBottom: 8,
  },
  commentImagePreviewRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  commentImagePreviewWrapper: {
    position: 'relative',
  },
  commentImagePreview: {
    width: 80,
    height: 80,
    borderRadius: 6,
  },
  commentRemoveImageButton: {
    position: 'absolute',
    top: -6,
    right: -6,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 10,
    padding: 3,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: PRIMARY,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
