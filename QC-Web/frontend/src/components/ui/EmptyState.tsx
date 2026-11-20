import { type ReactNode, type ComponentType, isValidElement } from 'react'
import { cn } from '../../lib/utils'

export interface EmptyStateProps {
  icon?: ReactNode | ComponentType<{ className?: string }>
  title: string
  description: string
  action?: ReactNode
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  const renderIcon = () => {
    if (!Icon) return null
    if (isValidElement(Icon)) {
      return Icon
    }
    const IconComp = Icon as any
    return <IconComp className="w-10 h-10 text-[#7D2E37]" />
  }

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-16 px-6 text-center',
        className
      )}
    >
      <div className="w-20 h-20 rounded-3xl bg-[#7D2E37]/10 border border-[#7D2E37]/20 flex items-center justify-center shadow-xs mb-5">
        {renderIcon()}
      </div>
      <h3 className="text-xl font-bold text-[#2B1518] tracking-tight">{title}</h3>
      <p className="text-sm text-[#6E5155] mt-2 max-w-md leading-relaxed">
        {description}
      </p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}

export default EmptyState
