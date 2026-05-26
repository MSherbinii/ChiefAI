import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

type Variant = 'solid' | 'outline' | 'ghost' | 'danger';
type Size = 'xs' | 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
  loading?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  solid: [
    'bg-[linear-gradient(135deg,#2633D9_0%,#8A3AFF_100%)]',
    'text-white font-semibold',
    'border border-[rgba(138,58,255,0.32)]',
    'shadow-[inset_0_1px_0_rgba(255,255,255,0.09),0_0_24px_rgba(89,74,255,0.24),0_4px_12px_rgba(0,0,0,0.30)]',
    'hover:brightness-110 active:brightness-95',
  ].join(' '),
  outline: [
    'bg-[rgba(247,240,255,0.04)] text-[var(--v2-text-dim)]',
    'border border-[rgba(247,240,255,0.12)]',
    'hover:bg-[rgba(247,240,255,0.07)] hover:border-[rgba(247,240,255,0.18)] hover:text-[var(--v2-text)]',
  ].join(' '),
  ghost: [
    'bg-transparent border-transparent text-[var(--v2-muted)]',
    'hover:bg-[rgba(247,240,255,0.05)] hover:text-[var(--v2-text-dim)]',
  ].join(' '),
  danger: [
    'bg-[rgba(255,79,109,0.10)] text-[var(--v2-danger)]',
    'border border-[rgba(255,79,109,0.24)]',
    'hover:bg-[rgba(255,79,109,0.16)] hover:border-[rgba(255,79,109,0.38)]',
  ].join(' '),
};

const SIZES: Record<Size, string> = {
  xs: 'h-6  px-2    text-[11px] gap-1   rounded-[8px]',
  sm: 'h-7  px-2.5  text-[12px] gap-1.5 rounded-[8px]',
  md: 'h-8  px-3.5  text-[13px] gap-2   rounded-[10px]',
  lg: 'h-10 px-5    text-[14px] gap-2   rounded-[12px]',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'outline', size = 'md', iconLeft, iconRight, loading, disabled, children, ...rest }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center font-semibold tracking-[0.01em]',
        'select-none whitespace-nowrap transition-all duration-100',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--v2-border-focus)]',
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...rest}
    >
      {loading ? (
        <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <circle cx="12" cy="12" r="10" strokeOpacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round"/>
        </svg>
      ) : iconLeft}
      {children}
      {!loading && iconRight}
    </button>
  )
);
Button.displayName = 'Button';
