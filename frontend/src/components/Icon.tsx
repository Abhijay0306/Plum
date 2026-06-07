import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement> & { size?: number }

const base = (size: number, paths: React.ReactNode, props: IconProps) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.75}
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    {paths}
  </svg>
)

export function IconMenu({ size = 18, ...p }: IconProps) {
  return base(size, <><line x1="4" y1="6" x2="20" y2="6" /><line x1="4" y1="12" x2="20" y2="12" /><line x1="4" y1="18" x2="20" y2="18" /></>, p)
}

export function IconSearch({ size = 18, ...p }: IconProps) {
  return base(size, <><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></>, p)
}

export function IconPlus({ size = 18, ...p }: IconProps) {
  return base(size, <><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></>, p)
}

export function IconList({ size = 18, ...p }: IconProps) {
  return base(size, <><line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" /><line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" /></>, p)
}

export function IconZap({ size = 18, ...p }: IconProps) {
  return base(size, <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />, p)
}

export function IconCheck({ size = 18, ...p }: IconProps) {
  return base(size, <polyline points="20 6 9 17 4 12" />, p)
}

export function IconX({ size = 18, ...p }: IconProps) {
  return base(size, <><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></>, p)
}

export function IconArrowLeft({ size = 18, ...p }: IconProps) {
  return base(size, <><line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" /></>, p)
}

export function IconUpload({ size = 18, ...p }: IconProps) {
  return base(size, <><polyline points="16 16 12 12 8 16" /><line x1="12" y1="12" x2="12" y2="21" /><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" /></>, p)
}

export function IconPlay({ size = 18, ...p }: IconProps) {
  return base(size, <polygon points="5 3 19 12 5 21 5 3" />, p)
}

export function IconRefresh({ size = 18, ...p }: IconProps) {
  return base(size, <><polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" /></>, p)
}

export function IconFile({ size = 18, ...p }: IconProps) {
  return base(size, <><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" /><polyline points="13 2 13 9 20 9" /></>, p)
}

export function IconChevronDown({ size = 16, ...p }: IconProps) {
  return base(size, <polyline points="6 9 12 15 18 9" />, p)
}

export function IconChevronUp({ size = 16, ...p }: IconProps) {
  return base(size, <polyline points="18 15 12 9 6 15" />, p)
}

export function IconAlertTriangle({ size = 18, ...p }: IconProps) {
  return base(size, <><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>, p)
}
