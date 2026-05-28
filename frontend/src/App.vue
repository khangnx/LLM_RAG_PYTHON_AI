<template>
  <div class="app-wrapper">
    <div class="app-header">
      <h1>🤖 AI RAG Demo Dashboard</h1>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs" @tab-click="onTabClick">

      <!-- ==================== TAB 1: CHAT ==================== -->
      <el-tab-pane label="💬 Không gian Chat & Knowledge Base" name="chat">
        <el-container class="chat-layout">

          <!-- LEFT SIDEBAR: Session list (ChatGPT style) + Knowledge Base -->
          <el-aside width="280px" class="sidebar">

            <!-- Phần 1: Session Actions -->
            <div class="sidebar-sessions">
              <el-button
                type="primary"
                :icon="Plus"
                class="new-session-btn"
                @click="createNewSession"
                :loading="isCreatingSession"
              >
                + Cuộc trò chuyện mới
              </el-button>

              <div class="session-list" v-loading="isLoadingSessions">
                <div
                  v-for="session in sessions"
                  :key="session.id"
                  :class="['session-item', { 'is-active': session.id === activeSessionId }]"
                  @click="switchSession(session)"
                >
                  <el-icon size="13"><ChatRound /></el-icon>
                  <span class="session-title">{{ session.title }}</span>
                </div>
                <div v-if="sessions.length === 0 && !isLoadingSessions" class="no-sessions">
                  Chưa có cuộc trò chuyện nào
                </div>
              </div>
            </div>

            <el-divider />

            <!-- Phần 2: Knowledge Base -->
            <div class="sidebar-kb">
              <div class="sidebar-actions">
                <el-button type="success" :icon="Refresh" :loading="isIngesting" @click="handleIngest" class="full-width">
                  Đồng bộ hệ thống
                </el-button>
              </div>
              <p class="sidebar-section-title">📁 TÀI LIỆU HIỆN CÓ</p>
              <div v-loading="isLoadingFiles" class="file-list">
                <div v-if="files.length === 0 && !isLoadingFiles" class="no-files">Chưa có tài liệu nào</div>
                <div v-for="file in files" :key="file.name" class="file-item">
                  <el-icon :size="16" :color="getFileIconColor(file.name)">
                    <component :is="getFileIcon(file.name)" />
                  </el-icon>
                  <span class="file-name" :title="file.name">{{ file.name }}</span>
                </div>
              </div>
            </div>
          </el-aside>

          <!-- MAIN AREA: Chat -->
          <el-main class="main-area">
            <!-- Header session hiện tại -->
            <div class="chat-header" v-if="activeSessionTitle">
              <span>💬 {{ activeSessionTitle }}</span>
            </div>
            <div class="chat-header placeholder-header" v-else>
              <span>← Chọn hoặc tạo cuộc trò chuyện mới từ sidebar</span>
            </div>

            <!-- Khung tin nhắn -->
            <div class="chat-container" ref="chatContainerRef">
              <div v-for="msg in messages" :key="msg.id" :class="['message-wrapper', msg.sender === 'user' ? 'is-user' : 'is-ai']">
                <div class="message-bubble">
                  <div class="message-text">{{ msg.text }}</div>
                  <div v-if="msg.sources && msg.sources.length > 0" class="message-sources">
                    <el-collapse accordion>
                      <el-collapse-item title="📚 Nguồn trích dẫn" name="sources">
                        <div class="source-list">
                          <el-tag v-for="(source, idx) in msg.sources" :key="idx" size="small" type="info" class="source-tag">
                            {{ source.file }} — {{ source.location }}
                          </el-tag>
                        </div>
                      </el-collapse-item>
                    </el-collapse>
                  </div>
                </div>
              </div>
              <div v-if="isChatting" class="message-wrapper is-ai">
                <div class="message-bubble loading-bubble">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>AI đang phân tích dữ liệu...</span>
                </div>
              </div>
            </div>

            <!-- Input -->
            <div class="chat-input-area">
              <el-input
                v-model="chatInput"
                type="textarea"
                :rows="3"
                :placeholder="activeSessionId ? 'Nhập câu hỏi (Enter để gửi)...' : 'Vui lòng tạo hoặc chọn một cuộc trò chuyện trước'"
                resize="none"
                :disabled="!activeSessionId"
                @keydown.enter.exact.prevent="sendMessage"
              />
              <el-button type="primary" :icon="Promotion" circle size="large" class="send-btn"
                :disabled="!chatInput.trim() || isChatting || !activeSessionId" @click="sendMessage" />
            </div>
          </el-main>

        </el-container>
      </el-tab-pane>

      <!-- ==================== TAB 2: LỊCH SỬ ==================== -->
      <el-tab-pane label="📜 Lịch sử & Đối chiếu Prompt" name="history">
        <div class="history-wrapper">
          <div class="history-header">
            <h3>Lịch sử truy vấn AI</h3>
            <el-button :icon="Refresh" @click="fetchHistory" :loading="isLoadingHistory">Làm mới</el-button>
          </div>
          <el-table :data="historyList" v-loading="isLoadingHistory" stripe border style="width: 100%">
            <el-table-column prop="created_at" label="Thời gian" width="170" align="center" />
            <el-table-column prop="search_query" label="Câu hỏi" width="260">
              <template #default="scope"><span class="query-text">{{ scope.row.search_query }}</span></template>
            </el-table-column>
            <el-table-column prop="ai_response" label="Kết quả AI">
              <template #default="scope">
                <span class="response-preview">{{ scope.row.ai_response.substring(0, 150) }}{{ scope.row.ai_response.length > 150 ? '...' : '' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="Hành động" width="170" align="center">
              <template #default="scope">
                <el-button type="info" size="small" @click="openPromptDialog(scope.row)">🔍 Xem Prompt</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="historyList.length === 0 && !isLoadingHistory" description="Chưa có lịch sử chat nào." />
        </div>

        <el-dialog v-model="isDialogVisible" title="🧪 Chi tiết Prompt gửi đến AI" width="70%" :close-on-click-modal="true">
          <div class="dialog-meta" v-if="selectedHistory">
            <p><strong>🕐 Thời gian:</strong> {{ selectedHistory.created_at }}</p>
            <p><strong>❓ Câu hỏi:</strong> {{ selectedHistory.search_query }}</p>
          </div>
          <el-divider content-position="left">📋 Prompt hoàn chỉnh</el-divider>
          <pre class="prompt-display">{{ selectedHistory?.generated_prompt }}</pre>
          <template #footer>
            <el-button @click="isDialogVisible = false">Đóng</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { Refresh, Promotion, Document, Grid, Loading, Plus, ChatRound } from '@element-plus/icons-vue';

// =====================================================
// TYPES & INTERFACES
// =====================================================
interface FileItem { name: string; }
interface Source { file: string; location: string; }
interface Message { id: string | number; sender: 'user' | 'ai'; text: string; sources?: Source[]; }
interface HistoryItem { id: number; search_query: string; generated_prompt: string; ai_response: string; created_at: string; }
interface ChatSession { id: string; title: string; created_at: string; }

// =====================================================
// CONSTANTS
// =====================================================
const API_BASE_URL = 'http://localhost:8000/api';

// =====================================================
// STATE: TAB
// =====================================================
const activeTab = ref<string>('chat');

// =====================================================
// STATE: SESSION MANAGEMENT
// =====================================================
const sessions = ref<ChatSession[]>([]);
const activeSessionId = ref<string | null>(null);
const activeSessionTitle = ref<string>('');
const isLoadingSessions = ref(false);
const isCreatingSession = ref(false);

// =====================================================
// STATE: KNOWLEDGE BASE / FILES
// =====================================================
const files = ref<FileItem[]>([]);
const isLoadingFiles = ref(false);
const isIngesting = ref(false);

// =====================================================
// STATE: CHAT
// =====================================================
const messages = ref<Message[]>([]);
const chatInput = ref('');
const isChatting = ref(false);
const chatContainerRef = ref<HTMLElement | null>(null);

// =====================================================
// STATE: LỊCH SỬ (Tab 2)
// =====================================================
const historyList = ref<HistoryItem[]>([]);
const isLoadingHistory = ref(false);
const isDialogVisible = ref(false);
const selectedHistory = ref<HistoryItem | null>(null);

// =====================================================
// HELPER: ICON & MÀU SẮC FILE
// =====================================================
const getFileIcon = (filename: string) => {
  if (!filename) return Document;
  const lower = filename.toLowerCase();
  if (lower.endsWith('.xlsx') || lower.endsWith('.xls')) return Grid;
  return Document;
};

const getFileIconColor = (filename: string) => {
  if (!filename) return '#909399';
  const lower = filename.toLowerCase();
  if (lower.endsWith('.pdf')) return '#F56C6C';
  if (lower.endsWith('.xlsx') || lower.endsWith('.xls')) return '#67C23A';
  if (lower.endsWith('.docx')) return '#409EFF';
  if (lower.endsWith('.pptx')) return '#E6A23C';
  if (lower.endsWith('.txt') || lower.endsWith('.log')) return '#909399';
  return '#909399';
};

// =====================================================
// HELPER: CUỘN XUỐNG CUỐI
// =====================================================
const scrollToBottom = async () => {
  await nextTick();
  if (chatContainerRef.value) {
    chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight;
  }
};

// =====================================================
// API: LẤY DANH SÁCH SESSIONS
// =====================================================
const fetchSessions = async () => {
  isLoadingSessions.value = true;
  try {
    const res = await axios.get(`${API_BASE_URL}/sessions`);
    sessions.value = res.data;
  } catch (e: any) {
    ElMessage.error('Không thể tải danh sách cuộc trò chuyện.');
  } finally {
    isLoadingSessions.value = false;
  }
};

// =====================================================
// API: TẠO SESSION MỚI
// =====================================================
const createNewSession = async () => {
  isCreatingSession.value = true;
  try {
    const res = await axios.post(`${API_BASE_URL}/sessions`, { title: 'Cuộc trò chuyện mới' });
    const newSession: ChatSession = res.data;
    sessions.value.unshift(newSession);
    // Chuyển sang session mới, xóa tin nhắn cũ
    activeSessionId.value = newSession.id;
    activeSessionTitle.value = newSession.title;
    messages.value = [{
      id: 'welcome',
      sender: 'ai',
      text: '👋 Cuộc trò chuyện mới bắt đầu. Hãy đặt câu hỏi cho tôi!'
    }];
    ElMessage.success('Đã tạo cuộc trò chuyện mới!');
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Không thể tạo cuộc trò chuyện mới.');
  } finally {
    isCreatingSession.value = false;
  }
};

// =====================================================
// API: CHUYỂN SESSION (click sidebar item)
// =====================================================
const switchSession = async (session: ChatSession) => {
  if (activeSessionId.value === session.id) return;
  activeSessionId.value = session.id;
  activeSessionTitle.value = session.title;
  messages.value = [];
  try {
    const res = await axios.get(`${API_BASE_URL}/sessions/${session.id}/messages`);
    const raw = res.data.messages as Array<{ role: string; content: string; id: number }>;
    messages.value = raw.map(m => ({
      id: m.id,
      sender: m.role === 'user' ? 'user' : 'ai',
      text: m.content
    }));
    if (messages.value.length === 0) {
      messages.value = [{ id: 'empty', sender: 'ai', text: '📭 Phiên này chưa có tin nhắn nào. Hãy bắt đầu hỏi!' }];
    }
    await scrollToBottom();
  } catch (e: any) {
    ElMessage.error('Không thể tải tin nhắn của phiên này.');
  }
};

// =====================================================
// API: LẤY DANH SÁCH FILE
// =====================================================
const fetchFiles = async () => {
  isLoadingFiles.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/files`);
    files.value = response.data.files.map((name: string) => ({ name }));
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Không thể tải danh sách tài liệu.');
  } finally {
    isLoadingFiles.value = false;
  }
};

// =====================================================
// API: ĐỒNG BỘ HỆ THỐNG (INGEST)
// =====================================================
const handleIngest = async () => {
  isIngesting.value = true;
  try {
    const response = await axios.post(`${API_BASE_URL}/ingest`);
    ElMessage.success(`Đồng bộ thành công! Đã tạo ${response.data?.chunks || 0} chunks.`);
    await fetchFiles();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Có lỗi xảy ra trong quá trình đồng bộ.');
  } finally {
    isIngesting.value = false;
  }
};

// =====================================================
// API: GỬI TIN NHẮN
// =====================================================
const sendMessage = async () => {
  const content = chatInput.value.trim();
  if (!content || isChatting.value || !activeSessionId.value) return;

  messages.value.push({ id: Date.now(), sender: 'user', text: content });
  chatInput.value = '';
  scrollToBottom();
  isChatting.value = true;

  try {
    const response = await axios.post(`${API_BASE_URL}/chat`, {
      question: content,
      session_id: activeSessionId.value
    });
    const { answer, sources } = response.data;

    messages.value.push({ id: Date.now() + 1, sender: 'ai', text: answer, sources: sources || [] });

    // Cập nhật tiêu đề session nếu là tin nhắn đầu (backend đã đổi title thành câu hỏi)
    const session = sessions.value.find(s => s.id === activeSessionId.value);
    if (session && session.title === 'Cuộc trò chuyện mới') {
      session.title = content.substring(0, 60);
      activeSessionTitle.value = session.title;
    }

    if (activeTab.value === 'history') await fetchHistory();
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Lỗi kết nối đến server AI.');
    messages.value.push({ id: Date.now() + 1, sender: 'ai', text: 'Xin lỗi, tôi đang gặp sự cố kỹ thuật.' });
  } finally {
    isChatting.value = false;
    scrollToBottom();
  }
};

// =====================================================
// API: LỊCH SỬ PROMPT (Tab 2)
// =====================================================
const fetchHistory = async () => {
  isLoadingHistory.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/history`);
    historyList.value = response.data;
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Không thể tải lịch sử chat.');
  } finally {
    isLoadingHistory.value = false;
  }
};

