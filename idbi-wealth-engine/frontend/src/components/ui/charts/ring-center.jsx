import { cn } from "../../../lib/utils";
import {
  chartCenterContainerClassName,
  chartCenterLabelClassName,
  chartCenterValueClassName,
} from "./chart-center-typography";
import {
  ChartStatFlow,
  defaultChartStatFlowFormat,
} from "./chart-stat-flow";
import { useRingHover, useRingStable } from "./ring-context";

/**
 * RingCenter displays content in the center of the ring chart.
 */
export function RingCenter({
  defaultLabel = "Total",
  formatOptions = defaultChartStatFlowFormat,
  children,
  className = "",
  valueClassName = chartCenterValueClassName,
  labelClassName = chartCenterLabelClassName,
  prefix,
  suffix,
}) {
  const { data, totalValue, baseInnerRadius } = useRingStable();
  const { hoveredIndex } = useRingHover();

  const hoveredData = hoveredIndex === null ? null : data[hoveredIndex];
  const displayValue = hoveredData ? hoveredData.value : totalValue;
  const displayLabel = hoveredData ? hoveredData.label : defaultLabel;

  // Calculate center area size based on scaled baseInnerRadius
  // Leave some padding so text doesn't touch the inner ring
  const centerSize = baseInnerRadius * 2 - 16;

  // If custom render function is provided
  if (children) {
    return (
      <div
        className={cn(
          chartCenterContainerClassName,
          "flex items-center justify-center",
          className
        )}
        style={{ width: centerSize, height: centerSize }}
      >
        {children({
          value: displayValue,
          label: displayLabel,
          isHovered: hoveredIndex !== null,
          data: hoveredData,
        })}
      </div>
    );
  }

  // Default center content with NumberFlow animations
  return (
    <div
      className={cn(
        chartCenterContainerClassName,
        "flex flex-col items-center justify-center text-center",
        className
      )}
      style={{ width: centerSize, height: centerSize }}
    >
      <ChartStatFlow
        formatOptions={formatOptions}
        label={displayLabel}
        labelClassName={labelClassName}
        prefix={prefix}
        suffix={suffix}
        value={displayValue}
        valueClassName={valueClassName}
      />
    </div>
  );
}

RingCenter.displayName = "RingCenter";

export default RingCenter;
