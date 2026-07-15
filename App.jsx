import React, { useEffect, useState, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  MessageSquare, Plus, FileText, Layers, Activity, Database,
  Moon, Sun, Mic, Send, ChevronDown, ChevronUp, RefreshCw,
  User, Calendar, Clock, Smile, Meh, Frown, Sparkles, CheckCircle, Terminal
} from 'lucide-react';
import {
  fetchMetadata, fetchInteractions, submitFormInteraction,
  sendChatMessage, transcribeVoiceNote, toggleTheme,
  toggleHistoryExpanded, updateFormField, toggleMaterialShared,
  updateSampleDistributed, loadPastInteractionIntoForm, resetForm,
  addLocalUserMessage
} from './store/crmSlice';
import './App.css';

export default function App() {
  const dispatch = useDispatch();
  
  // Select store values
  const { hcps, materials, samples, interactions, currentForm, chat, ui } = useSelector(state => state.crm);
  const [chatInput, setChatInput] = useState('');
  const [expandedLogs, setExpandedLogs] = useState({});
  
  const messagesEndRef = useRef(null);
  
  // Fetch metadata and interactions history on mount
  useEffect(() => {
    dispatch(fetchMetadata());
    dispatch(fetchInteractions());
  }, [dispatch]);

  // Set theme class on body
  useEffect(() => {
    document.body.setAttribute('data-theme', ui.theme);
  }, [ui.theme]);

  // Auto-scroll chat to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat.messages, chat.isTyping]);

  // Handle Form Change
  const handleInputChange = (field, value) => {
    dispatch(updateFormField({ field, value }));
  };

  // Submit form manually
  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!currentForm.hcp_id) {
      alert("Please select a Healthcare Professional (HCP) first.");
      return;
    }
    dispatch(submitFormInteraction(currentForm));
  };

  // Reset form to log a new interaction
  const handleResetForm = () => {
    dispatch(resetForm());
  };

  // Send message to AI assistant
  const handleSendChat = (text) => {
    const msg = text || chatInput;
    if (!msg.trim()) return;
    
    dispatch(addLocalUserMessage(msg));
    dispatch(sendChatMessage({ message: msg, formState: currentForm }));
    setChatInput('');
  };

  // Trigger simulated voice-to-text summarization
  const handleVoiceNoteSubmit = () => {
    dispatch(transcribeVoiceNote(currentForm));
  };

  // Toggle visibility of specific message trace logs
  const toggleLogView = (msgId) => {
    setExpandedLogs(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  // Load past logged interaction into the edit state
  const handleLoadPastInteraction = (interaction) => {
    dispatch(loadPastInteractionIntoForm(interaction));
    // Scroll form back to top
    document.querySelector('.form-scrollable')?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="app-container">
      {/* Header bar */}
      <header className="app-header">
        <div className="header-brand">
          <Activity size={24} color="#6366f1" />
          <h1>AI-First CRM - HCP Log Interaction</h1>
        </div>
        <div className="header-actions">
          <div className="db-badge">
            <Database size={14} />
            <span>SQLite Connected</span>
          </div>
          <button className="theme-toggle-btn" onClick={() => dispatch(toggleTheme())}>
            {ui.theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </header>

      {/* Main split-screen grid layout */}
      <main className="main-layout">
        {/* Left Side: Structured Form */}
        <section className="panel-card">
          <h2>
            <FileText size={20} color="#6366f1" />
            <span>Interaction Details {currentForm.id && <span style={{fontSize:'0.8rem', color:'var(--border-focus)'}}>(Editing Record #{currentForm.id})</span>}</span>
          </h2>
          
          <form onSubmit={handleFormSubmit} className="form-scrollable">
            {/* HCP Selector */}
            <div className="form-group">
              <label>HCP Name & Specialty</label>
              <select
                className="form-input"
                value={currentForm.hcp_id || ''}
                onChange={(e) => handleInputChange('hcp_id', e.target.value ? parseInt(e.target.value) : '')}
                required
              >
                <option value="">Select or search HCP...</option>
                {hcps.map(h => (
                  <option key={h.id} value={h.id}>
                    {h.name} - {h.specialty} ({h.hospital})
                  </option>
                ))}
              </select>
            </div>

            {/* Row: Type, Date, Time */}
            <div className="form-group-row">
              <div className="form-group">
                <label>Interaction Type</label>
                <select
                  className="form-input"
                  value={currentForm.interaction_type}
                  onChange={(e) => handleInputChange('interaction_type', e.target.value)}
                >
                  <option value="Meeting">Meeting</option>
                  <option value="Call">Call</option>
                  <option value="Email">Email</option>
                  <option value="Phone">Phone</option>
                </select>
              </div>
              <div className="form-group-row">
                <div className="form-group">
                  <label>Date</label>
                  <input
                    type="date"
                    className="form-input"
                    value={currentForm.date}
                    onChange={(e) => handleInputChange('date', e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Time</label>
                  <input
                    type="time"
                    className="form-input"
                    value={currentForm.time}
                    onChange={(e) => handleInputChange('time', e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            {/* Attendees */}
            <div className="form-group">
              <label>Attendees</label>
              <input
                type="text"
                placeholder="Enter attendee names..."
                className="form-input"
                value={currentForm.attendees}
                onChange={(e) => handleInputChange('attendees', e.target.value)}
              />
            </div>

            {/* Topics Discussed */}
            <div className="form-group">
              <label>Topics Discussed</label>
              <textarea
                placeholder="Key points discussed..."
                className="form-input"
                rows={3}
                value={currentForm.topics_discussed}
                onChange={(e) => handleInputChange('topics_discussed', e.target.value)}
              />
            </div>

            {/* Simulated Voice Recognition consent section */}
            <div className="voice-note-section">
              <div className="voice-note-info">
                <span className="voice-note-title">Voice Note Summarizer</span>
                <span className="voice-note-desc">Fills the CRM fields using simulated dictation transcript.</span>
              </div>
              <button type="button" className="voice-btn" onClick={handleVoiceNoteSubmit}>
                <Mic size={14} />
                <span>Dictate (Mock Voice)</span>
              </button>
            </div>

            {/* Shared Materials */}
            <div className="form-group">
              <label>Materials Shared / Sales Brochures</label>
              <div className="checklist-container">
                {materials.map(m => (
                  <label key={m.id} className="checklist-item">
                    <input
                      type="checkbox"
                      checked={currentForm.materials_shared.includes(m.id)}
                      onChange={() => dispatch(toggleMaterialShared(m.id))}
                    />
                    <span>{m.name} ({m.type})</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Samples Distributed */}
            <div className="form-group">
              <label>Samples Distributed</label>
              <div className="checklist-container">
                {samples.map(s => {
                  const selection = currentForm.samples_distributed.find(item => item.sample_id === s.id);
                  const qty = selection ? selection.quantity : 0;
                  return (
                    <div key={s.id} className="sample-row">
                      <div className="sample-name-label">
                        <span>{s.name} ({s.dosage})</span>
                        <span className="sample-stock">Available stock: {s.stock}</span>
                      </div>
                      <div className="counter-controls">
                        <button
                          type="button"
                          className="counter-btn"
                          onClick={() => dispatch(updateSampleDistributed({ sampleId: s.id, quantity: qty - 1 }))}
                        >
                          -
                        </button>
                        <span className="counter-value">{qty}</span>
                        <button
                          type="button"
                          className="counter-btn"
                          onClick={() => {
                            if (qty >= s.stock) {
                              alert("Cannot distribute more than available stock.");
                              return;
                            }
                            dispatch(updateSampleDistributed({ sampleId: s.id, quantity: qty + 1 }));
                          }}
                        >
                          +
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Sentiment */}
            <div className="form-group">
              <label>Observed/Inferred HCP Sentiment</label>
              <div className="sentiment-row">
                <button
                  type="button"
                  className={`sentiment-btn positive ${currentForm.sentiment === 'Positive' ? 'active' : ''}`}
                  onClick={() => handleInputChange('sentiment', 'Positive')}
                >
                  <Smile size={16} />
                  <span>Positive</span>
                </button>
                <button
                  type="button"
                  className={`sentiment-btn neutral ${currentForm.sentiment === 'Neutral' ? 'active' : ''}`}
                  onClick={() => handleInputChange('sentiment', 'Neutral')}
                >
                  <Meh size={16} />
                  <span>Neutral</span>
                </button>
                <button
                  type="button"
                  className={`sentiment-btn negative ${currentForm.sentiment === 'Negative' ? 'active' : ''}`}
                  onClick={() => handleInputChange('sentiment', 'Negative')}
                >
                  <Frown size={16} />
                  <span>Negative</span>
                </button>
              </div>
            </div>

            {/* Outcomes */}
            <div className="form-group">
              <label>Outcomes / Agreements</label>
              <textarea
                placeholder="Core agreements, outcomes or doctors responses..."
                className="form-input"
                rows={2}
                value={currentForm.outcomes}
                onChange={(e) => handleInputChange('outcomes', e.target.value)}
              />
            </div>

            {/* Follow up actions */}
            <div className="form-group">
              <label>Follow-Up Actions</label>
              <textarea
                placeholder="Enter next tasks or follow-ups..."
                className="form-input"
                rows={2}
                value={currentForm.follow_up_actions}
                onChange={(e) => handleInputChange('follow_up_actions', e.target.value)}
              />
            </div>

            {/* Action buttons */}
            <div className="form-actions">
              <button type="button" className="btn-secondary" onClick={handleResetForm}>
                Clear / Log New
              </button>
              <button type="submit" className="btn-primary" disabled={ui.loading}>
                {ui.loading ? 'Saving...' : currentForm.id ? 'Save Changes' : 'Log Interaction'}
              </button>
            </div>
          </form>
        </section>

        {/* Right Side: AI Assistant Conversational Log */}
        <section className="panel-card">
          <h2>
            <MessageSquare size={20} color="#6366f1" />
            <span>AI Assistant (Log via Chat)</span>
          </h2>
          
          <div className="chat-container">
            {/* Chat Bubble Log */}
            <div className="chat-messages">
              {chat.messages.map((msg) => (
                <div key={msg.id} className={`chat-bubble ${msg.sender}`}>
                  <div className="msg-header">
                    <span>{msg.sender === 'user' ? 'Sales Rep' : 'AI Assistant'}</span>
                    <span className="msg-time">{msg.timestamp}</span>
                  </div>
                  
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>

                  {/* Render suggestions if any */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="suggestions-panel">
                      {msg.suggestions.map((sug, idx) => (
                        <button
                          key={idx}
                          className="suggestion-chip"
                          onClick={() => handleSendChat(sug)}
                        >
                          <Sparkles size={10} style={{marginRight:'4px'}} />
                          {sug}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Collapsible Agent execution log (LangGraph Trace logs) */}
                  {msg.logs && msg.logs.length > 0 && (
                    <div className="logs-collapsible">
                      <button
                        type="button"
                        className="logs-trigger"
                        onClick={() => toggleLogView(msg.id)}
                      >
                        <span style={{display:'flex', alignItems:'center', gap:'4px'}}>
                          <Terminal size={12} />
                          {expandedLogs[msg.id] ? 'Hide LangGraph Agent Trace' : 'View LangGraph Agent Trace'}
                        </span>
                        {expandedLogs[msg.id] ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                      
                      {expandedLogs[msg.id] && (
                        <div className="console-block">
                          {msg.logs.map((logLine, index) => (
                            <div key={index}>{logLine}</div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              
              {/* Typing indicator animation */}
              {chat.isTyping && (
                <div className="typing-indicator">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Chat message input bar */}
            <div className="chat-input-row">
              <input
                type="text"
                placeholder="Describe interaction or ask a query..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
              />
              <button className="log-chat-btn" onClick={() => handleSendChat()}>
                <Send size={14} />
                <span>Log</span>
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Bottom Tray: Database Feeds / History Panel */}
      <section className="history-section">
        <div className="history-header" onClick={() => dispatch(toggleHistoryExpanded())}>
          <div className="history-title">
            <Database size={18} color="#6366f1" />
            <span>Database Interactions Feed</span>
            <span className="history-count">{interactions.length} Logs</span>
          </div>
          {ui.historyExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>
        
        {ui.historyExpanded && (
          <div className="history-content">
            {interactions.length === 0 ? (
              <div className="no-history-placeholder">
                <RefreshCw size={24} style={{ animation: 'spin 2s linear infinite', marginBottom: '8px' }} />
                <p>No interactions logged yet. Log your first meeting above.</p>
              </div>
            ) : (
              <div className="history-grid">
                {interactions.map(item => (
                  <div key={item.id} className="history-item-card">
                    <div className="history-card-header">
                      <div>
                        <div className="history-hcp-name">{item.hcp.name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {item.hcp.specialty} | {item.hcp.hospital}
                        </div>
                      </div>
                      <span className={`sentiment-badge ${item.sentiment.toLowerCase()}`}>
                        {item.sentiment}
                      </span>
                    </div>

                    <div className="history-card-topics">
                      <strong>Discussed:</strong> {item.topics_discussed || 'N/A'}
                    </div>

                    <div className="history-card-details">
                      <div className="history-card-detail-item">
                        <strong>Type:</strong> {item.interaction_type}
                      </div>
                      <div className="history-card-detail-item">
                        <strong>Date/Time:</strong> {item.date} at {item.time}
                      </div>
                      {item.materials.length > 0 && (
                        <div className="history-card-detail-item">
                          <strong>Brochures:</strong> {item.materials.map(m => m.name.split(' ')[0]).join(', ')}
                        </div>
                      )}
                      {item.samples.length > 0 && (
                        <div className="history-card-detail-item">
                          <strong>Samples:</strong> {item.samples.map(s => `${s.name.split(' ')[0]} (x${s.quantity})`).join(', ')}
                        </div>
                      )}
                      {item.follow_up_tasks.length > 0 && (
                        <div className="history-card-detail-item">
                          <strong>Follow Up Action:</strong> {item.follow_up_tasks[0].description} (Due: {item.follow_up_tasks[0].due_date})
                        </div>
                      )}
                    </div>

                    <div className="history-card-actions">
                      <button type="button" onClick={() => handleLoadPastInteraction(item)}>
                        Edit / Load
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
