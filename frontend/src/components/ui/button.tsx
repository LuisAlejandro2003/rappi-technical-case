"use client";

import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg' | 'icon';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
          {
            'bg-[#FF441F] text-white hover:bg-[#E03A18] shadow-sm': variant === 'primary',
            'bg-gray-100 text-gray-700 hover:bg-gray-200': variant === 'secondary',
            'hover:bg-gray-100 text-gray-600': variant === 'ghost',
            'border border-gray-200 bg-white text-gray-700 hover:bg-gray-50': variant === 'outline',
          },
          {
            'h-8 px-3 text-sm rounded-lg': size === 'sm',
            'h-10 px-4 text-sm rounded-lg': size === 'md',
            'h-12 px-6 text-base rounded-lg': size === 'lg',
            'h-8 w-8 rounded-lg': size === 'icon',
          },
          className
        )}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';
