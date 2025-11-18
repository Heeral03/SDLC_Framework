import React, { useState, useRef, useEffect } from 'react';
import { Send, Plus, Upload, MessageSquare, AlertCircle, CheckCircle, XCircle, Menu, X, Shield, FileText, Target, Zap, Settings } from 'lucide-react';

export default function RAGChatbot() {
  const [chats, setChats] = useState([
    { 
      id: 1, 
      title: 'New Conversation', 
      messages: [], 
      timestamp: Date.now(),
      sessionId: generateSessionId(),
      sdlcPhase: 'auto',
      uploadedFiles: []
    }
  ]);
  const [activeChat, setActiveChat] = useState(1);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [verifyEnabled, setVerifyEnabled] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // SDLC Phases
  const SDLC_PHASES = [
    { value: 'auto', label: '🔄 Auto-detect', color: 'bg-gray-100 text-gray-800' },
    { value: 'requirements', label: '📋 Requirements', color: 'bg-blue-100 text-blue-800' },
    { value: 'design', label: '🎨 Design', color: 'bg-purple-100 text-purple-800' },
    { value: 'development', label: '💻 Development', color: 'bg-green-100 text-green-800' },
    { value: 'testing', label: '🧪 Testing', color: 'bg-yellow-100 text-yellow-800' },
    { value: 'deployment', label: '🚀 Deployment', color: 'bg-orange-100 text-orange-800' },
    { value: 'maintenance', label: '🔧 Maintenance', color: 'bg-red-100 text-red-800' }
  ];

  function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

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
      timestamp: Date.now(),
      sessionId: generateSessionId(),
      sdlcPhase: 'auto',
      uploadedFiles: []
    };
    setChats(prev => [newChat, ...prev]);
    setActiveChat(newId);
  };

  const updateChatPhase = (phase) => {
    setChats(prev => prev.map(c => 
      c.id === activeChat ? { ...c, sdlcPhase: phase } : c
    ));
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const currentChat = getCurrentChat();
    if (currentChat.messages.length === 0) {
      updateChatTitle(activeChat, `Uploaded: ${file.name}`);
    }

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
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`http://localhost:8000/upload?session_id=${currentChat.sessionId}`, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      setChats(prev => prev.map(c => {
        if (c.id === activeChat) {
          const filteredMessages = c.messages.filter(m => m.content !== uploadingMessage.content);
          
          let resultContent = '';
          let detectedPhase = '';
          
          if (result.success) {
            resultContent = `✓ ${file.name} uploaded successfully!\n`;
            resultContent += `• ${result.chunks_created} chunks created\n`;
            
            if (result.detected_sdlc_phase) {
              detectedPhase = result.detected_sdlc_phase;
              const phaseInfo = SDLC_PHASES.find(p => p.value === detectedPhase);
              resultContent += `• Detected Phase: ${phaseInfo?.label || detectedPhase}`;
            }
          } else {
            resultContent = `✗ Upload failed: ${result.message}`;
          }

          const resultMessage = {
            role: result.success ? 'system' : 'error',
            content: resultContent,
            timestamp: Date.now()
          };

          return { 
            ...c, 
            messages: [...filteredMessages, resultMessage],
            uploadedFiles: result.success ? [...c.uploadedFiles, file.name] : c.uploadedFiles,
            sdlcPhase: detectedPhase || c.sdlcPhase
          };
        }
        return c;
      }));

    } catch (error) {
      console.error('Upload error:', error);
      
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
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: userMessage.content,
          session_id: currentChat.sessionId,
          verify: verifyEnabled,
          sdlc_phase: currentChat.sdlcPhase
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Clean the response content to remove any prompt leakage
      const cleanContent = cleanResponseContent(data.dss_output || 'No response generated');

      const assistantMessage = {
        role: 'assistant',
        content: cleanContent,
        verification: data.verification,
        sdlcPhase: data.sdlc_phase,
        phaseInfo: data.phase_info,
        sessionFiles: data.session_files,
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

  // Clean response content from backend
  const cleanResponseContent = (content) => {
    if (!content) return 'No response generated';
    
    // Remove common prompt leakage patterns
    const patterns = [
      /You are an expert.*?SDLC DSS\./gi,
      /CRITICAL INSTRUCTIONS:.*?USER QUESTION:/gs,
      /TASK:.*?USER QUESTION:/gs,
      /RESPONSE FORMAT:.*?USER QUESTION:/gs,
      /CONTEXT INFORMATION:.*?USER QUESTION:/gs,
      /BEGIN OUTPUT:.*?USER QUESTION:/gs,
      /MUST FOLLOW THIS EXACT FORMAT.*?USER QUESTION:/gs,
      /USER QUESTION:.*$/gs
    ];

    let cleaned = content;
    patterns.forEach(pattern => {
      cleaned = cleaned.replace(pattern, '');
    });

    // Remove lines that are clearly from the prompt
    const lines = cleaned.split('\n');
    const filteredLines = lines.filter(line => {
      const lowerLine = line.toLowerCase();
      return !lowerLine.includes('you are an expert') &&
             !lowerLine.includes('critical instructions') &&
             !lowerLine.includes('task:') &&
             !lowerLine.includes('response format') &&
             !lowerLine.includes('begin your response') &&
             !lowerLine.includes('must follow') &&
             !lowerLine.includes('context information') &&
             !lowerLine.includes('user question:') &&
             !lowerLine.includes('begin output:');
    });

    cleaned = filteredLines.join('\n').trim();

    // If we removed everything, return the original but with basic cleaning
    if (!cleaned || cleaned.length < 50) {
      cleaned = content.replace(/You are an expert.*?SDLC DSS\./gi, '')
                      .replace(/USER QUESTION:.*$/gi, '')
                      .trim();
    }

    return cleaned || 'Unable to generate proper analysis. Please try again with a different question.';
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
    const score = verification.compliance_score || 0;

    return (
      <div className={`mt-4 p-4 rounded-xl border-2 ${
        isPassing 
          ? 'bg-green-50 border-green-300' 
          : 'bg-red-50 border-red-300'
      }`}>
        <div className="flex items-start gap-3">
          {isPassing ? (
            <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className={`font-bold text-lg ${
                isPassing ? 'text-green-800' : 'text-red-800'
              }`}>
                {verification.pass_fail}
              </span>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                score >= 0.7 ? 'bg-green-200 text-green-800' :
                score >= 0.4 ? 'bg-yellow-200 text-yellow-800' :
                'bg-red-200 text-red-800'
              }`}>
                Score: {(score * 100).toFixed(0)}%
              </span>
              {verification.risk_level && (
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  verification.risk_level === 'High' ? 'bg-red-200 text-red-800' :
                  verification.risk_level === 'Medium' ? 'bg-yellow-200 text-yellow-800' :
                  'bg-green-200 text-green-800'
                }`}>
                  {verification.risk_level} Risk
                </span>
              )}
            </div>
            
            {verification.explanation && (
              <p className={`text-sm mb-3 ${isPassing ? 'text-green-700' : 'text-red-700'}`}>
                {verification.explanation}
              </p>
            )}

            {verification.criteria_met && verification.criteria_met.length > 0 && (
              <div className="mb-3">
                <p className="font-semibold text-green-800 mb-2 text-sm">✓ Criteria Met:</p>
                <ul className="list-disc list-inside text-green-700 space-y-1 text-sm">
                  {verification.criteria_met.map((req, idx) => (
                    <li key={idx}>{req}</li>
                  ))}
                </ul>
              </div>
            )}

            {verification.criteria_failed && verification.criteria_failed.length > 0 && (
              <div className="mb-3">
                <p className="font-semibold text-red-800 mb-2 text-sm">✗ Criteria Failed:</p>
                <ul className="list-disc list-inside text-red-700 space-y-1 text-sm">
                  {verification.criteria_failed.map((req, idx) => (
                    <li key={idx}>{req}</li>
                  ))}
                </ul>
              </div>
            )}

            {verification.recommendations && verification.recommendations.length > 0 && (
              <div>
                <p className="font-semibold text-gray-800 mb-2 text-sm">💡 Recommendations:</p>
                <ul className="list-disc list-inside text-gray-700 space-y-1 text-sm">
                  {verification.recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const FormattedMessage = ({ content }) => {
    // Enhanced formatting for SDLC analysis
    const formatContent = (text) => {
      if (!text) return null;

      // Split by lines and format accordingly
      const lines = text.split('\n');
      let inPhaseScores = false;
      let inDetailedAnalysis = false;

      return lines.map((line, index) => {
        const trimmed = line.trim();
        
        // Section headers
        if (trimmed.includes('AGGREGATED PHASE SCORES')) {
          inPhaseScores = true;
          inDetailedAnalysis = false;
          return (
            <div key={index} className="mb-4">
              <h3 className="text-lg font-bold text-purple-800 bg-purple-50 px-3 py-2 rounded-lg border-l-4 border-purple-500">
                📊 {trimmed}
              </h3>
            </div>
          );
        }

        if (trimmed.includes('DETAILED ANALYSIS FOR CURRENT PHASE')) {
          inPhaseScores = false;
          inDetailedAnalysis = true;
          return (
            <div key={index} className="mt-6 mb-4">
              <h3 className="text-lg font-bold text-blue-800 bg-blue-50 px-3 py-2 rounded-lg border-l-4 border-blue-500">
                🔍 {trimmed}
              </h3>
            </div>
          );
        }

        // Phase score lines
        if (inPhaseScores && trimmed.includes('/10')) {
          const match = trimmed.match(/(.*?):\s*(\d+)\/10\s*-\s*(.*)/);
          if (match) {
            const [, phase, score, justification] = match;
            const scoreNum = parseInt(score);
            const scoreColor = scoreNum >= 8 ? 'text-green-600' : 
                             scoreNum >= 6 ? 'text-yellow-600' : 
                             'text-red-600';
            
            return (
              <div key={index} className="flex items-start gap-3 mb-3 p-3 bg-gray-50 rounded-lg">
                <span className={`font-bold text-lg ${scoreColor} min-w-12`}>
                  {score}/10
                </span>
                <div className="flex-1">
                  <div className="font-semibold text-gray-900">{phase}</div>
                  <div className="text-sm text-gray-700 mt-1">{justification}</div>
                </div>
              </div>
            );
          }
        }

        // Regular phase lines without score parsing
        if (inPhaseScores && trimmed && !trimmed.includes('━━━━') && trimmed.length > 5) {
          return (
            <div key={index} className="mb-2 text-gray-800">
              {trimmed}
            </div>
          );
        }

        // Detailed analysis content
        if (inDetailedAnalysis && trimmed) {
          // Check for sub-headers in detailed analysis
          if (trimmed.includes('COMPLIANCE:') || trimmed.includes('ISSUES FOUND:') || 
              trimmed.includes('RECOMMENDATIONS:') || trimmed.includes('RISK LEVEL:') || 
              trimmed.includes('NEXT STEPS:')) {
            return (
              <div key={index} className="mt-4 mb-2">
                <h4 className="font-bold text-gray-900 text-sm uppercase tracking-wide">
                  {trimmed}
                </h4>
              </div>
            );
          }

          // List items in detailed analysis
          if (trimmed.startsWith('-') || trimmed.startsWith('•')) {
            return (
              <div key={index} className="flex items-start gap-2 ml-4 mb-1">
                <span className="text-gray-500 mt-1">•</span>
                <span className="text-gray-700">{trimmed.substring(1).trim()}</span>
              </div>
            );
          }

          // Regular text in detailed analysis
          return (
            <div key={index} className="text-gray-700 mb-2">
              {trimmed}
            </div>
          );
        }

        // Separator lines
        if (trimmed.includes('━━━━')) {
          return <hr key={index} className="my-4 border-gray-300" />;
        }

        // Skip empty lines at certain points
        if (!trimmed) {
          return <br key={index} />;
        }

        // Default formatting
        return (
          <div key={index} className="text-gray-800 mb-1">
            {trimmed}
          </div>
        );
      });
    };

    return (
      <div className="whitespace-pre-wrap font-sans leading-relaxed">
        {formatContent(content)}
      </div>
    );
  };

  const EmptyState = () => (
    <div className="h-full flex items-center justify-center p-6">
      <div className="text-center max-w-3xl">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            SDLC Decision Support System
          </h2>
          <p className="text-gray-600 text-lg">
            AI-powered software verification with SDLC phase-aware analysis
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl p-5 border-2 border-purple-300 hover:border-purple-400 transition-colors">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-3 mx-auto">
              <FileText className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Phase-Aware Analysis</h3>
            <p className="text-sm text-gray-600">
              Evaluates your project based on current SDLC phase requirements
            </p>
          </div>

          <div className="bg-white rounded-xl p-5 border-2 border-purple-300 hover:border-purple-400 transition-colors">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-3 mx-auto">
              <Target className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Compliance Checking</h3>
            <p className="text-sm text-gray-600">
              Verifies adherence to software engineering best practices
            </p>
          </div>

          <div className="bg-white rounded-xl p-5 border-2 border-purple-300 hover:border-purple-400 transition-colors">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-3 mx-auto">
              <Zap className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Risk Assessment</h3>
            <p className="text-sm text-gray-600">
              Identifies issues and provides actionable recommendations
            </p>
          </div>
        </div>

        <div className="bg-purple-50 rounded-xl p-6 border-2 border-purple-300">
          <h3 className="font-semibold text-gray-900 mb-3">Get Started</h3>
          <p className="text-sm text-gray-700 mb-4">
            Upload your project files (SRS, code, tests, etc.) and ask questions about requirements, design, implementation, or compliance.
          </p>
          <div className="text-xs text-gray-600">
            <p><strong>Supported:</strong> Python, JavaScript, Java, C++, Jupyter notebooks, PyTorch models, JSON, CSV, PDFs, and 20+ formats</p>
          </div>
        </div>
      </div>
    </div>
  );

  const currentChat = getCurrentChat();
  const currentPhase = SDLC_PHASES.find(p => p.value === currentChat?.sdlcPhase);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className={`${
        isSidebarOpen ? 'w-80' : 'w-0'
      } bg-slate-900 text-white transition-all duration-300 flex flex-col overflow-hidden`}>
        <div className="p-4 border-b border-slate-700">
          <button
            onClick={createNewChat}
            className="w-full flex items-center justify-center gap-2 bg-purple-500 hover:bg-purple-600 text-white px-4 py-3 rounded-xl transition-colors font-medium shadow-lg"
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
                  ? 'bg-purple-500 text-white shadow-lg' 
                  : 'hover:bg-slate-800 text-slate-300'
              }`}
            >
              <div className="flex items-start gap-2">
                <MessageSquare className="w-4 h-4 mt-1 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{chat.title}</p>
                  <p className={`text-xs mt-1 ${activeChat === chat.id ? 'text-purple-200' : 'text-slate-400'}`}>
                    {chat.messages.length} messages • {chat.uploadedFiles?.length || 0} files
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className="p-4 border-t border-slate-700 space-y-3">
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
            onChange={handleFileUpload}
            className="hidden"
            accept=".txt,.pdf,.py,.ipynb,.json,.csv,.md,.yaml,.yml,.pt,.pth,.pkl,.pickle,.js,.jsx,.ts,.tsx,.java,.cpp,.c,.h,.rs,.go,.rb,.php,.html,.css,.xml,.sh,.r,.sql"
            disabled={isUploading}
          />
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4 flex items-center gap-3">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
          >
            {isSidebarOpen ? <X className="w-5 h-5 text-gray-700" /> : <Menu className="w-5 h-5 text-gray-700" />}
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-gray-900">
                {currentChat?.title || 'SDLC Assistant'}
              </h1>
              {currentPhase && (
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${currentPhase.color}`}>
                  {currentPhase.label}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600">
              {currentChat?.uploadedFiles?.length > 0 
                ? `${currentChat.uploadedFiles.length} files uploaded`
                : 'Upload files to start analysis'}
            </p>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
          >
            <Settings className="w-5 h-5 text-gray-700" />
          </button>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="bg-purple-50 border-b border-purple-200 p-4">
            <div className="max-w-4xl mx-auto space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  SDLC Phase
                </label>
                <select
                  value={currentChat?.sdlcPhase || 'auto'}
                  onChange={(e) => updateChatPhase(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  {SDLC_PHASES.map(phase => (
                    <option key={phase.value} value={phase.value}>
                      {phase.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="verify"
                  checked={verifyEnabled}
                  onChange={(e) => setVerifyEnabled(e.target.checked)}
                  className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                />
                <label htmlFor="verify" className="text-sm font-medium text-gray-700">
                  Enable Compliance Verification (adds detailed checks to each response)
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          {currentChat?.messages.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              {currentChat?.messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'system' ? (
                    <div className="flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-700 rounded-xl text-sm font-medium border border-blue-200">
                      <AlertCircle className="w-4 h-4" />
                      <div className="whitespace-pre-line">{msg.content}</div>
                    </div>
                  ) : msg.role === 'error' ? (
                    <div className="flex items-start gap-2 px-4 py-3 bg-red-100 text-red-700 rounded-xl text-sm max-w-2xl border border-red-200">
                      <XCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      <span>{msg.content}</span>
                    </div>
                  ) : msg.role === 'user' ? (
                    <div className="bg-purple-500 text-white px-5 py-3 rounded-2xl max-w-xl shadow-md">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="bg-white px-6 py-5 rounded-2xl max-w-full border-2 border-gray-200 shadow-sm w-full">
                      <FormattedMessage content={msg.content} />
                      <VerificationBadge verification={msg.verification} />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white px-5 py-4 rounded-2xl border border-gray-200">
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2.5 h-2.5 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
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
                  placeholder="Ask about requirements, compliance, design patterns, or code quality..."
                  className="w-full px-5 py-3 border-2 border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none bg-white"
                  rows="1"
                  style={{ minHeight: '52px', maxHeight: '200px' }}
                  disabled={isLoading}
                />
              </div>
              <button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                className="bg-purple-500 hover:bg-purple-600 text-white p-3.5 rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-lg"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Press Enter to send • Shift+Enter for new line • Click ⚙️ for settings
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}