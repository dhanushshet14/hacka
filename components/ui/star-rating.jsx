import React, { useState } from "react";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

const StarRating = React.forwardRef(({ 
  total = 5, 
  value = 0, 
  onChange,
  readOnly = false,
  className,
  starClassName,
  ...props 
}, ref) => {
  const [hoverValue, setHoverValue] = useState(0);

  const handleMouseEnter = (index) => {
    if (readOnly) return;
    setHoverValue(index);
  };

  const handleMouseLeave = () => {
    if (readOnly) return;
    setHoverValue(0);
  };

  const handleClick = (index) => {
    if (readOnly) return;
    onChange?.(index);
  };

  const renderStars = () => {
    return Array.from({ length: total }, (_, i) => {
      const starValue = i + 1;
      const isFilled = hoverValue ? starValue <= hoverValue : starValue <= value;
      
      return (
        <Star
          key={i}
          className={cn(
            "cursor-pointer transition-all",
            isFilled ? "fill-amber-500 text-amber-500" : "fill-none text-slate-300",
            readOnly && "cursor-default",
            starClassName
          )}
          size={24}
          onMouseEnter={() => handleMouseEnter(starValue)}
          onClick={() => handleClick(starValue)}
        />
      );
    });
  };

  return (
    <div 
      ref={ref}
      className={cn("flex gap-1", className)}
      onMouseLeave={handleMouseLeave}
      {...props}
    >
      {renderStars()}
    </div>
  );
});

StarRating.displayName = "StarRating";

export { StarRating }; 