import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

type Variant = 'default' | 'elevated' | 'inset' | 'ghost';

interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
  interactive?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  default: [
    'border border-[rgba(247,240,255,0.10)]',
    '[background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))]',
  ].join(' '),
  elevated: [
    'border border-[rgba(247,240,255,0.14)]',
    '[background:linear-gradient(180deg,rgba(23,30,43,0.98),rgba(14,19,28,0.98))]',
  ].join(' '),
  inset: [
    'border border-[rgba(247,240,255,0.07)]',
    'bg-[rgba(8,11,17,0.95)]',
  ].join(' '),
  ghost: 'bg-transparent border border-transparent',
};

export const Panel = forwardRef<HTMLDivElement, PanelProps>(
  ({ className, variant = 'default', interactive, children, ...rest }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-[16px] relative overflow-hidden chief-specular',
        VARIANTS[variant],
        variant !== 'ghost' && 'shadow-[inset_0_1px_0_rgba(255,255,255,0.035),0_18px_55px_rgba(0,0,0,0.38)]',
        interactive && [
          'cursor-pointer select-none transition-all duration-150',
          'hover:border-[rgba(247,240,255,0.16)]',
          'hover:[background:linear-gradient(180deg,rgba(22,29,41,0.98),rgba(13,18,26,0.98))]',
          'hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_0_0_1px_rgba(138,58,255,0.14),0_20px_50px_rgba(0,0,0,0.42)]',
          'active:scale-[0.998] active:duration-75',
        ].join(' '),
        className
      )}
      {...rest}
    >
      {children}
    </div>
  )
);
Panel.displayName = 'Panel';
