import { useState, useRef, useEffect, useCallback } from 'react'
import AuthPage from './AuthPage.jsx'

const API_BASE = ''

function authHeader() {
  const token = localStorage.getItem('econagent_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatTime(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatTimestamp(iso) {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}


// ─── Markdown ────────────────────────────────────────────────────────────────

function InlineMarkdown({ text }) {
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g)
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**'))
          return <strong key={i}>{part.slice(2, -2)}</strong>
        if (part.startsWith('`') && part.endsWith('`'))
          return <code key={i} className="bg-black/5 px-1 py-0.5 rounded text-sm font-mono">{part.slice(1, -1)}</code>
        return <span key={i}>{part}</span>
      })}
    </>
  )
}

function SimpleMarkdown({ text }) {
  const lines = text.split('\n')
  const elements = []
  let key = 0
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (!line.trim()) { elements.push(<br key={key++} />); continue }
    if (line.startsWith('- ')) {
      elements.push(<li key={key++} className="ml-4 list-disc"><InlineMarkdown text={line.slice(2)} /></li>)
      continue
    }
    if (/^\d+\.\s/.test(line)) {
      elements.push(<li key={key++} className="ml-4 list-decimal"><InlineMarkdown text={line.replace(/^\d+\.\s/, '')} /></li>)
      continue
    }
    elements.push(<p key={key++}><InlineMarkdown text={line} /></p>)
  }
  return <div className="prose-message space-y-0.5 leading-relaxed">{elements}</div>
}

// ─── Task Panel Components ────────────────────────────────────────────────────

const STATUS_CONFIG = {
  pending:   { dot: 'bg-gray-300',          label: 'Pending',   text: 'text-gray-400' },
  running:   { dot: 'bg-accent animate-pulse', label: 'Running', text: 'text-accent' },
  completed: { dot: 'bg-green-400',          label: 'Done',      text: 'text-green-600' },
  failed:    { dot: 'bg-red-400',            label: 'Failed',    text: 'text-red-500' },
}

const TOOL_ICONS = {
  world_bank_api:  '🌍',
  imf_data_api:    '📊',
  oecd_api:        '🏛️',
  eurostat_api:    '🇪🇺',
  fred_api:        '🏦',
  brave_search:    '🔍',
  python_calculator: '🧮',
}

