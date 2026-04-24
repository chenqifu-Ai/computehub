/**
 * 热力图组件 - 专家意见分布可视化
 * 展示专家对各个方案的偏好程度分布
 */

import { useEffect, useRef } from 'react';

const Heatmap = ({
  data,
  experts = [],
  schemes = [],
  width = 600,
  height = 400,
  colorScale = 'viridis',
  showLegend = true,
  onCellClick,
  className = ''
}) => {
  const chartRef = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // 清除旧图表
    while (chartRef.current.firstChild) {
      chartRef.current.removeChild(chartRef.current.firstChild);
    }

    // 创建SVG元素
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', width);
    svg.setAttribute('height', height);
    svg.setAttribute('class', 'decision-heatmap');

    // 计算布局参数
    const margin = { top: 40, right: 120, bottom: 60, left: 100 };
    const cellWidth = (width - margin.left - margin.right) / schemes.length;
    const cellHeight = (height - margin.top - margin.bottom) / experts.length;

    // 绘制热力图
    drawHeatmap(svg, data, experts, schemes, margin, cellWidth, cellHeight, colorScale, onCellClick);

    // 添加图例
    if (showLegend) {
      drawLegend(svg, width, height, margin, colorScale);
    }

    chartRef.current.appendChild(svg);
  }, [data, experts, schemes, width, height, colorScale, showLegend, onCellClick]);

  // 绘制热力图
  const drawHeatmap = (svg, data, experts, schemes, margin, cellWidth, cellHeight, colorScale, onCellClick) => {
    // 绘制专家标签
    experts.forEach((expert, rowIndex) => {
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', margin.left - 10);
      text.setAttribute('y', margin.top + (rowIndex + 0.5) * cellHeight);
      text.setAttribute('text-anchor', 'end');
      text.setAttribute('alignment-baseline', 'middle');
      text.setAttribute('font-size', '12');
      text.setAttribute('fill', '#333');
      text.textContent = expert;
      svg.appendChild(text);
    });

    // 绘制方案标签
    schemes.forEach((scheme, colIndex) => {
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', margin.left + (colIndex + 0.5) * cellWidth);
      text.setAttribute('y', margin.top - 10);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('alignment-baseline', 'baseline');
      text.setAttribute('font-size', '12');
      text.setAttribute('fill', '#333');
      text.textContent = scheme;
      svg.appendChild(text);
    });

    // 绘制热力单元格
    experts.forEach((expert, rowIndex) => {
      schemes.forEach((scheme, colIndex) => {
        const value = data[expert]?.[scheme] || 0;
        const color = getColor(value, colorScale);

        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', margin.left + colIndex * cellWidth);
        rect.setAttribute('y', margin.top + rowIndex * cellHeight);
        rect.setAttribute('width', cellWidth);
        rect.setAttribute('height', cellHeight);
        rect.setAttribute('fill', color);
        rect.setAttribute('stroke', '#fff');
        rect.setAttribute('stroke-width', '1');
        rect.setAttribute('data-expert', expert);
        rect.setAttribute('data-scheme', scheme);
        rect.setAttribute('data-value', value);

        // 添加交互功能
        if (onCellClick) {
          rect.addEventListener('click', () => {
            onCellClick({
              expert,
              scheme,
              value
            });
          });

          // 悬停效果
          rect.addEventListener('mouseenter', () => {
            rect.setAttribute('stroke', '#333');
            rect.setAttribute('stroke-width', '2');
            
            // 显示工具提示
            const tooltip = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            tooltip.setAttribute('x', margin.left + (colIndex + 0.5) * cellWidth);
            tooltip.setAttribute('y', margin.top + (rowIndex + 0.5) * cellHeight - 5);
            tooltip.setAttribute('text-anchor', 'middle');
            tooltip.setAttribute('alignment-baseline', 'middle');
            tooltip.setAttribute('font-size', '10');
            tooltip.setAttribute('fill', '#fff');
            tooltip.setAttribute('class', 'heatmap-tooltip');
            tooltip.textContent = value;
            svg.appendChild(tooltip);
          });

          rect.addEventListener('mouseleave', () => {
            rect.setAttribute('stroke', '#fff');
            rect.setAttribute('stroke-width', '1');
            const tooltip = svg.querySelector('.heatmap-tooltip');
            if (tooltip) {
              svg.removeChild(tooltip);
            }
          });
        }

        svg.appendChild(rect);

        // 添加数值标签
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', margin.left + (colIndex + 0.5) * cellWidth);
        text.setAttribute('y', margin.top + (rowIndex + 0.5) * cellHeight);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('alignment-baseline', 'middle');
        text.setAttribute('font-size', '10');
        text.setAttribute('fill', value > 50 ? '#fff' : '#333');
        text.textContent = value;
        svg.appendChild(text);
      });
    });
  };

  // 绘制图例
  const drawLegend = (svg, width, height, margin, colorScale) => {
    const legendWidth = 200;
    const legendHeight = 20;
    const legendX = width - margin.right + 20;
    const legendY = margin.top;

    // 图例标题
    const title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    title.setAttribute('x', legendX);
    title.setAttribute('y', legendY - 10);
    title.setAttribute('font-size', '12');
    title.setAttribute('fill', '#333');
    title.textContent = '偏好程度';
    svg.appendChild(title);

    // 图例渐变条
    for (let i = 0; i < legendWidth; i++) {
      const value = (i / legendWidth) * 100;
      const color = getColor(value, colorScale);
      
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', legendX + i);
      rect.setAttribute('y', legendY);
      rect.setAttribute('width', 1);
      rect.setAttribute('height', legendHeight);
      rect.setAttribute('fill', color);
      svg.appendChild(rect);
    }

    // 图例刻度
    const ticks = [0, 25, 50, 75, 100];
    ticks.forEach(tick => {
      const x = legendX + (tick / 100) * legendWidth;
      
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', x);
      line.setAttribute('y1', legendY + legendHeight);
      line.setAttribute('x2', x);
      line.setAttribute('y2', legendY + legendHeight + 5);
      line.setAttribute('stroke', '#666');
      line.setAttribute('stroke-width', '1');
      svg.appendChild(line);

      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', x);
      text.setAttribute('y', legendY + legendHeight + 15);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('font-size', '10');
      text.setAttribute('fill', '#666');
      text.textContent = tick;
      svg.appendChild(text);
    });
  };

  // 获取颜色
  const getColor = (value, scale) => {
    const normalized = value / 100;
    
    switch (scale) {
      case 'viridis':
        // Viridis配色方案
        const colors = [
          '#440154', '#482878', '#3e4989', '#31688e',
          '#26828e', '#1f9e89', '#35b779', '#6ece58',
          '#b5de2b', '#fde725'
        ];
        return colors[Math.floor(normalized * (colors.length - 1))];
      
      case 'red-blue':
        // 红蓝配色方案
        if (normalized < 0.5) {
          const intensity = normalized * 2;
          return `rgb(${255 * intensity}, ${255 * intensity}, 255)`;
        } else {
          const intensity = (normalized - 0.5) * 2;
          return `rgb(255, ${255 * (1 - intensity)}, ${255 * (1 - intensity)})`;
        }
      
      default:
        // 默认灰度方案
        const gray = 255 - (normalized * 255);
        return `rgb(${gray}, ${gray}, ${gray})`;
    }
  };

  return (
    <div 
      ref={chartRef} 
      className={`decision-viz-heatmap ${className}`}
      style={{ width: `${width}px`, height: `${height}px` }}
    />
  );
};

export default Heatmap;