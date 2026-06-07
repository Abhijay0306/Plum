import React, { useRef, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, NavLink, useLocation, useNavigate } from 'react-router-dom'
import SubmitClaim from './pages/SubmitClaim'
import ClaimsList from './pages/ClaimsList'
import ClaimDetail from './pages/ClaimDetail'
import TestCases from './pages/TestCases'
import ErrorBoundary from './components/ErrorBoundary'
import { IconMenu, IconPlus, IconList, IconZap, IconSearch } from './components/Icon'

const NAV_ITEMS = [
  { to: '/',           label: 'Submit Claim',   icon: IconPlus, end: true  },
  { to: '/claims',     label: 'Claims History', icon: IconList, end: false },
  { to: '/test-cases', label: 'Test Cases',     icon: IconZap,  end: false },
]

const PAGE_TITLES: Record<string, string> = {
  '/': 'Submit Claim',
  '/claims': 'Claims History',
  '/test-cases': 'Test Cases',
}

function Sidebar({ collapsed }: { collapsed: boolean }) {
  return (
    <aside style={{
      width: collapsed ? 64 : 240,
      flexShrink: 0,
      background: 'var(--surface-sidebar)',
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      position: 'sticky',
      top: 0,
      transition: 'width 0.2s ease',
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{ padding: collapsed ? '24px 0' : '24px 20px', display: 'flex', alignItems: 'center', gap: 10, minHeight: 72 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8, flexShrink: 0,
          background: 'var(--plum-500)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, color: '#fff', fontWeight: 700,
          marginLeft: collapsed ? 'auto' : 0, marginRight: collapsed ? 'auto' : 0,
        }}>P</div>
        {!collapsed && (
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: 15, lineHeight: 1.2 }}>Plum</div>
            <div style={{ color: 'var(--plum-300)', fontSize: 10, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Claims</div>
          </div>
        )}
      </div>

      <div style={{ width: '100%', height: 1, background: 'rgba(255,255,255,0.06)', marginBottom: 8 }} />

      {/* Nav items */}
      <nav style={{ flex: 1, padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            title={collapsed ? label : undefined}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: collapsed ? '10px 0' : '10px 12px',
              justifyContent: collapsed ? 'center' : 'flex-start',
              borderRadius: 8,
              color: isActive ? '#fff' : 'rgba(255,255,255,0.5)',
              background: isActive ? 'var(--surface-sidebar-active)' : 'transparent',
              borderLeft: isActive ? '2px solid var(--plum-400)' : '2px solid transparent',
              fontSize: 14,
              fontWeight: isActive ? 600 : 400,
              transition: 'all 0.1s',
              cursor: 'pointer',
            })}
          >
            <Icon size={16} style={{ flexShrink: 0 }} />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div style={{ width: '100%', height: 1, background: 'rgba(255,255,255,0.06)' }} />

      {/* Footer label */}
      <div style={{ padding: collapsed ? '16px 0' : '16px 20px', display: 'flex', alignItems: 'center', justifyContent: collapsed ? 'center' : 'flex-start' }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8, flexShrink: 0,
          background: 'rgba(255,255,255,0.06)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--plum-300)' }}>A</span>
        </div>
        {!collapsed && (
          <div style={{ marginLeft: 10 }}>
            <div style={{ color: '#fff', fontSize: 13, fontWeight: 500 }}>Claims Agent</div>
            <div style={{ color: 'var(--plum-300)', fontSize: 11 }}>plumhq.com</div>
          </div>
        )}
      </div>
    </aside>
  )
}

function TopBar({ onToggle }: { onToggle: () => void }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const parts = location.pathname.split('/').filter(Boolean)
  const title = PAGE_TITLES[location.pathname] ?? (parts[0] === 'claims' && parts[1] ? 'Claim Detail' : 'Plum Claims')

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    navigate(q ? `/claims?q=${encodeURIComponent(q)}` : '/claims')
  }

  return (
    <header style={{
      height: 56, flexShrink: 0,
      background: 'var(--surface-card)',
      borderBottom: '1px solid var(--border-default)',
      display: 'flex', alignItems: 'center',
      padding: '0 20px', gap: 12,
      position: 'sticky', top: 0, zIndex: 100,
    }}>
      <button
        onClick={onToggle}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', padding: '6px', borderRadius: 6, display: 'flex', alignItems: 'center' }}
        title="Toggle sidebar"
      >
        <IconMenu size={18} />
      </button>

      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1 }}>
        {parts.length > 1 ? (
          <>
            <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
              {PAGE_TITLES['/' + parts[0]] ?? parts[0]}
            </span>
            <span style={{ color: 'var(--text-disabled)', fontSize: 13 }}>›</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</span>
          </>
        ) : (
          <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>{title}</span>
        )}
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--surface-sunken)', padding: '6px 12px',
          borderRadius: 'var(--radius-md)', border: '1px solid var(--border-default)',
          width: 220,
        }}>
          <IconSearch size={14} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search claims…"
            style={{
              background: 'none', border: 'none', outline: 'none',
              fontSize: 13, color: 'var(--text-primary)', width: '100%',
              fontFamily: 'var(--font-ui)',
            }}
          />
        </div>
      </form>
    </header>
  )
}

function Shell() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar collapsed={collapsed} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar onToggle={() => setCollapsed(c => !c)} />
        <main style={{ flex: 1, overflowY: 'auto', background: 'var(--surface-base)' }}>
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<SubmitClaim />} />
              <Route path="/claims" element={<ClaimsList />} />
              <Route path="/claims/:claimId" element={<ClaimDetail />} />
              <Route path="/test-cases" element={<TestCases />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
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
