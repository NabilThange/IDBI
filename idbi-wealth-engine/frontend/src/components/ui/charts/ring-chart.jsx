import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { arc as arcGenerator } from "@visx/shape";
import {
  Children,
  isValidElement,
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { cn } from "../../../lib/utils";
import {
  defaultRingColors,
  RingProvider,
  ringCssVars,
} from "./ring-context";

function generateRingArcPath(
  innerRadius,
  outerRadius,
  startAngle,
  endAngle,
  cornerRadius
) {
  const generator = arcGenerator({
    innerRadius,
    outerRadius,
    cornerRadius,
  });
  return generator({ startAngle, endAngle }) || "";
}

function isRing(child) {
  return (
    isValidElement(child) &&
    typeof child.type === "function" &&
    (child.type.displayName === "Ring" || child.type.name === "Ring")
  );
}

function isRingCenter(child) {
  return (
    isValidElement(child) &&
    typeof child.type === "function" &&
    (child.type.displayName === "RingCenter" || child.type.name === "RingCenter")
  );
}

const RingChartCore = memo(function RingChartCore({
  width,
  height,
  data,
  strokeWidth: strokeWidthProp,
  ringGap: ringGapProp,
  baseInnerRadius: baseInnerRadiusProp,
  children,
  containerRef,
  hoveredIndexProp,
  onHoverChange,
  startAngle,
  endAngle,
  enterTransition,
  enterStaggerScale,
  geometryScrubbing,
}) {
  const [internalHoveredIndex, setInternalHoveredIndex] = useState(null);
  const [animationKey] = useState(0);
  const [isLoaded, setIsLoaded] = useState(false);

  const isControlled = hoveredIndexProp !== undefined;
  const hoveredIndex = isControlled ? hoveredIndexProp : internalHoveredIndex;
  const setHoveredIndex = useCallback(
    (index) => {
      if (isControlled) {
        onHoverChange?.(index);
      } else {
        setInternalHoveredIndex(index);
      }
    },
    [isControlled, onHoverChange]
  );

  const size = Math.min(width, height);
  const center = size / 2;

  const ringCount = data.length;
  const padding = 8;
  const availableRadius = center - padding;

  const designOuterRadius =
    baseInnerRadiusProp +
    (ringCount - 1) * (strokeWidthProp + ringGapProp) +
    strokeWidthProp;

  const scale = Math.min(1, availableRadius / designOuterRadius);

  const strokeWidth = strokeWidthProp * scale;
  const ringGap = ringGapProp * scale;
  const baseInnerRadius = baseInnerRadiusProp * scale;

  const totalValue = useMemo(
    () => data.reduce((sum, d) => sum + d.value, 0),
    [data]
  );

  const getColor = useCallback(
    (index) => {
      const item = data[index];
      if (item?.color) {
        return item.color;
      }
      return defaultRingColors[index % defaultRingColors.length];
    },
    [data]
  );

  const getRingRadii = useCallback(
    (index) => {
      const innerRadius = baseInnerRadius + index * (strokeWidth + ringGap);
      const outerRadius = innerRadius + strokeWidth;
      return { innerRadius, outerRadius };
    },
    [baseInnerRadius, strokeWidth, ringGap]
  );

  const arcRange = endAngle - startAngle;
  const scrubRingLayers = useMemo(() => {
    if (!geometryScrubbing) {
      return null;
    }
    return data.map((ringData, index) => {
      const { innerRadius, outerRadius } = getRingRadii(index);
      const cornerRadius = (outerRadius - innerRadius) / 2;
      const progress = ringData.value / ringData.maxValue;
      const progressEndAngle = startAngle + arcRange * progress;
      return {
        bgPath: generateRingArcPath(
          innerRadius,
          outerRadius,
          startAngle,
          endAngle,
          cornerRadius
        ),
        progressPath:
          progressEndAngle <= startAngle + 0.01
            ? ""
            : generateRingArcPath(
                innerRadius,
                outerRadius,
                startAngle,
                progressEndAngle,
                cornerRadius
              ),
        color: getColor(index),
      };
    });
  }, [
    geometryScrubbing,
    data,
    getRingRadii,
    getColor,
    startAngle,
    endAngle,
    arcRange,
  ]);

  const effectiveIsLoaded = geometryScrubbing || isLoaded;

  useEffect(() => {
    if (geometryScrubbing) {
      return;
    }
    setIsLoaded(false);
    const timer = setTimeout(() => {
      setIsLoaded(true);
    }, 100);
    return () => clearTimeout(timer);
  }, [enterTransition, enterStaggerScale, geometryScrubbing]);

  const { svgChildren, centerChildren } = useMemo(() => {
    const svgNodes = [];
    const centerNodes = [];

    Children.forEach(children, (child) => {
      if (isRingCenter(child)) {
        centerNodes.push(child);
      } else if (geometryScrubbing && isRing(child)) {
        return;
      } else {
        svgNodes.push(child);
      }
    });

    return { svgChildren: svgNodes, centerChildren: centerNodes };
  }, [children, geometryScrubbing]);

  const contextValue = useMemo(
    () => ({
      data,
      size,
      center,
      strokeWidth,
      ringGap,
      baseInnerRadius,
      hoveredIndex,
      setHoveredIndex,
      animationKey,
      isLoaded: effectiveIsLoaded,
      enterTransition,
      enterStaggerScale,
      containerRef,
      totalValue,
      getColor,
      getRingRadii,
      startAngle,
      endAngle,
      geometryScrubbing,
    }),
    [
      data,
      size,
      center,
      strokeWidth,
      ringGap,
      baseInnerRadius,
      hoveredIndex,
      setHoveredIndex,
      animationKey,
      effectiveIsLoaded,
      enterTransition,
      enterStaggerScale,
      containerRef,
      totalValue,
      getColor,
      getRingRadii,
      startAngle,
      endAngle,
      geometryScrubbing,
    ]
  );

  return (
    <RingProvider value={contextValue}>
      <div
        className="grid"
        style={{
          gridTemplateColumns: "1fr",
          gridTemplateRows: "1fr",
          width: size,
          height: size,
        }}
      >
        <svg
          aria-hidden="true"
          height={size}
          style={{ gridArea: "1 / 1", contain: "layout style paint" }}
          width={size}
        >
          <Group left={center} top={center}>
            {scrubRingLayers
              ? scrubRingLayers.map((layer, index) => (
                  <g key={data[index]?.label ?? index}>
                    <path d={layer.bgPath} fill={ringCssVars.ringBackground} />
                    {layer.progressPath ? (
                      <path d={layer.progressPath} fill={layer.color} />
                    ) : null}
                  </g>
                ))
              : null}
            {svgChildren}
          </Group>
        </svg>

        {centerChildren.length > 0 && (
          <div
            className="pointer-events-none flex items-center justify-center"
            style={{ gridArea: "1 / 1" }}
          >
            {centerChildren}
          </div>
        )}
      </div>
    </RingProvider>
  );
}, ringChartCorePropsEqual);

function ringChartCorePropsEqual(prev, next) {
  return (
    prev.width === next.width &&
    prev.height === next.height &&
    prev.data === next.data &&
    prev.strokeWidth === next.strokeWidth &&
    prev.ringGap === next.ringGap &&
    prev.baseInnerRadius === next.baseInnerRadius &&
    prev.hoveredIndexProp === next.hoveredIndexProp &&
    prev.onHoverChange === next.onHoverChange &&
    prev.startAngle === next.startAngle &&
    prev.endAngle === next.endAngle &&
    prev.enterTransition === next.enterTransition &&
    prev.enterStaggerScale === next.enterStaggerScale &&
    prev.geometryScrubbing === next.geometryScrubbing &&
    prev.children === next.children
  );
}

function RingChartInner(props) {
  const size = Math.min(props.width, props.height);
  if (size < 10) {
    return null;
  }
  return <RingChartCore {...props} />;
}

export function RingChart({
  data,
  size: fixedSize,
  strokeWidth = 12,
  ringGap = 6,
  baseInnerRadius = 60,
  className = "",
  hoveredIndex,
  onHoverChange,
  startAngle = -Math.PI / 2,
  endAngle = (3 * Math.PI) / 2,
  enterTransition,
  enterStaggerScale = 1,
  geometryScrubbing = false,
  children,
}) {
  const containerRef = useRef(null);

  if (fixedSize) {
    return (
      <div
        className={cn("relative flex items-center justify-center", className)}
        ref={containerRef}
        style={{ width: fixedSize, height: fixedSize }}
      >
        <RingChartInner
          baseInnerRadius={baseInnerRadius}
          containerRef={containerRef}
          data={data}
          endAngle={endAngle}
          enterStaggerScale={enterStaggerScale}
          enterTransition={enterTransition}
          geometryScrubbing={geometryScrubbing}
          height={fixedSize}
          hoveredIndexProp={hoveredIndex}
          onHoverChange={onHoverChange}
          ringGap={ringGap}
          startAngle={startAngle}
          strokeWidth={strokeWidth}
          width={fixedSize}
        >
          {children}
        </RingChartInner>
      </div>
    );
  }

  return (
    <div
      className={cn("relative aspect-square w-full", className)}
      ref={containerRef}
    >
      <ParentSize debounceTime={10}>
        {({ width, height }) => (
          <RingChartInner
            baseInnerRadius={baseInnerRadius}
            containerRef={containerRef}
            data={data}
            endAngle={endAngle}
            enterStaggerScale={enterStaggerScale}
            enterTransition={enterTransition}
            geometryScrubbing={geometryScrubbing}
            height={height}
            hoveredIndexProp={hoveredIndex}
            onHoverChange={onHoverChange}
            ringGap={ringGap}
            startAngle={startAngle}
            strokeWidth={strokeWidth}
            width={width}
          >
            {children}
          </RingChartInner>
        )}
      </ParentSize>
    </div>
  );
}

export default RingChart;
