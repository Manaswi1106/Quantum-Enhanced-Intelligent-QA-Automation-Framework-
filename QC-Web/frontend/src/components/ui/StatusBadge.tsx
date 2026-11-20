import type { HTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

export type BadgeSize = 'sm' | 'md'

export interface StatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  status: string
  size?: BadgeSize
}

interface StatusConfig {
  classes: string
  isPulsing?: boolean
  dotColor?: string
}

function getStatusConfig(status: string): StatusConfig {
  const normalized = (status || '').toLowerCase().trim().replace(/[\s-]+/g, '_')

  switch (normalized) {
    case 'passed':
    case 'active':
    case 'ready':
      return {
        classes: 'bg-emerald-50 text-emerald-800 border-emerald-300/80 shadow-2xs font-semibold',
        dotColor: 'bg-emerald-600',
      }

    case 'failed':
    case 'error':
    case 'changes_required':
      return {
        classes: 'bg-[#7D2E37]/12 text-[#7D2E37] border-[#7D2E37]/35 shadow-2xs font-bold',
        dotColor: 'bg-[#7D2E37]',
      }

    case 'running':
    case 'analyzing':
      return {
        classes: 'bg-[#9E3B46]/15 text-[#7D2E37] border-[#9E3B46]/30 shadow-2xs font-semibold',
        isPulsing: true,
        dotColor: 'bg-[#7D2E37]',
      }

    case 'not_run':
    case 'excluded':
    case 'skipped':
      return {
        classes: 'bg-stone-100/90 text-stone-600 border-stone-200/80',
        dotColor: 'bg-stone-400',
      }

    case 'selected':
      return {
        classes: 'bg-[#7D2E37] text-white border-[#63222B] font-bold shadow-xs',
        dotColor: 'bg-white',
      }

    case 'limited_discovery':
    case 'warning':
      return {
        classes: 'bg-amber-500/15 text-amber-300 border-amber-500/35 font-semibold',
        dotColor: 'bg-amber-400',
      }

    default:
      return {
        classes: 'bg-stone-100 text-stone-600 border-stone-200',
        dotColor: 'bg-stone-400',
      }
  }
}

function formatStatusText(status: string): string {
  return (status || '')
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

export function StatusBadge({
  status,
  size = 'md',
  className,
  ...props
}: StatusBadgeProps) {
  const config = getStatusConfig(status)
  const formattedText = formatStatusText(status)

  const sizeClasses =
    size === 'sm'
      ? 'px-2.5 py-0.5 text-[11px] gap-1.5'
      : 'px-3 py-1 text-xs gap-2'

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center font-medium rounded-full border shrink-0 select-none capitalize transition-colors',
        sizeClasses,
        config.classes,
        className
      )}
      {...props}
    >
      <span className="relative flex h-2 w-2 shrink-0">
        {config.isPulsing && (
          <span className={cn('animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', config.dotColor)} />
        )}
        <span className={cn('relative inline-flex rounded-full h-2 w-2', config.dotColor)} />
      </span>
      <span>{formattedText}</span>
    </span>
  )
}

export default StatusBadge
