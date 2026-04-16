import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  Image, 
  TextInput, 
  TouchableOpacity, 
  FlatList,
  KeyboardAvoidingView,
  Platform
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { PlaceholderScreen } from '@/components/shared/PlaceholderScreen';

const PRIMARY = '#FF7A22';

const MOCK_MESSAGES = [
  {
    id: "1",
    text: "Hey! How did your morning cardio session go today?",
    sender: "trainer",
    time: "09:00 AM",
  },
  {
    id: "2",
    text: "I literally just finished it! Crushed the 3-minute blast without stopping! 🏃‍♂️💨",
    sender: "user",
    time: "09:32 AM",
  },
  {
    id: "3",
    text: "That's exactly what I like to hear! 🔥",
    sender: "trainer",
    time: "09:35 AM",
  },
  {
    id: "4",
    text: "You're building great endurance. Make sure you hydrate and get some protein in right now.",
    sender: "trainer",
    time: "09:35 AM",
  },
  {
    id: "5",
    text: "Will do. Are we still on for the strength training assessment on Thursday?",
    sender: "user",
    time: "09:40 AM",
  },
  {
    id: "6",
    text: "Yes! Thursday at 4 PM. Be ready to push some weight.",
    sender: "trainer",
    time: "09:42 AM",
  }
];

export default function ChatScreen() {
  const [messages, setMessages] = useState(MOCK_MESSAGES);
  const [inputText, setInputText] = useState('');

  const renderHeader = () => (
    <View style={styles.headerContainer}>
      <View style={styles.headerLeft}>
        <Image source={require('../../assets/ava-women.jpg')} style={styles.headerAvatar} />
        <View>
          <Text style={styles.headerName}>Coach Alice</Text>
          <Text style={styles.headerStatus}>Online</Text>
        </View>
      </View>
      <View style={styles.headerRight}>
        <TouchableOpacity style={styles.iconBtn}>
          <Ionicons name="call-outline" size={24} color="#111" />
        </TouchableOpacity>
        <TouchableOpacity style={styles.iconBtn}>
          <Ionicons name="videocam-outline" size={26} color="#111" />
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderMessage = ({ item }: { item: typeof MOCK_MESSAGES[0] }) => {
    const isUser = item.sender === 'user';
    return (
      <View style={[styles.messageWrapper, isUser ? styles.messageWrapperUser : styles.messageWrapperTrainer]}>
        {!isUser && (
          <Image source={require('../../assets/ava-women.jpg')} style={styles.messageAvatar} />
        )}
        <View style={styles.messageContent}>
          <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleTrainer]}>
            <Text style={[styles.messageText, isUser ? styles.messageTextUser : styles.messageTextTrainer]}>
              {item.text}
            </Text>
          </View>
          <Text style={[styles.timeText, isUser && { alignSelf: 'flex-end' }]}>{item.time}</Text>
        </View>
      </View>
    );
  };

  const sendMessage = () => {
    if (inputText.trim()) {
      const newMessage = {
        id: Date.now().toString(),
        text: inputText,
        sender: "user",
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages([...messages, newMessage]);
      setInputText('');
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView 
        style={styles.container} 
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {renderHeader()}
        
        <FlatList
          data={messages}
          keyExtractor={item => item.id}
          renderItem={renderMessage}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
        />

        {/* Input Area */}
        <View style={styles.inputWrapper}>
          <TextInput 
            style={styles.textInput}
            placeholder="Type a message..."
            placeholderTextColor="#999"
            value={inputText}
            onChangeText={setInputText}
            multiline
          />
          {inputText.trim().length > 0 ? (
            <TouchableOpacity style={styles.sendBtn} onPress={sendMessage}>
              <Ionicons name="send" size={16} color="#fff" style={{marginLeft: 4, marginTop: 2}} />
            </TouchableOpacity>
          ) : (
             <TouchableOpacity style={styles.iconBtnSm}>
                <Ionicons name="camera-outline" size={26} color="#888" />
             </TouchableOpacity>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: '#fff',
  },
  container: {
    flex: 1,
    backgroundColor: '#F8F9FA',
  },
  headerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#ebebeb',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    marginRight: 12,
  },
  headerName: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111',
  },
  headerStatus: {
    fontSize: 13,
    color: '#4ADE80',
    fontWeight: '600',
    marginTop: 2,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconBtn: {
    padding: 8,
  },
  listContent: {
    padding: 16,
    paddingBottom: 20,
  },
  messageWrapper: {
    flexDirection: 'row',
    marginBottom: 20,
    alignItems: 'flex-end',
  },
  messageWrapperUser: {
    justifyContent: 'flex-end',
  },
  messageWrapperTrainer: {
    justifyContent: 'flex-start',
  },
  messageAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    marginRight: 8,
  },
  messageContent: {
    maxWidth: '75%',
  },
  bubble: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
    marginBottom: 4,
  },
  bubbleTrainer: {
    backgroundColor: '#fff',
    borderBottomLeftRadius: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  bubbleUser: {
    backgroundColor: PRIMARY,
    borderBottomRightRadius: 4,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 22,
  },
  messageTextTrainer: {
    color: '#111',
  },
  messageTextUser: {
    color: '#fff',
  },
  timeText: {
    fontSize: 11,
    color: '#aaa',
    marginTop: 2,
    marginHorizontal: 4,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#fff',
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#ebebeb',
    paddingBottom: Platform.OS === 'ios' ? 24 : 10,
  },
  attachBtn: {
    padding: 8,
    marginRight: 4,
  },
  iconBtnSm: {
    padding: 8,
    marginLeft: 6,
  },
  textInput: {
    flex: 1,
    backgroundColor: '#F3F4F6',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 12,
    fontSize: 16,
    color: '#111',
    maxHeight: 100,
  },
  sendBtn: {
    backgroundColor: PRIMARY,
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 10,
    shadowColor: PRIMARY,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  }
});