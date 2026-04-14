import { useState } from 'react'

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register'

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Something went wrong.')
        return
      }

      localStorage.setItem('econagent_token', data.token)
      localStorage.setItem('econagent_user_id', data.user_id)
      onAuth(data.token, data.user_id, data.email)
    } catch {
      setError('Cannot reach the server. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-[#f7f7f8]">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 py-4 px-12">
        <div className="select-none leading-none">
          <span className="text-[48px] font-bold tracking-tight text-black">Soft </span>
          <span className="text-[48px] font-bold tracking-tight text-[#DC2626]">Econ</span>
          <span className="text-[48px] font-bold tracking-tight text-black">Agent</span>
        </div>
        <div className="text-[13px] text-black mt-2">
          powered by <span className="text-[#DC2626] italic font-semibold">AI</span>
        </div>
      </header>

      {/* Card */}
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm w-full max-w-sm p-8">
          <h2 className="text-[20px] font-bold text-gray-900 mb-1">
            {mode === 'login' ? 'Welcome back' : 'Create an account'}
          </h2>
          <p className="text-[13px] text-gray-400 mb-6">
            {mode === 'login'
              ? 'Sign in to access your research history.'
              : 'Start your economic research journey.'}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[12px] font-medium text-gray-600 mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-[14px] outline-none focus:border-[#DC2626]/50 transition-colors"
              />
            </div>

            <div>
              <label className="block text-[12px] font-medium text-gray-600 mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder={mode === 'register' ? 'At least 6 characters' : '••••••••'}
                className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-[14px] outline-none focus:border-[#DC2626]/50 transition-colors"
              />
            </div>

            {error && (
              <p className="text-[12px] text-red-500 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#DC2626] hover:bg-[#B91C1C] disabled:opacity-50 text-white font-bold text-[14px] py-2.5 rounded-xl transition-colors"
            >
              {loading ? '...' : mode === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>

          <p className="text-center text-[12px] text-gray-400 mt-5">
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="text-[#DC2626] font-medium hover:underline"
            >
              {mode === 'login' ? 'Sign up' : 'Sign in'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
