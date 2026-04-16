import React, { useEffect, useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  Image, 
  TextInput, 
  TouchableOpacity, 
  FlatList,
  Platform,
  ActivityIndicator,
  Alert,
  Modal
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as ImagePicker from 'expo-image-picker';
import { forumAPI } from '../../services/forum';
import { mediaAPI } from '../../services/media';
import { useAuth } from '../../contexts/AuthContext';
import { API_BASE_URL } from '../../config/api';

const PRIMARY = '#FF7A22';

export default function ForumScreen() {
  const [posts, setPosts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { token, user } = useAuth();
  const [newPostTitle, setNewPostTitle] = useState('');
  const [newPostContent, setNewPostContent] = useState('');
  const [showCreatePost, setShowCreatePost] = useState(false);
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
    fetchPosts();
  }, []);

  const fetchPosts = async () => {
    try {
      console.log('Fetching posts from:', API_BASE_URL);
      const data = await forumAPI.getAllPosts();
      console.log('Posts fetched:', data);
      setPosts(data);
    } catch (error: any) {
      console.error('Failed to fetch posts:', error);
      console.error('Error message:', error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreatePost = async () => {
    if (!token) {
      Alert.alert('Login Required', 'Please login to create a post');
      return;
    }

    if (!newPostTitle.trim() || !newPostContent.trim()) {
      Alert.alert('Error', 'Please fill in both title and content');
      return;
    }

    setIsUploading(true);
    try {
      // Create post first
      const response: any = await forumAPI.createPost(token, {
        title: newPostTitle,
        content: newPostContent,
      });
      const newPost = response.post || response;

      // Upload all images with postId if selected
      if (selectedImages.length > 0) {
        for (const image of selectedImages) {
          await mediaAPI.uploadImage(token, image, 'post', newPost.id);
        }
      }

      // Refresh posts to get the updated data with media
      await fetchPosts();
      
      setNewPostTitle('');
      setNewPostContent('');
      setSelectedImages([]);
      setShowCreatePost(false);
    } catch (error: any) {
      console.error('Failed to create post:', error);
      Alert.alert('Error', 'Failed to create post');
    } finally {
      setIsUploading(false);
    }
  };

  const renderHeader = () => (
    <View style={styles.headerContainer}>
      {/* Top Bell Icon */}
      <View style={styles.headerTop}>
        <TouchableOpacity style={styles.bellIcon} activeOpacity={0.8}>
          <Ionicons name="notifications" size={34} color={PRIMARY} />
          <View style={styles.badge}>
            <Text style={styles.badgeText}>1</Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* Input Section */}
      <View style={styles.createPostContainer}>
        <View style={styles.postAvatar}>
          <Text style={styles.avatarText}>{user?.username?.[0] || 'U'}</Text>
        </View>
        <TouchableOpacity 
          style={styles.inputContainer}
          onPress={() => {
            if (!token) {
              Alert.alert('Login Required', 'Please login to create a post');
            } else {
              setShowCreatePost(true);
            }
          }}
          activeOpacity={0.7}
        >
          <Text style={styles.inputPlaceholder}>What are you thinking?</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderPost = ({ item }: { item: any }) => (
    <View key={item.id} style={styles.postRow}>
      {/* Left Column (Avatar) */}
      <View style={styles.postAvatar}>
        <Text style={styles.avatarText}>{item.user?.username?.[0] || 'U'}</Text>
      </View>

      {/* Right Column (Content) */}
      <View style={styles.postContentRight}>
        {/* Name & Handle */}
        <View style={styles.authorHeader}>
          <Text style={styles.authorName}>{item.user?.username || 'Anonymous'}</Text>
        </View>
        
        {/* Post Text */}
        <Text style={styles.postText}>{item.content}</Text>

        {/* Post Images */}
        {item.media && item.media.length > 0 && (
          <View style={styles.postImagesRow}>
            {item.media.map((media: any, index: number) => (
              <Image
                key={media.id || index}
                source={{ uri: media.url }}
                style={styles.postImage}
              />
            ))}
          </View>
        )}

        {/* Stats / Action Bar */}
        <View style={styles.statsContainer}>
          <TouchableOpacity 
            key="comments" 
            style={styles.statItem} 
            activeOpacity={0.7}
            onPress={() => router.push(`/post/${item.id}` as any)}
          >
            <Ionicons name="chatbubble-outline" size={22} color="#000" />
            <Text style={styles.statText}>{item.comments?.length || 0}</Text>
          </TouchableOpacity>
          <TouchableOpacity key="likes" style={styles.statItem} activeOpacity={0.7}>
            <Ionicons name="heart-outline" size={24} color="#000" />
            <Text style={styles.statText}>{item.likes || 0}</Text>
          </TouchableOpacity>
        </View>
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
      <FlatList
        data={posts}
        keyExtractor={(item, index) => item.id || `post-${index}`}
        renderItem={renderPost}
        ListHeaderComponent={renderHeader}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={{ paddingBottom: 100 }}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No posts yet</Text>
          </View>
        }
      />

      {/* Create Post Modal */}
      <Modal visible={showCreatePost} animationType="slide">
        <SafeAreaView style={styles.modalSafe}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <TouchableOpacity onPress={() => setShowCreatePost(false)}>
                <Text style={styles.modalCancel}>Cancel</Text>
              </TouchableOpacity>
              <Text style={styles.modalTitle}>Create Post</Text>
              <TouchableOpacity onPress={handleCreatePost}>
                <Text style={styles.modalPost}>Post</Text>
              </TouchableOpacity>
            </View>

            <TextInput
              style={styles.titleInput}
              placeholder="Title"
              placeholderTextColor="#888"
              value={newPostTitle}
              onChangeText={setNewPostTitle}
            />

            <TextInput
              style={styles.contentInput}
              placeholder="What's on your mind?"
              placeholderTextColor="#888"
              value={newPostContent}
              onChangeText={setNewPostContent}
              multiline
              numberOfLines={6}
              textAlignVertical="top"
            />

            {selectedImages.length > 0 && (
              <View style={styles.imagePreviewContainer}>
                <View style={styles.imagePreviewRow}>
                  {selectedImages.map((image, index) => (
                    <View key={index} style={styles.imagePreviewWrapper}>
                      <Image source={{ uri: image.uri }} style={styles.imagePreview} />
                      <TouchableOpacity
                        style={styles.removeImageButton}
                        onPress={() => setSelectedImages(selectedImages.filter((_, i) => i !== index))}
                      >
                        <Ionicons name="close-circle" size={20} color="#fff" />
                      </TouchableOpacity>
                    </View>
                  ))}
                </View>
              </View>
            )}

            <TouchableOpacity style={styles.addImageButton} onPress={pickImage}>
              <Ionicons name="image-outline" size={20} color="#666" />
              <Text style={styles.addImageText}>{selectedImages.length > 0 ? 'Add More Images' : 'Add Image'}</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: '#fff',
  },
  headerContainer: {
    marginBottom: 8,
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 10,
  },
  bellIcon: {
    position: 'relative',
  },
  badge: {
    position: 'absolute',
    top: -2,
    right: -4,
    backgroundColor: '#fff',
    borderRadius: 10,
    width: 18,
    height: 18,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: '#e0e0e0',
  },
  badgeText: {
    fontSize: 10,
    fontWeight: '800',
    color: '#000',
  },
  createPostContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#eee',
    paddingBottom: 30, // give some breathing room
  },
  myAvatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    marginRight: 16,
  },
  inputContainer: {
    flex: 1,
    backgroundColor: '#F5F6F8',
    borderRadius: 24,
    paddingHorizontal: 18,
    paddingVertical: 14,
  },
  input: {
    fontSize: 16,
    color: '#111',
    fontWeight: '500',
  },
  inputPlaceholder: {
    fontSize: 16,
    color: '#666',
    fontWeight: '500',
  },
  postRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 20,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#ddd',
  },
  postAvatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    marginRight: 12,
    backgroundColor: '#FF7A22',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
  },
  postContentRight: {
    flex: 1,
  },
  authorHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  authorName: {
    fontWeight: '700',
    fontSize: 16,
    color: '#000',
    marginRight: 6,
  },
  authorHandle: {
    fontSize: 15,
    color: '#555',
  },
  postText: {
    fontSize: 16,
    color: '#111',
    lineHeight: 22,
    fontWeight: '500',
  },
  postTags: {
    fontSize: 15,
    color: '#4DA2FF',
    marginTop: 4,
    marginBottom: 12,
    fontWeight: '500',
  },
  postImagesRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 16,
  },
  postImage: {
    flex: 1,
    height: 280,
    borderRadius: 16,
    backgroundColor: '#f0f0f0',
  },
  statsContainer: {
    flexDirection: 'row',
    gap: 40,
    alignItems: 'center',
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#000',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 16,
    color: '#666',
  },
  modalSafe: {
    flex: 1,
    backgroundColor: '#fff',
  },
  modalContent: {
    flex: 1,
    padding: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  modalCancel: {
    fontSize: 16,
    color: '#666',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111',
  },
  modalPost: {
    fontSize: 16,
    color: '#FF7A22',
    fontWeight: '700',
  },
  titleInput: {
    backgroundColor: '#F7F8FA',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    marginBottom: 16,
    color: '#111',
    fontWeight: '600',
  },
  contentInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    minHeight: 120,
    marginBottom: 16,
  },
  imagePreviewContainer: {
    position: 'relative',
    marginBottom: 16,
  },
  imagePreviewRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  imagePreviewWrapper: {
    position: 'relative',
  },
  imagePreview: {
    width: 100,
    height: 100,
    borderRadius: 8,
  },
  removeImageButton: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 12,
    padding: 4,
  },
  addImageButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
  },
  addImageText: {
    fontSize: 16,
    color: '#666',
  },
});
