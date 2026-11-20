import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Globe,
  FileCheck,
  Play,
  Atom,
  Clock,
  BarChart3,
  Menu,
  X,
  Sparkles,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '../../lib/utils'

interface NavItem {
  label: string
  path: string
  icon: LucideIcon
  exact?: boolean
}

const navItems: NavItem[] = [
  { label: 'Overview', path: '/', icon: LayoutDashboard, exact: true },
  { label: 'Applications', path: '/applications', icon: Globe },
  { label: 'Test Cases', path: '/test-cases', icon: FileCheck },
  { label: 'QAOA Optimization', path: '/optimization', icon: Atom },
  { label: 'Execution', path: '/execution', icon: Play },
  { label: 'History', path: '/history', icon: Clock },
  { label: 'Results', path: '/results', icon: BarChart3 },
]

export interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const [isMobileExpanded, setIsMobileExpanded] = useState(false)

  return (
    <>
      {/* Mobile backdrop overlay */}
      {isMobileExpanded && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden transition-opacity"
          onClick={() => setIsMobileExpanded(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'fixed top-4 left-4 bottom-4 z-40 flex flex-col',
          'bg-[#0F172A]/90 backdrop-blur-2xl border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)] rounded-[28px]',
          'transition-[width] duration-300 ease-in-out',
          isMobileExpanded ? 'w-64' : 'w-20 lg:w-64',
          className
        )}
        aria-label="Sidebar Navigation"
      >
        {/* Top Header: Logo + Toggle */}
        <div className="h-20 flex items-center justify-between px-4 lg:px-5 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-3 overflow-hidden">
            {/* Quantum dot icon */}
            <div
              className="relative flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 text-white shadow-[0_8px_20px_rgba(124,58,237,0.35)] shrink-0"
              title="QC Web Quantum Platform"
            >
              <Atom className="w-5 h-5 animate-spin [animation-duration:14s]" />
              <span className="absolute w-2 h-2 rounded-full bg-white/70 animate-ping opacity-60" />
            </div>

            {/* Logo text: hidden when collapsed */}
            <div
              className={cn(
                'flex flex-col min-w-0 transition-all duration-200',
                isMobileExpanded ? 'flex' : 'hidden lg:flex'
              )}
            >
              <div className="flex items-center gap-1.5">
                <span className="text-base font-extrabold tracking-tight text-white whitespace-nowrap">
                  QC Web
                </span>
                <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  V2
                </span>
              </div>
              <span className="text-[10px] uppercase font-semibold tracking-wider text-slate-400 truncate">
                Quantum Testing
              </span>
            </div>
          </div>

          {/* Mobile toggle button */}
          <button
            type="button"
            onClick={() => setIsMobileExpanded(!isMobileExpanded)}
            className="lg:hidden p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors shrink-0 cursor-pointer"
            aria-label={isMobileExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {isMobileExpanded ? <X className="w-5 h-5 text-white" /> : <Menu className="w-5 h-5 text-white" />}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 overflow-y-auto px-2.5 lg:px-3 py-4 space-y-1.5">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.exact}
                onClick={() => setIsMobileExpanded(false)}
                title={item.label}
                className={({ isActive }) =>
                  cn(
                    'flex items-center rounded-2xl text-sm font-medium transition-all group relative',
                    isMobileExpanded
                      ? 'gap-3 px-3.5 py-2.5 justify-start'
                      : 'gap-0 lg:gap-3 px-0 lg:px-3.5 py-2.5 justify-center lg:justify-start',
                    isActive
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold shadow-[0_8px_20px_rgba(124,58,237,0.3)]'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={cn(
                        'w-5 h-5 shrink-0 transition-colors',
                        isActive ? 'text-white' : 'text-slate-400 group-hover:text-purple-300'
                      )}
                    />
                    <span
                      className={cn(
                        'truncate transition-opacity duration-200',
                        isMobileExpanded ? 'inline' : 'hidden lg:inline'
                      )}
                    >
                      {item.label}
                    </span>
                    {isActive && (
                      <span className="hidden lg:block ml-auto w-1.5 h-1.5 rounded-full bg-white shadow-xs" />
                    )}
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Bottom Status: Simulation Mode */}
        <div className="p-3 lg:p-4 border-t border-white/10 shrink-0">
          <div
            className={cn(
              'flex items-center rounded-2xl bg-purple-950/40 border border-purple-500/20 shadow-2xs transition-all',
              isMobileExpanded
                ? 'gap-2.5 px-3 py-2.5 justify-start'
                : 'gap-0 lg:gap-2.5 px-2 lg:px-3 py-2.5 justify-center lg:justify-start'
            )}
            title="Qiskit Aer Simulator Active"
          >
            <span className="relative flex h-2.5 w-2.5 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-60" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-purple-400" />
            </span>
            <div
              className={cn(
                'flex flex-col min-w-0',
                isMobileExpanded ? 'flex' : 'hidden lg:flex'
              )}
            >
              <span className="text-xs font-bold text-white truncate flex items-center gap-1">
                Qiskit Aer <Sparkles className="w-3 h-3 text-purple-400" />
              </span>
              <span className="text-[10px] text-purple-300 font-medium">
                512 Shots Active
              </span>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
