import { cn } from "../../../../lib/utils";
import { useLegendItem } from "./legend-context";

export function LegendProgress({
  trackClassName = "",
  indicatorClassName = "",
  height = "h-1.5",
}) {
  const { item } = useLegendItem();

  if (!item.maxValue) {
    return null;
  }

  const percentage = (item.value / item.maxValue) * 100;

  return (
    <div
      className={cn(
        "w-full overflow-hidden rounded-full bg-slate-800",
        height,
        trackClassName
      )}
    >
      <div
        className={cn(
          "h-full rounded-full transition-all duration-500",
          indicatorClassName
        )}
        style={{ width: `${percentage}%`, backgroundColor: item.color }}
      />
    </div>
  );
}

LegendProgress.displayName = "LegendProgress";
