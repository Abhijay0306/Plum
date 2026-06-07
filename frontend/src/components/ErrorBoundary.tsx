import { Component } from 'react'
import type { ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean; message: string }

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message }
  }

  override render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div style={{
        padding: 40, textAlign: 'center',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16,
      }}>
        <div style={{
          width: 48, height: 48, borderRadius: '50%',
          background: 'var(--status-rejected-bg)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--status-rejected-fg)', fontSize: 22, fontWeight: 700,
        }}>!</div>
        <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>
          Something went wrong
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', maxWidth: 380 }}>
          {this.state.message || 'An unexpected error occurred while rendering this page.'}
        </div>
        <button
          onClick={() => this.setState({ hasError: false, message: '' })}
          style={{
            padding: '8px 20px', borderRadius: 'var(--radius-md)', border: 'none',
            background: 'var(--plum-500)', color: '#fff', fontWeight: 600,
            fontSize: 13, cursor: 'pointer', fontFamily: 'var(--font-ui)',
          }}
        >
          Try again
        </button>
      </div>
    )
  }
}
