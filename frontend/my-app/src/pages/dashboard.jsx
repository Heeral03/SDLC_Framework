import React, { useState, useRef, useEffect } from 'react';
import { Send, Plus, Upload, MessageSquare, AlertCircle, CheckCircle, XCircle, Menu, X, Shield, FileText, Target, Zap } from 'lucide-react';

export default function RAGChatbot() {
  const [chats, setChats] = useState([
    { id: 1, title: 'New Conversation', messages: [], timestamp: Date.now() }
  ]);
  const [activeChat, setActiveChat] = useState(1);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chats, activeChat]);

  const getCurrentChat = () => chats.find(c => c.id === activeChat);

  const updateChatTitle = (chatId, firstMessage) => {
    const title = firstMessage.length > 30 
      ? firstMessage.substring(0, 30) + '...' 
      : firstMessage;
    setChats(prev => prev.map(c => 
      c.id === chatId && c.title === 'New Conversation' 
        ? { ...c, title } 
        : c
    ));
  };

  const createNewChat = () => {
    const newId = Math.max(...chats.map(c => c.id), 0) + 1;
    const newChat = { 
      id: newId, 
      title: 'New Conversation', 
      messages: [],
      timestamp: Date.now()
    };
    setChats(prev => [newChat, ...prev]);
    setActiveChat(newId);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const currentChat = getCurrentChat();
    if (currentChat.messages.length === 0) {
      updateChatTitle(activeChat, `Uploaded: ${file.name}`);
    }

    // Show uploading message
    const uploadingMessage = {
      role: 'system',
      content: `📤 Uploading ${file.name}...`,
      timestamp: Date.now()
    };

    setChats(prev => prev.map(c => 
      c.id === activeChat 
        ? { ...c, messages: [...c.messages, uploadingMessage] }
        : c
    ));

    setIsUploading(true);

    try {
      // Create FormData to send file
      const formData = new FormData();
      formData.append('file', file);

      // Upload to backend
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      // Remove uploading message and add result
      setChats(prev => prev.map(c => {
        if (c.id === activeChat) {
          const filteredMessages = c.messages.filter(m => m.content !== uploadingMessage.content);
          
          const resultMessage = {
            role: result.success ? 'system' : 'error',
            content: result.success 
              ? `✓ ${file.name} uploaded successfully! (${result.chunks_created} chunks created)`
              : `✗ Upload failed: ${result.message}`,
            timestamp: Date.now()
          };

          return { ...c, messages: [...filteredMessages, resultMessage] };
        }
        return c;
      }));

    } catch (error) {
      console.error('Upload error:', error);
      
      // Remove uploading message and show error
      setChats(prev => prev.map(c => {
        if (c.id === activeChat) {
          const filteredMessages = c.messages.filter(m => m.content !== uploadingMessage.content);
          
          const errorMessage = {
            role: 'error',
            content: `✗ Upload failed: ${error.message}. Make sure FastAPI is running on http://localhost:8000`,
            timestamp: Date.now()
          };

          return { ...c, messages: [...filteredMessages, errorMessage] };
        }
        return c;
      }));
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: Date.now()
    };

    const currentChat = getCurrentChat();
    if (currentChat.messages.length === 0) {
      updateChatTitle(activeChat, input.trim());
    }

    setChats(prev => prev.map(c => 
      c.id === activeChat 
        ? { ...c, messages: [...c.messages, userMessage] }
        : c
    ));

    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`http://localhost:8000/ask?q=${encodeURIComponent(userMessage.content)}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Extract clean DSS output
      let cleanDssOutput = data.dss_output || '';
      const answerMarker = 'Answer in simple terms:';
      const answerIndex = cleanDssOutput.indexOf(answerMarker);
      
      if (answerIndex !== -1) {
        cleanDssOutput = cleanDssOutput.substring(answerIndex + answerMarker.length).trim();
      }

      // Parse verification
      let verificationData = null;
      if (data.verification && typeof data.verification === 'object') {
        if (data.verification.raw_output) {
          try {
            const jsonMatch = data.verification.raw_output.match(/\{[\s\S]*?\}/);
            if (jsonMatch) {
              verificationData = JSON.parse(jsonMatch[0]);
            }
          } catch (e) {
            console.error('Failed to parse verification from raw_output:', e);
          }
        } else {
          verificationData = data.verification;
        }
      }

      const assistantMessage = {
        role: 'assistant',
        content: cleanDssOutput || 'No response generated',
        verification: verificationData,
        context: data.context || '',
        timestamp: Date.now()
      };

      setChats(prev => prev.map(c => 
        c.id === activeChat 
          ? { ...c, messages: [...c.messages, assistantMessage] }
          : c
      ));
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        role: 'error',
        content: `Connection failed: ${error.message}. Make sure FastAPI is running on http://localhost:8000`,
        timestamp: Date.now()
      };

      setChats(prev => prev.map(c => 
        c.id === activeChat 
          ? { ...c, messages: [...c.messages, errorMessage] }
          : c
      ));
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const VerificationBadge = ({ verification }) => {
    if (!verification) return null;

    const isPassing = verification.pass_fail === 'PASS';
    const riskLevel = verification.risk_score > 0.7 ? 'high' : 
                      verification.risk_score > 0.4 ? 'medium' : 'low';

    return (
      <div className={`mt-3 p-4 rounded-xl border ${
        isPassing 
          ? 'bg-purple-50 border-purple-300' 
          : 'bg-red-50 border-red-300'
      }`}>
        <div className="flex items-start gap-3">
          {isPassing ? (
            <CheckCircle className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`font-semibold ${
                isPassing ? 'text-purple-800' : 'text-red-800'
              }`}>
                {verification.pass_fail}
              </span>
              <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                riskLevel === 'high' ? 'bg-red-200 text-red-800' :
                riskLevel === 'medium' ? 'bg-purple-200 text-purple-800' :
                'bg-purple-200 text-purple-800'
              }`}>
                Risk: {(verification.risk_score * 100).toFixed(0)}%
              </span>
            </div>
            <p className={`text-sm ${isPassing ? 'text-purple-700' : 'text-red-700'} mb-2`}>
              {verification.explanation}
            </p>
            {verification.violated_requirements && verification.violated_requirements.length > 0 && (
              <div className="mt-3">
                <p className="font-medium text-red-800 mb-1.5 text-sm">Violated Requirements:</p>
                <ul className="list-disc list-inside text-red-700 space-y-1 text-sm">
                  {verification.violated_requirements.map((req, idx) => (
                    <li key={idx}>{req}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const EmptyState = () => (
    <div className="h-full flex items-center justify-center p-6">
      <div className="text-center max-w-2xl">
        <div className="mb-5">
          <p className="text-gray-600 text-lg mt-7">
            AI-powered document verification with compliance checking
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="bg-white rounded-xl p-5 border border-purple-500 hover:border-purple-200 transition-colors">
            <div className="w-12 h-12 bg-purple-50 rounded-lg flex items-center justify-center mb-3 mx-auto">
              <FileText className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Multi-Format Support</h3>
            <p className="text-sm text-gray-600">
              Upload Python, Jupyter notebooks, PyTorch models, JSON, CSV, and 25+ file formats
            </p>
          </div>

          <div className="bg-white rounded-xl p-5 border border-purple-500 hover:border-purple-200 transition-colors">
            <div className="w-12 h-12 bg-purple-50 rounded-lg flex items-center justify-center mb-3 mx-auto">
              <Target className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Compliance Checking</h3>
            <p className="text-sm text-gray-600">
              Ensures adherence to safety, ethical, and regulatory constraints
            </p>
          </div>

          <div className="bg-white rounded-xl p-5 border border-purple-500 hover:border-purple-200 transition-colors">
            <div className="w-12 h-12 bg-purple-50 rounded-lg flex items-center justify-center mb-3 mx-auto">
              <Zap className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Risk Assessment</h3>
            <p className="text-sm text-gray-600">
              Calculates risk scores and identifies potential violations
            </p>
          </div>
        </div>

        <div className="bg-purple-50 rounded-xl p-6 border border-purple-500 mb-4">
          <h3 className="font-semibold text-gray-900 mb-3">Supported File Formats</h3>
          <div className="text-sm text-gray-700 space-y-2">
            <p><span className="font-medium text-purple-600">Code:</span> .py, .js, .jsx, .ts, .java, .cpp, .c, .rs, .go, .rb, .php, .sh, .r, .sql</p>
            <p><span className="font-medium text-purple-600">ML/Data:</span> .ipynb, .pt, .pth, .pkl, .pickle, .json, .csv</p>
            <p><span className="font-medium text-purple-600">Documents:</span> .txt, .pdf, .md, .yaml, .yml</p>
            <p><span className="font-medium text-purple-600">Web:</span> .html, .css, .xml</p>
          </div>
        </div>
      </div>
    </div>
  );

  const currentChat = getCurrentChat();

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar */}
      <div className={`${
        isSidebarOpen ? 'w-72' : 'w-0'
      } bg-slate-900 text-white transition-all duration-300 flex flex-col overflow-hidden`}>
        <div className="p-4 border-b border-slate-800">
          <button
            onClick={createNewChat}
            className="w-full flex items-center justify-center gap-2 bg-purple-300 hover:bg-purple-400 text-gray-900 px-4 py-3 rounded-xl transition-colors font-medium"
          >
            <Plus className="w-5 h-5" />
            <span>New Chat</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {chats.map(chat => (
            <button
              key={chat.id}
              onClick={() => setActiveChat(chat.id)}
              className={`w-full text-left px-4 py-3 rounded-xl transition-colors ${
                activeChat === chat.id 
                  ? 'bg-purple-300 text-gray-900' 
                  : 'hover:bg-slate-800 text-white'
              }`}
            >
              <div className="flex items-start gap-2">
                <MessageSquare className="w-4 h-4 mt-1 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{chat.title}</p>
                  <p className={`text-xs mt-1 ${activeChat === chat.id ? 'text-gray-700' : 'text-slate-400'}`}>
                    {chat.messages.length} messages
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className="p-4 border-t border-slate-800">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-700 disabled:cursor-not-allowed px-4 py-3 rounded-xl transition-colors font-medium"
          >
            <Upload className="w-5 h-5" />
            <span>{isUploading ? 'Uploading...' : 'Upload Files'}</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileUpload}
            className="hidden"
            accept=".txt,.pdf,.py,.ipynb,.json,.csv,.md,.yaml,.yml,.pt,.pth,.pkl,.pickle,.js,.jsx,.ts,.tsx,.java,.cpp,.c,.h,.rs,.go,.rb,.php,.html,.css,.xml,.sh,.r,.sql"
            disabled={isUploading}
          />
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4 flex items-center gap-3">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
          >
            {isSidebarOpen ? <X className="w-5 h-5 text-gray-700" /> : <Menu className="w-5 h-5 text-gray-700" />}
          </button>
          <div className="flex-1">
            <h1 className="text-lg font-bold text-gray-900">
              {currentChat?.title || 'RAG Verification Assistant'}
            </h1>
            <p className="text-sm text-gray-600">
              Intelligent verification with compliance checking
            </p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          {currentChat?.messages.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              {currentChat?.messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'system' ? (
                    <div className="flex items-center gap-2 px-4 py-2 bg-purple-100 text-purple-700 rounded-xl text-sm font-medium">
                      <AlertCircle className="w-4 h-4" />
                      {msg.content}
                    </div>
                  ) : msg.role === 'error' ? (
                    <div className="flex items-start gap-2 px-4 py-3 bg-red-100 text-red-700 rounded-xl text-sm max-w-lg border border-red-200">
                      <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      <span>{msg.content}</span>
                    </div>
                  ) : msg.role === 'user' ? (
                    <div className="bg-purple-300 text-gray-900 px-5 py-3 rounded-2xl max-w-lg">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="bg-white px-5 py-4 rounded-2xl max-w-2xl border border-gray-200">
                      <div className="prose prose-sm max-w-none text-gray-800">
                        {msg.content}
                      </div>
                      <VerificationBadge verification={msg.verification} />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white px-5 py-4 rounded-2xl border border-gray-200">
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 bg-purple-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2.5 h-2.5 bg-purple-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2.5 h-2.5 bg-purple-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3 items-end">
              <div className="flex-1 relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about requirements, compliance, or verification..."
                  className="w-full px-5 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-300 focus:border-transparent resize-none bg-white"
                  rows="1"
                  style={{ minHeight: '52px', maxHeight: '200px' }}
                  disabled={isLoading}
                />
              </div>
              <button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                className="bg-purple-300 hover:bg-purple-400 text-gray-900 p-3.5 rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Press Enter to send • Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}