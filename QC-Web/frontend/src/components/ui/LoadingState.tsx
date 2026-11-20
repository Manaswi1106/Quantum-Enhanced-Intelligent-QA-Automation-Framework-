import { cn } from '../../lib/utils'

export interface LoadingStateProps {
  message?: string
  className?: string
}

export function LoadingState({
  message = 'Loading...',
  className,
}: LoadingStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-12 min-h-[220px]',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <div className="w-10 h-10 border-3 border-[#E5CECE] border-t-[#7D2E37] rounded-full animate-spin" />
      {message && (
        <p className="text-sm text-[#6E5155] mt-4 font-semibold tracking-wide">
          {message}
        </p>
      )}
      <span className="sr-only">{message}</span>
    </div>
  )
}

export default LoadingState
