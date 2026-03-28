"use client";

import { cn } from '@/lib/cn';

interface AvatarProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  children: React.ReactNode;
}

export function Avatar({ size = 'md', className, children }: AvatarProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-full bg-[#FF441F] text-white flex-shrink-0',
        {
          'w-6 h-6': size === 'sm',
          'w-8 h-8': size === 'md',
          'w-14 h-14 rounded-2xl': size === 'lg',
        },
        className
      )}
    >
      {children}
    </div>
  );
}
