import * as React from "react"

import { cn } from "@/lib/utils"

const Progress = React.forwardRef(({ className, value, ...props }, ref) => {
  return (
    <div
      ref={ref}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      className={cn(
        "relative h-4 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800",
        className
      )}
      {...props}
    >
      <div
        className="h-full w-full flex-1 bg-slate-900 transition-all dark:bg-slate-400"
        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
      />
    </div>
  )
})
Progress.displayName = "Progress"

export { Progress } 