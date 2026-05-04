import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  TextInput, 
  TouchableOpacity, 
  FlatList, 
  Alert,
  SafeAreaView,
  StatusBar
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// 配置
const CONFIG = {
  // 茶信服务器地址（根据实际部署修改）
  SERVER_URL: 'http://192.168.1.17:8080',
  API_KEY: '8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii',
  NODE_ID: 'phone', // 手机节点ID
};

// 已注册的智能体
const AGENTS = [
  { id: 'xiaozhi', name: '小龙虾', emoji: '🦞' },
  { id: 'hongcha', name: '红茶', emoji: '🍵' },
  { id: 'laok', name: '老K', emoji: '📊' },
  { id: 'ali', name: '阿狸', emoji: '🦊' },
  { id: 'xinxin', name: '小信', emoji: '📡' },
  { id: 'laohei', name: '老黑', emoji: '🔧' },
];

// 主界面
export default function App() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0]);
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    loadMessages();
    checkConnection();
  }, []);

  // 加载历史消息
  const loadMessages = async () => {
    try {
      const saved = await AsyncStorage.getItem('messages');
      if (saved) {
        setMessages(JSON.parse(saved));
      }
    } catch (e) {
      console.error('加载消息失败', e);
    }
  };

  // 保存消息
  const saveMessages = async (msgs) => {
    try {
      await AsyncStorage.setItem('messages', JSON.stringify(msgs));
    } catch (e) {
      console.error('保存消息失败', e);
    }
  };

  // 检查连接
  const checkConnection = async () => {
    try {
      const response = await fetch(`${CONFIG.SERVER_URL}/health`, {
        method: 'GET',
        headers: {
          'X-API-Key': CONFIG.API_KEY,
        },
      });
      const data = await response.json();
      setConnected(data.status === 'ok' || data.code === 200);
    } catch (e) {
      setConnected(false);
    }
  };

  // 发送消息
  const sendMessage = async () => {
    if (!inputText.trim()) {
      Alert.alert('提示', '请输入消息内容');
      return;
    }

    if (!connected) {
      Alert.alert('提示', '未连接到服务器，请检查网络');
      return;
    }

    setLoading(true);
    const newMessage = {
      id: Date.now().toString(),
      from: 'phone',
      to: selectedAgent.id,
      subject: inputText.substring(0, 50),
      body: inputText,
      timestamp: new Date().toISOString(),
      sent: false,
    };

    try {
      // 发送消息
      const response = await fetch(`${CONFIG.SERVER_URL}/msg/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': CONFIG.API_KEY,
        },
        body: JSON.stringify({
          from: CONFIG.NODE_ID,
          to: selectedAgent.id,
          subject: inputText.substring(0, 50),
          body: inputText,
          timestamp: new Date().toISOString(),
        }),
      });

      const result = await response.json();
      
      if (result.status === 'sent' || result.code === 200) {
        newMessage.sent = true;
        
        // 等待回复
        setTimeout(() => {
          fetchReply(selectedAgent.id);
        }, 3000);
      } else {
        newMessage.sent = false;
        Alert.alert('发送失败', result.message || '请检查网络');
      }
    } catch (e) {
      newMessage.sent = false;
      Alert.alert('发送失败', e.message);
    }

    const updatedMessages = [newMessage, ...messages];
    setMessages(updatedMessages);
    saveMessages(updatedMessages);
    setInputText('');
    setLoading(false);
  };

  // 获取回复
  const fetchReply = async (agentId) => {
    try {
      const response = await fetch(
        `${CONFIG.SERVER_URL}/msg/list?key=${CONFIG.API_KEY}&to=${CONFIG.NODE_ID}&limit=5`,
        {
          method: 'GET',
          headers: {
            'X-API-Key': CONFIG.API_KEY,
          },
        }
      );
      const data = await response.json();
      
      if (data.messages && data.messages.length > 0) {
        // 找到最新回复
        const replies = data.messages
          .filter(m => m.from === agentId)
          .map(m => ({
            id: m.id.toString(),
            from: m.from,
            to: 'phone',
            subject: m.subject,
            body: m.body,
            timestamp: m.timestamp,
            sent: true,
            isReply: true,
          }));

        if (replies.length > 0) {
          const newMessages = [...replies, ...messages];
          // 去重
          const uniqueMessages = newMessages.filter((msg, index, self) =>
            index === self.findIndex(m => m.id === msg.id)
          );
          setMessages(uniqueMessages);
          saveMessages(uniqueMessages);
        }
      }
    } catch (e) {
      console.error('获取回复失败', e);
    }
  };

  // 刷新消息
  const refreshMessages = () => {
    fetchReply(selectedAgent.id);
    checkConnection();
  };

  // 渲染消息项
  const renderMessage = ({ item }) => (
    <View style={[
      styles.messageItem,
      item.isReply ? styles.replyMessage : styles.sentMessage
    ]}>
      <View style={styles.messageHeader}>
        <Text style={styles.senderName}>
          {item.isReply ? AGENTS.find(a => a.id === item.from)?.name || item.from : '我'}
        </Text>
        <Text style={styles.timestamp}>
          {new Date(item.timestamp).toLocaleTimeString()}
        </Text>
      </View>
      <Text style={styles.messageBody}>{item.body}</Text>
      <Text style={styles.messageStatus}>
        {item.sent ? '✓ 已发送' : '⏳ 发送中...'}
      </Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      
      {/* 标题栏 */}
      <View style={styles.header}>
        <Text style={styles.title}>茶信 🍵</Text>
        <View style={styles.statusContainer}>
          <View style={[styles.statusDot, { backgroundColor: connected ? '#4CAF50' : '#f44336' }]} />
          <Text style={styles.statusText}>{connected ? '已连接' : '离线'}</Text>
        </View>
      </View>

      {/* 智能体选择 */}
      <View style={styles.agentSelector}>
        <Text style={styles.selectorLabel}>发送给：</Text>
        <FlatList
          data={AGENTS}
          horizontal
          showsHorizontalScrollIndicator={false}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[
                styles.agentButton,
                selectedAgent.id === item.id && styles.agentButtonActive
              ]}
              onPress={() => setSelectedAgent(item)}
            >
              <Text style={styles.agentEmoji}>{item.emoji}</Text>
              <Text style={[
                styles.agentName,
                selectedAgent.id === item.id && styles.agentNameActive
              ]}>{item.name}</Text>
            </TouchableOpacity>
          )}
        />
      </View>

      {/* 消息列表 */}
      <FlatList
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        style={styles.messageList}
        refreshing={loading}
        onRefresh={refreshMessages}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>暂无消息</Text>
            <Text style={styles.emptySubtext}>发送消息开始对话</Text>
          </View>
        }
      />

      {/* 输入区域 */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          value={inputText}
          onChangeText={setInputText}
          placeholder="输入消息..."
          placeholderTextColor="#999"
          multiline
          maxLength={5000}
        />
        <TouchableOpacity 
          style={[styles.sendButton, !inputText.trim() && styles.sendButtonDisabled]}
          onPress={sendMessage}
          disabled={!inputText.trim() || loading}
        >
          <Text style={styles.sendButtonText}>
            {loading ? '发送中...' : '发送'}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

// 样式
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 4,
  },
  statusText: {
    fontSize: 12,
    color: '#666',
  },
  agentSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  selectorLabel: {
    fontSize: 14,
    color: '#666',
    marginRight: 8,
  },
  agentButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    paddingHorizontal: 12,
    marginRight: 8,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
  },
  agentButtonActive: {
    backgroundColor: '#4CAF50',
  },
  agentEmoji: {
    fontSize: 16,
    marginRight: 4,
  },
  agentName: {
    fontSize: 14,
    color: '#666',
  },
  agentNameActive: {
    color: '#fff',
    fontWeight: 'bold',
  },
  messageList: {
    flex: 1,
    padding: 8,
  },
  messageItem: {
    padding: 12,
    marginVertical: 4,
    borderRadius: 12,
    maxWidth: '85%',
  },
  sentMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#E3F2FD',
  },
  replyMessage: {
    alignSelf: 'flex-start',
    backgroundColor: '#fff',
  },
  messageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  senderName: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#333',
  },
  timestamp: {
    fontSize: 10,
    color: '#999',
  },
  messageBody: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
  },
  messageStatus: {
    fontSize: 10,
    color: '#999',
    marginTop: 4,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
  },
  emptySubtext: {
    fontSize: 12,
    color: '#ccc',
    marginTop: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 8,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    fontSize: 16,
    maxHeight: 100,
  },
  sendButton: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    marginLeft: 8,
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#ccc',
  },
  sendButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
});