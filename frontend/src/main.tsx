import React, { useRef, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import SubmitClaim from './pages/SubmitClaim'
import ClaimsList from './pages/ClaimsList'
import ClaimDetail from './pages/ClaimDetail'
import TestCases from './pages/TestCases'
import ErrorBoundary from './components/ErrorBoundary'
import { IconPlus, IconList, IconZap, IconSearch } from './components/Icon'

const NAV_ITEMS = [
  { to: '/',           label: 'Submit Claim',   icon: IconPlus, end: true  },
  { to: '/claims',     label: 'Claims History', icon: IconList, end: false },
  { to: '/test-cases', label: 'Test Cases',     icon: IconZap,  end: false },
]

function FloatingNav() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    navigate(q ? `/claims?q=${encodeURIComponent(q)}` : '/claims')
    setSearchOpen(false)
    setQuery('')
  }

  return (
    <nav style={{
      position: 'fixed',
      top: 20,
      left: 24,
      right: 24,
      zIndex: 200,
      background: '#FFFFFF',
      borderRadius: 40,
      boxShadow: 'rgba(0, 0, 0, 0.06) 0px 4px 24px 0px',
      display: 'flex',
      alignItems: 'center',
      height: 60,
      padding: '0 24px',
      gap: 0,
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0, marginRight: 32 }}>
        <div style={{
          width: 34, height: 34, borderRadius: '50%',
          background: '#141413',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 15, color: '#F3F0EE', fontWeight: 700, letterSpacing: '-0.02em',
        }}>P</div>
        <div>
          <div style={{ color: '#141413', fontWeight: 700, fontSize: 15, lineHeight: 1.15, letterSpacing: '-0.02em' }}>Plum</div>
          <div style={{ color: '#696969', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', lineHeight: 1 }}>Claims</div>
        </div>
      </div>

      {/* Nav links */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, flex: 1 }}>
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            style={({ isActive }) => ({
              display: 'inline-flex',
              alignItems: 'center',
              gap: 7,
              padding: '8px 16px',
              borderRadius: 999,
              background: isActive ? '#141413' : 'transparent',
              color: isActive ? '#F3F0EE' : '#696969',
              fontSize: 14,
              fontWeight: isActive ? 600 : 500,
              letterSpacing: isActive ? '-0.01em' : 'normal',
              transition: 'all 0.15s',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            })}
          >
            <Icon size={14} style={{ flexShrink: 0 }} />
            {label}
          </NavLink>
        ))}
      </div>

      {/* Search */}
      <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>
        {searchOpen ? (
          <form onSubmit={handleSearch} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              background: '#F3F0EE',
              padding: '8px 16px',
              borderRadius: 999,
              border: '1.5px solid #141413',
              width: 220,
            }}>
              <IconSearch size={13} style={{ color: '#696969', flexShrink: 0 }} />
              <input
                ref={inputRef}
                autoFocus
                value={query}
                onChange={e => setQuery(e.target.value)}
                onBlur={() => { if (!query) setSearchOpen(false) }}
                placeholder="Search claims…"
                style={{
                  background: 'none', border: 'none', outline: 'none',
                  fontSize: 13, color: '#141413', width: '100%',
                  fontFamily: 'var(--font-ui)',
                }}
              />
            </div>
          </form>
        ) : (
          <button
            onClick={() => { setSearchOpen(true); setTimeout(() => inputRef.current?.focus(), 50) }}
            style={{
              width: 40, height: 40, borderRadius: '50%',
              background: 'transparent',
              border: '1.5px solid #D1CDC7',
              cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#696969',
              transition: 'border-color 0.15s, color 0.15s',
            }}
            title="Search claims"
          >
            <IconSearch size={15} />
          </button>
        )}
      </div>
    </nav>
  )
}

function Shell() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--surface-base)' }}>
      <FloatingNav />
      <main style={{ paddingTop: 100 }}>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<SubmitClaim />} />
            <Route path="/claims" element={<ClaimsList />} />
            <Route path="/claims/:claimId" element={<ClaimDetail />} />
            <Route path="/test-cases" element={<TestCases />} />
          </Routes>
        </ErrorBoundary>
      </main>

      {/* Footer */}
      <footer style={{
        marginTop: 96,
        background: '#141413',
        padding: '48px 48px 40px',
      }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <p style={{
            fontSize: 22, fontWeight: 500, color: '#F3F0EE',
            letterSpacing: '-0.02em', marginBottom: 32, lineHeight: 1.3,
          }}>
            Plum Claims — powered by AI, explainable by design.
          </p>
          <div style={{
            borderTop: '1px solid rgba(255,255,255,0.12)',
            paddingTop: 20,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
          }}>
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', letterSpacing: '0.02em' }}>
              © 2024 Plum Benefits · Health insurance claims processing
            </span>
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.25)' }}>plumhq.com</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  </React.StrictMode>,
)
