import React from 'react'
import { cn } from '../../lib/utils'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'porcelain' | 'velvet'
  glow?: boolean
}

export function Card({
  className,
  variant = 'porcelain',
  glow = false,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        variant === 'velvet' ? 'card-velvet' : 'card-porcelain',
        'rounded-[32px] transition-all duration-300',
        glow && 'ring-2 ring-[#7D2E37]/30 shadow-lg',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}

export function CardHeader({
  className,
  children,
  ...props
}: CardHeaderProps) {
  return (
    <div
      className={cn('p-6 sm:p-7 border-b border-[#F0DDDD]', className)}
      {...props}
    >
      {children}
    </div>
  )
}

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

export function CardTitle({
  className,
  children,
  ...props
}: CardTitleProps) {
  return (
    <h3
      className={cn('text-lg font-bold text-[#2B1518] tracking-tight', className)}
      {...props}
    >
      {children}
    </h3>
  )
}

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export function CardContent({
  className,
  children,
  ...props
}: CardContentProps) {
  return (
    <div
      className={cn('p-6 sm:p-7', className)}
      {...props}
    >
      {children}
    </div>
  )
}

export default Card