function TaskCard({ task }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = STATUS_CONFIG[task.status] || STATUS_CONFIG.pending

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm">
      {/* Header */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full text-left px-3 py-2.5 flex items-start gap-2 hover:bg-gray-50 transition-colors"
      >
        <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-1">
            <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">{task.id}</span>
            <span className={`text-[10px] font-medium ${cfg.text}`}>{cfg.label}</span>
          </div>
          <p className="text-[12px] text-gray-700 leading-snug mt-0.5 line-clamp-2">{task.description}</p>
        </div>
        <span className="text-gray-300 text-[10px] mt-1 flex-shrink-0">{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Tool calls */}
      {expanded && task.toolCalls.length > 0 && (
        <div className="border-t border-gray-50 px-3 py-2 space-y-1.5">
          {task.toolCalls.map((tc, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-[13px] flex-shrink-0">{TOOL_ICONS[tc.name] || '🔧'}</span>
              <div className="min-w-0">
                <span className="text-[11px] font-medium text-gray-600">{tc.name}</span>
                {tc.done && (
                  <span className="ml-1.5 text-[10px] text-green-500">✓</span>
                )}
                {tc.input && (
                  <p className="text-[10px] text-gray-400 truncate mt-0.5">
                    {JSON.stringify(tc.input).slice(0, 80)}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TaskPanel({ tasks, isActive }) {
  return (
    <aside className="bg-white border-l border-gray-100 flex flex-col flex-shrink-0" style={{ width: '260px' }}>
      <div className="p-4 border-b border-gray-50">
        <h2 className="text-[13px] font-bold uppercase tracking-widest text-accent text-center">
          Research Tasks
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {tasks.length === 0 && (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <p className="text-[12px] text-gray-400 leading-relaxed">
              {isActive ? 'Waiting for task plan…' : 'Tasks will appear here\nfor complex research queries'}
            </p>
          </div>
        )}
        {tasks.map(task => (
          <TaskCard key={task.id} task={task} />
        ))}
      </div>
    </aside>
  )
}

// ─── Chat Components ──────────────────────────────────────────────────────────

function Brand() {
  return (
    <div className="select-none leading-none">
      <span className="text-[48px] font-bold tracking-tight text-black">Soft </span><span className="text-[48px] font-bold tracking-tight text-accent">Econ</span><span className="text-[48px] font-bold tracking-tight text-black">Agent</span>
    </div>
  )
}

function PoweredBy() {
  return (
    <div className="text-[13px] tracking-wide text-black select-none mt-2">
      powered by <span className="text-accent italic font-semibold">AI</span>
    </div>
  )
}

function ThreadItem({ thread, active, onClick, onDelete }) {
  function handleDelete(e) {
    e.stopPropagation()
    onDelete(thread.id)
  }

  return (
    <div
      onClick={onClick}
      className={`group relative w-full text-left px-4 py-3.5 rounded-xl transition-all duration-150 cursor-pointer ${
        active ? 'bg-accent/8 border border-accent/20' : 'hover:bg-gray-50 border border-transparent'
      }`}
    >
      <p className={`text-[14px] font-medium truncate leading-snug pr-6 ${active ? 'text-accent' : 'text-gray-800'}`}>
        {thread.title}
      </p>
      <div className="flex items-center justify-between mt-1">
        <span className="text-[12px] text-gray-400">{thread.message_count} messages</span>
        <span className="text-[12px] text-gray-400">{formatTime(thread.updated_at)}</span>
      </div>
      <button
        onClick={handleDelete}
        className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-lg hover:bg-red-50 text-gray-300 hover:text-red-400"
        title="Delete chat"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}

function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-5`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-accent/10 flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
          <span className="text-accent text-[10px] font-bold">EA</span>
        </div>
      )}
      <div className={`max-w-[72%] flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-4 py-3 rounded-2xl text-[14px] leading-relaxed shadow-sm ${
          isUser ? 'bg-accent text-white rounded-br-sm' : 'bg-white text-gray-800 border border-gray-100 rounded-bl-sm'
        }`}>
          {isUser ? <p>{message.content}</p> : <SimpleMarkdown text={message.content} />}
        </div>
        <span className="text-[11px] text-gray-400 px-1">{formatTimestamp(message.created_at)}</span>
      </div>
      {isUser && (
        <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center ml-3 mt-0.5 flex-shrink-0">
          <span className="text-gray-500 text-[10px] font-bold">You</span>
        </div>
      )}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-5">
      <div className="w-7 h-7 rounded-full bg-accent/10 flex items-center justify-center mr-3 mt-0.5 flex-shrink-0">
        <span className="text-accent text-[10px] font-bold">EA</span>
      </div>
      <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      <div className="w-14 h-14 rounded-2xl bg-accent/8 flex items-center justify-center mb-5">
        <svg className="w-6 h-6 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9 9 0 100-18 9 9 0 000 18z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.5 9.5c.5-1.5 2.5-2 3.5-.5 1 1.5 0 3-2 3v1.5M12 17.5h.01" />
        </svg>
      </div>
      <h3 className="text-[15px] font-semibold text-gray-800 mb-2">Start a new conversation</h3>
      <p className="text-[13px] text-gray-400 max-w-xs leading-relaxed">
        Ask about GDP trends, trade balances, inflation dynamics, monetary policy, or any macroeconomic topic.
      </p>
    </div>
  )
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('econagent_token'))
  const [userEmail, setUserEmail] = useState('')
  const [threads, setThreads] = useState([])
  const [activeThreadId, setActiveThreadId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [tasks, setTasks] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const userId = useRef(localStorage.getItem('econagent_user_id') || '')
  const currentThreadId = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const loadThreads = useCallback(async () => {
    if (!token) return
    try {
      const res = await fetch(`${API_BASE}/api/threads`, { headers: authHeader() })
      const data = await res.json()
      setThreads(data.threads || [])
    } catch (e) {
      console.error('Failed to load threads', e)
    }
  }, [token])

  useEffect(() => { loadThreads() }, [loadThreads])

  // 未登录 → 显示登录页
  if (!token) {
    return (
      <AuthPage onAuth={(tok, uid, email) => {
        setToken(tok)
        setUserEmail(email)
        userId.current = uid
      }} />
    )
  }

  function handleLogout() {
    localStorage.removeItem('econagent_token')
    localStorage.removeItem('econagent_user_id')
    setToken(null)
    setThreads([])
    setMessages([])
    setTasks([])
  }

  async function handleSelectThread(thread) {
    setActiveThreadId(thread.id)
    currentThreadId.current = thread.id
    setMessages([])
    setTasks([])
    try {
      const res = await fetch(`${API_BASE}/api/history/${thread.id}`, { headers: authHeader() })
      const data = await res.json()
      setMessages(data.messages.map((m, i) => ({ ...m, id: `loaded-${i}` })))
    } catch (e) {
      console.error('Failed to load history', e)
    }
  }

  function handleNewChat() {
    setActiveThreadId(null)
    currentThreadId.current = null
    setMessages([])
    setTasks([])
  }

  async function handleDeleteThread(threadId) {
    try {
      await fetch(`${API_BASE}/api/threads/${threadId}`, { method: 'DELETE', headers: authHeader() })
      setThreads(prev => prev.filter(t => t.id !== threadId))
      if (threadId === activeThreadId) {
        setActiveThreadId(null)
        currentThreadId.current = null
        setMessages([])
        setTasks([])
      }
    } catch (e) {
      console.error('Failed to delete thread', e)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // ── Task state helpers ────────────────────────────────────────────────────

  function upsertTask(taskId, patch) {
    setTasks(prev => {
      const exists = prev.find(t => t.id === taskId)
      if (exists) return prev.map(t => t.id === taskId ? { ...t, ...patch } : t)
      return [...prev, { id: taskId, description: '', status: 'pending', toolCalls: [], ...patch }]
    })
  }

  function addToolCall(taskId, toolName, toolInput) {
    setTasks(prev => prev.map(t => {
      if (t.id !== taskId) return t
      return { ...t, toolCalls: [...t.toolCalls, { name: toolName, input: toolInput, done: false }] }
    }))
  }

  function markToolDone(taskId, toolName) {
    setTasks(prev => prev.map(t => {
      if (t.id !== taskId) return t
      // mark last pending call with this tool name as done
      const calls = [...t.toolCalls]
      for (let i = calls.length - 1; i >= 0; i--) {
        if (calls[i].name === toolName && !calls[i].done) {
          calls[i] = { ...calls[i], done: true }
          break
        }
      }
      return { ...t, toolCalls: calls }
    }))
  }

  // ── Send & SSE ────────────────────────────────────────────────────────────

  async function handleSend() {
    const text = input.trim()
    if (!text || isTyping) return

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsTyping(true)
    setIsStreaming(true)
    setTasks([])  // clear tasks from previous turn

    let assistantContent = ''
    const assistantId = `asst-${Date.now()}`

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        body: JSON.stringify({
          message: text,
          thread_id: currentThreadId.current,
        }),
      })

      const newThreadId = res.headers.get('X-Thread-Id')
      const newUserId = res.headers.get('X-User-Id')
      if (newThreadId) { currentThreadId.current = newThreadId; setActiveThreadId(newThreadId) }
      if (newUserId) { userId.current = newUserId; localStorage.setItem('econagent_user_id', newUserId) }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim()
          } else if (line.startsWith('data:')) {
            const raw = line.slice(5).trim()
            if (!raw) continue
            try {
              const payload = JSON.parse(raw)

              if (eventType === 'report_token' || eventType === 'chat_token') {
                assistantContent += payload.token || ''
                setMessages(prev => {
                  const existing = prev.find(m => m.id === assistantId)
                  if (existing) return prev.map(m => m.id === assistantId ? { ...m, content: assistantContent } : m)
                  return [...prev, { id: assistantId, role: 'assistant', content: assistantContent, created_at: new Date().toISOString() }]
                })
                setIsTyping(false)

              } else if (eventType === 'task_status_update') {
                upsertTask(payload.task_id, { status: payload.status })

              } else if (eventType === 'tool_call_start') {
                addToolCall(payload.task_id, payload.tool_name, payload.tool_input)

              } else if (eventType === 'tool_call_result') {
                markToolDone(payload.task_id, payload.tool_name)

              } else if (eventType === 'plan_generated') {
                // plan_generated may carry task list; pre-populate with pending status
                if (Array.isArray(payload.tasks)) {
                  setTasks(payload.tasks.map(t => ({
                    id: t.id,
                    description: t.description,
                    status: 'pending',
                    toolCalls: [],
                  })))
                }

              } else if (eventType === 'done' || eventType === 'error') {
                setIsTyping(false)
              }
            } catch {
              // ignore parse errors
            }
            eventType = ''
          }
        }
      }
    } catch (e) {
      console.error('Chat error', e)
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, something went wrong. Please check the backend is running.',
        created_at: new Date().toISOString(),
      }])
    } finally {
      setIsTyping(false)
      setIsStreaming(false)
      await loadThreads()
    }
  }

  const activeThread = threads.find(t => t.id === activeThreadId)

  return (
    <div className="h-screen flex flex-col bg-[#f7f7f8] overflow-hidden">

      {/* ── Top bar ── */}
      <header className="bg-white border-b border-gray-100 flex-shrink-0 z-10 py-4 px-12">
        <div className="flex items-end justify-between">
          <div className="flex flex-col">
            <Brand />
            <PoweredBy />
          </div>
          <div className="flex items-center gap-3 pb-1">
            {userEmail && (
              <span className="text-[12px] text-gray-400">{userEmail}</span>
            )}
            <button
              onClick={handleLogout}
              className="text-[12px] text-gray-400 hover:text-red-500 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex w-full flex-1 overflow-hidden bg-white">

          {/* ── Left Sidebar — Chat history ── */}
          <aside className="bg-white border-r border-gray-100 flex flex-col flex-shrink-0" style={{ width: '272px' }}>
            <div className="p-4 border-b border-gray-50">
              <button
                onClick={handleNewChat}
                className="w-full bg-accent hover:bg-accent-hover text-white text-[13px] font-bold py-2.5 px-4 rounded-xl shadow-sm transition-all duration-150 active:scale-95 mb-3"
              >
                Start a new chat
              </button>
              <h2 className="text-[13px] font-bold uppercase tracking-widest text-accent text-center">
                Chat history
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-1">
              {threads.length === 0 && (
                <p className="text-[12px] text-gray-400 text-center mt-6">No conversations yet</p>
              )}
              {threads.map(thread => (
                <ThreadItem
                  key={thread.id}
                  thread={thread}
                  active={thread.id === activeThreadId}
                  onClick={() => handleSelectThread(thread)}
                  onDelete={handleDeleteThread}
                />
              ))}
            </div>
          </aside>

          {/* ── Main chat area ── */}
          <main className="flex-1 flex flex-col overflow-hidden bg-[#fafafa]">
            <div className="h-12 bg-white border-b border-gray-100 flex items-center px-4 flex-shrink-0">
              <p className="text-[14px] font-medium text-gray-700 truncate">
                {activeThread?.title ?? 'New conversation'}
              </p>
              {activeThread && activeThread.message_count > 0 && (
                <span className="ml-3 text-[11px] text-gray-400 flex-shrink-0">
                  {activeThread.message_count} messages
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto px-20 py-6">
              {messages.length === 0 && !isTyping ? (
                <EmptyState />
              ) : (
                <>
                  {messages.map(msg => (
                    <MessageBubble key={msg.id} message={msg} />
                  ))}
                  {isTyping && <TypingIndicator />}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            <div className="px-20 pb-6 pt-2 flex-shrink-0">
              <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden focus-within:border-accent/40 focus-within:shadow-md transition-all duration-150">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about GDP, inflation, trade balances, monetary policy…"
                  rows={3}
                  className="w-full resize-none px-4 pt-3.5 pb-2 text-[14px] text-gray-800 placeholder-gray-400 outline-none leading-relaxed"
                />
                <div className="flex items-center justify-between px-4 pb-3">
                  <span className="text-[11px] text-gray-400">
                    Press <kbd className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-500 font-mono">↵</kbd> to send
                    &nbsp;·&nbsp;
                    <kbd className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-500 font-mono">⇧↵</kbd> for new line
                  </span>
                  <button
                    onClick={handleSend}
                    disabled={!input.trim() || isTyping}
                    className="bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed text-white text-[13px] font-medium px-5 py-2 rounded-xl transition-all duration-150 active:scale-95"
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          </main>

          {/* ── Right Sidebar — Task Panel ── */}
          <TaskPanel tasks={tasks} isActive={isStreaming} />

        </div>
      </div>
    </div>
  )
}