const openPromptDialog = (record: HistoryItem) => {
  selectedHistory.value = record;
  isDialogVisible.value = true;
};

const onTabClick = (tab: any) => {
  if (tab.paneName === 'history') fetchHistory();
};

// =====================================================
// LIFECYCLE
// =====================================================
onMounted(async () => {
  await Promise.all([fetchFiles(), fetchSessions()]);
});
</script>



<style scoped>
/* =====================================================
   LAYOUT TỔNG THỂ
   ===================================================== */
.app-wrapper {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  background-color: #f0f2f5;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  overflow: hidden;
}

.app-header {
  background: linear-gradient(135deg, #409eff, #6b21a8);
  padding: 12px 24px;
  color: #fff;
  flex-shrink: 0;
}

.app-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* =====================================================
   EL-TABS TÙY CHỈNH
   ===================================================== */
.main-tabs {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

:deep(.el-tabs__header) {
  background: #fff;
  margin: 0;
  padding: 0 24px;
  border-bottom: 1px solid #dcdfe6;
  flex-shrink: 0;
}

:deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

:deep(.el-tab-pane) {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* =====================================================
   TAB 1: CHAT LAYOUT
   ===================================================== */
.chat-layout {
  height: 100%;
  overflow: hidden;
}

/* --- Sidebar --- */
.sidebar {
  background-color: #fff;
  border-right: 1px solid #dcdfe6;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.sidebar-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.sidebar-actions {
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
}

.full-width {
  width: 100%;
}

.sidebar-content {
  padding: 16px 20px;
  flex: 1;
  overflow-y: auto;
}

.sidebar-section-title {
  font-size: 11px;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 12px 0;
  font-weight: 600;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 40px;
}

.no-files {
  text-align: center;
  color: #c0c4cc;
  font-size: 13px;
  padding: 20px 0;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #f5f7fa;
  transition: background 0.2s;
}

.file-item:hover {
  background: #e8f0fe;
}

.file-name {
  font-size: 13px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* --- Main chat area --- */
.main-area {
  display: flex;
  flex-direction: column;
  padding: 0;
  background-color: #f0f2f5;
  overflow: hidden;
}

.chat-container {
  flex: 1;
  padding: 20px 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-wrapper {
  display: flex;
  width: 100%;
}

.message-wrapper.is-user {
  justify-content: flex-end;
}

.message-wrapper.is-ai {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 68%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  word-break: break-word;
  white-space: pre-wrap;
}

.is-user .message-bubble {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  border-bottom-right-radius: 3px;
}

.is-ai .message-bubble {
  background: #fff;
  color: #303133;
  border-bottom-left-radius: 3px;
}

/* Nguồn trích dẫn */
.message-sources {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #ebeef5;
}

:deep(.el-collapse) { border: none; }
:deep(.el-collapse-item__header) {
  height: 30px;
  line-height: 30px;
  background: transparent;
  color: #909399;
  font-size: 12px;
  border: none;
}
:deep(.el-collapse-item__wrap) { background: transparent; border: none; }
:deep(.el-collapse-item__content) { padding-bottom: 4px; }

.source-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 6px;
}

.source-tag {
  font-size: 11px;
}

/* Loading bubble */
.loading-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-style: italic;
  font-size: 13px;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
}

/* Khu vực nhập liệu */
.chat-input-area {
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #dcdfe6;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-shrink: 0;
}

.send-btn {
  margin-bottom: 5px;
  flex-shrink: 0;
}

/* =====================================================
   TAB 2: LỊCH SỬ
   ===================================================== */
.history-wrapper {
  padding: 20px 24px;
  height: 100%;
  overflow-y: auto;
  background: #f0f2f5;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.history-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.query-text {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}

.response-preview {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

/* Dialog chi tiết Prompt */
.dialog-meta {
  background: #f5f7fa;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 12px;
}

.dialog-meta p {
  margin: 4px 0;
  font-size: 14px;
  color: #303133;
}

.prompt-display {
  white-space: pre-wrap;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
  max-height: 50vh;
  overflow-y: auto;
  border: 1px solid #dcdfe6;
  font-family: 'Courier New', Courier, monospace;
}

/* =====================================================
   SIDEBAR: SESSION LIST (ChatGPT Style)
   ===================================================== */
.sidebar {
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid #2a2a4a;
}

.sidebar-sessions {
  padding: 12px;
  flex-shrink: 0;
}

.new-session-btn {
  width: 100%;
  margin-bottom: 10px;
  background: #16213e;
  border-color: #4a4a7a;
  color: #fff;
  font-weight: 600;
}

.new-session-btn:hover {
  background: #0f3460;
  border-color: #409eff;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 280px;
  overflow-y: auto;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: #c8c8d8;
  font-size: 13px;
  transition: background 0.15s;
  min-width: 0;
}

.session-item:hover {
  background: #16213e;
  color: #fff;
}

.session-item.is-active {
  background: #0f3460;
  color: #fff;
  font-weight: 500;
}

.session-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.no-sessions {
  text-align: center;
  color: #666688;
  font-size: 12px;
  padding: 16px 0;
}

/* =====================================================
   SIDEBAR: KNOWLEDGE BASE SECTION
   ===================================================== */
.sidebar-kb {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0 12px 12px;
  min-height: 0;
}

.sidebar-actions {
  margin-bottom: 10px;
  flex-shrink: 0;
}

.sidebar-section-title {
  font-size: 11px;
  color: #666688;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 8px 0;
  font-weight: 600;
  flex-shrink: 0;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  flex: 1;
}

.no-files {
  text-align: center;
  color: #666688;
  font-size: 12px;
  padding: 16px 0;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  background: #16213e;
  transition: background 0.2s;
}

.file-item:hover { background: #0f3460; }

.file-name {
  font-size: 12px;
  color: #c8c8d8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* =====================================================
   CHAT HEADER
   ===================================================== */
.chat-header {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.placeholder-header {
  color: #909399;
  font-weight: 400;
  font-style: italic;
}
</style>

