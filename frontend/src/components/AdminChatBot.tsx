import { useState, useEffect, useRef } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  X,
  ChevronDown,
  ChevronUp,
  Database,
  Trash2,
  Copy,
  Check,
  Loader2,
  Layers,
  Minimize2
} from 'lucide-react';
import API_BASE_URL from '../services/api';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  collection?: string;
  pipeline?: any;
  query?: any;
  rows?: any[];
  error?: string | null;
  timestamp: string;
}

const SAMPLE_QUESTIONS = [
                    "Which location has the most escalated incidents?",
                    "How many open tickets?'",
                    "Which technician resolved the most high-severity tickets?",
                    "How many escalated tickets per location?",
                    "How many resolved tickets?"
];

export default function AdminChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedQueryId, setCopiedQueryId] = useState<string | null>(null);
  const [expandedQueryId, setExpandedQueryId] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Hello! I am your NOC Database AI Assistant. Ask me anything about telecom incidents, locations, severities, technician workloads, or users in natural English!',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, loading]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 150);
    }
  }, [isOpen]);

  const handleSend = async (questionText?: string) => {
    const queryText = (questionText || input).trim();
    if (!queryText || loading) return;

    const userMessageId = `user-${Date.now()}`;
    const userMessage: ChatMessage = {
      id: userMessageId,
      sender: 'user',
      text: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/noc/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: queryText })
      });

      const data = await response.json();
      const assistantMessageId = `assistant-${Date.now()}`;

      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        sender: 'assistant',
        text:
          data.answer ||
          (data.error ? `Error: ${data.error}` : 'No response returned from the agent.'),
        collection: data.collection,
        pipeline: data.pipeline || data.query,
        query: data.pipeline || data.query,
        rows: data.rows,
        error: data.error,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      setMessages(prev => [
        ...prev,
        {
          id: `assistant-err-${Date.now()}`,
          sender: 'assistant',
          text: `Failed to connect to NOC AI service: ${err?.message || 'Network error'}. Ensure Flask backend is running on port 8000.`,
          error: String(err),
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopyQuery = (queryObj: any, messageId: string) => {
    navigator.clipboard.writeText(JSON.stringify(queryObj, null, 2));
    setCopiedQueryId(messageId);
    setTimeout(() => setCopiedQueryId(null), 2000);
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'welcome-reset',
        sender: 'assistant',
        text: 'Chat history cleared. How can I assist you with incidents or users data?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  return (
    <>
      {/* Floating Trigger Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px 20px',
            borderRadius: '9999px',
            background: 'linear-gradient(135deg, #0284c7 0%, #3b82f6 50%, #6366f1 100%)',
            color: '#ffffff',
            border: '1px solid rgba(255, 255, 255, 0.25)',
            boxShadow: '0 10px 25px -5px rgba(56, 189, 248, 0.5), 0 0 20px rgba(99, 102, 241, 0.3)',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '14px',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
        >
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Bot size={20} />
            <span
              style={{
                position: 'absolute',
                top: '-3px',
                right: '-3px',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: '#10b981',
                boxShadow: '0 0 8px #10b981'
              }}
            />
          </div>
          <span>NOC AI Agent</span>
          <Sparkles size={16} style={{ opacity: 0.9 }} />
        </button>
      )}

      {/* Chat Popup Window */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            width: isExpanded ? '540px' : '400px',
            maxWidth: 'calc(100vw - 32px)',
            height: isExpanded ? '660px' : '530px',
            maxHeight: 'calc(100vh - 48px)',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#0a0f1d',
            borderRadius: '16px',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            boxShadow:
              '0 25px 50px -12px rgba(0, 0, 0, 0.85), 0 0 35px rgba(56, 189, 248, 0.15)',
            overflow: 'hidden',
            backdropFilter: 'blur(20px)',
            animation: 'fadeIn 0.25s ease-out'
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: '14px 18px',
              background:
                'linear-gradient(135deg, rgba(14, 23, 42, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  background: 'linear-gradient(135deg, #0284c7, #6366f1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                  boxShadow: '0 0 12px rgba(56, 189, 248, 0.4)'
                }}
              >
                <Bot size={20} />
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <h3
                    style={{
                      fontSize: '14px',
                      fontWeight: 700,
                      color: '#f8fafc',
                      margin: 0,
                      letterSpacing: '-0.01em'
                    }}
                  >
                    NOC Database AI
                  </h3>
                  <span
                    style={{
                      display: 'inline-block',
                      width: '7px',
                      height: '7px',
                      borderRadius: '50%',
                      backgroundColor: '#10b981',
                      boxShadow: '0 0 6px #10b981'
                    }}
                  />
                </div>
                <p style={{ fontSize: '11px', color: '#94a3b8', margin: 0 }}>
                  incidents & users • Natural Language MongoDB
                </p>
              </div>
            </div>

            {/* Header Control Buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                onClick={clearChat}
                title="Clear Chat"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: '6px',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <Trash2 size={15} />
              </button>

              <button
                onClick={() => setIsExpanded(!isExpanded)}
                title={isExpanded ? 'Normal view' : 'Expand view'}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: '6px',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {isExpanded ? <Minimize2 size={15} /> : <Layers size={15} />}
              </button>

              <button
                onClick={() => setIsOpen(false)}
                title="Close"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: '6px',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <X size={17} />
              </button>
            </div>
          </div>

          {/* Quick Starter Suggestions */}
          <div
            style={{
              padding: '8px 14px',
              backgroundColor: 'rgba(15, 23, 42, 0.6)',
              borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
              display: 'flex',
              gap: '6px',
              overflowX: 'auto',
              whiteSpace: 'nowrap',
              scrollbarWidth: 'none'
            }}
          >
            {SAMPLE_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(q)}
                style={{
                  fontSize: '11px',
                  padding: '4px 10px',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(56, 189, 248, 0.08)',
                  color: '#38bdf8',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                  cursor: 'pointer',
                  flexShrink: 0,
                  transition: 'all 0.2s ease'
                }}
              >
                {q}
              </button>
            ))}
          </div>

          {/* Messages Container */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}
          >
            {messages.map(msg => {
              const isUser = msg.sender === 'user';
              const isExpandedQuery = expandedQueryId === msg.id;
              const pipelineData = msg.pipeline || msg.query;

              return (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '100%'
                  }}
                >
                  <div
                    style={{
                      maxWidth: '88%',
                      padding: '10px 14px',
                      borderRadius: isUser ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                      backgroundColor: isUser
                        ? '#0284c7'
                        : 'rgba(30, 41, 59, 0.85)',
                      color: isUser ? '#ffffff' : '#f1f5f9',
                      fontSize: '13px',
                      lineHeight: '1.45',
                      border: isUser
                        ? '1px solid rgba(255, 255, 255, 0.15)'
                        : '1px solid rgba(255, 255, 255, 0.08)',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)',
                      wordBreak: 'break-word'
                    }}
                  >
                    <p style={{ margin: 0 }}>{msg.text}</p>

                    {/* Query Details Accordion */}
                    {pipelineData && (
                      <div
                        style={{
                          marginTop: '8px',
                          paddingTop: '8px',
                          borderTop: '1px solid rgba(255, 255, 255, 0.1)'
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '8px'
                          }}
                        >
                          <button
                            onClick={() =>
                              setExpandedQueryId(isExpandedQuery ? null : msg.id)
                            }
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: '#38bdf8',
                              fontSize: '11px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: 0,
                              fontWeight: 600
                            }}
                          >
                            <Database size={12} />
                            <span>
                              {msg.collection ? `${msg.collection}` : 'MongoDB Pipeline'}
                            </span>
                            {isExpandedQuery ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          </button>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            {msg.rows && (
                              <span
                                style={{
                                  fontSize: '10px',
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  backgroundColor: 'rgba(16, 185, 129, 0.15)',
                                  color: '#34d399',
                                  fontWeight: 600
                                }}
                              >
                                {msg.rows.length} row{msg.rows.length !== 1 ? 's' : ''}
                              </span>
                            )}
                            <button
                              onClick={() => handleCopyQuery(pipelineData, msg.id)}
                              title="Copy Query JSON"
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: '#94a3b8',
                                cursor: 'pointer',
                                padding: '2px',
                                display: 'flex',
                                alignItems: 'center'
                              }}
                            >
                              {copiedQueryId === msg.id ? (
                                <Check size={12} color="#10b981" />
                              ) : (
                                <Copy size={12} />
                              )}
                            </button>
                          </div>
                        </div>

                        {isExpandedQuery && (
                          <pre
                            style={{
                              marginTop: '6px',
                              padding: '8px',
                              borderRadius: '6px',
                              backgroundColor: '#050811',
                              color: '#38bdf8',
                              fontSize: '10px',
                              fontFamily: 'monospace',
                              overflowX: 'auto',
                              border: '1px solid rgba(56, 189, 248, 0.2)',
                              maxHeight: '140px'
                            }}
                          >
                            {JSON.stringify(
                              {
                                collection: msg.collection || 'incidents',
                                pipeline: pipelineData
                              },
                              null,
                              2
                            )}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>

                  <span
                    style={{
                      fontSize: '10px',
                      color: '#64748b',
                      marginTop: '4px',
                      padding: '0 4px'
                    }}
                  >
                    {msg.timestamp}
                  </span>
                </div>
              );
            })}

            {/* Typing / Loading indicator */}
            {loading && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  alignSelf: 'flex-start',
                  padding: '10px 14px',
                  borderRadius: '14px 14px 14px 2px',
                  backgroundColor: 'rgba(30, 41, 59, 0.85)',
                  border: '1px solid rgba(255, 255, 255, 0.08)'
                }}
              >
                <Loader2 size={16} className="animate-spin" color="#38bdf8" />
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>
                  Querying MongoDB & reasoning with AI...
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Footer Input Form */}
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: '#0c1222',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about incidents, locations, technicians, users..."
              disabled={loading}
              style={{
                flex: 1,
                padding: '10px 14px',
                borderRadius: '8px',
                backgroundColor: '#162032',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#f8fafc',
                fontSize: '13px',
                outline: 'none',
                transition: 'border 0.2s'
              }}
              onFocus={e => (e.target.style.borderColor = '#38bdf8')}
              onBlur={e => (e.target.style.borderColor = 'rgba(255, 255, 255, 0.12)')}
            />

            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '8px',
                backgroundColor: input.trim() && !loading ? '#0284c7' : '#1e293b',
                color: '#ffffff',
                border: 'none',
                cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s ease',
                boxShadow:
                  input.trim() && !loading ? '0 0 12px rgba(2, 132, 199, 0.4)' : 'none'
              }}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
