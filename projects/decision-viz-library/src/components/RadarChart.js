/**
 * 雷达图组件 - 多维度方案对比可视化
 * 支持决策方案在多维度上的对比分析
 */

import { useEffect, useRef } from 'react';

const RadarChart = ({
  data,
  dimensions = ['性能', '成本', '可维护性', '扩展性', '安全性'],
  width = 400,
  height = 400,
  colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57'],
  interactive = true,
  onPointClick,
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
    svg.setAttribute('class', 'decision-radar-chart');

    // 计算中心点和半径
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.4;

    // 绘制雷达网格
    drawRadarGrid(svg, centerX, centerY, radius, dimensions.length);

    // 绘制数据线
    data.forEach((item, index) => {
      drawDataLine(svg, centerX, centerY, radius, dimensions, item, colors[index % colors.length]);
    });

    // 添加交互功能
    if (interactive) {
      addInteractivity(svg, dimensions, onPointClick);
    }

    chartRef.current.appendChild(svg);
  }, [data, dimensions, width, height, colors, interactive, onPointClick]);

  // 绘制雷达网格
  const drawRadarGrid = (svg, centerX, centerY, radius, numDimensions) => {
    const angleStep = (2 * Math.PI) / numDimensions;

    // 绘制同心圆
    for (let i = 1; i <= 5; i++) {
      const circleRadius = (radius * i) / 5;
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', centerX);
      circle.setAttribute('cy', centerY);
      circle.setAttribute('r', circleRadius);
      circle.setAttribute('fill', 'none');
      circle.setAttribute('stroke', '#e0e0e0');
      circle.setAttribute('stroke-width', '1');
      svg.appendChild(circle);
    }

    // 绘制维度线
    for (let i = 0; i < numDimensions; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);

      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', centerX);
      line.setAttribute('y1', centerY);
      line.setAttribute('x2', x);
      line.setAttribute('y2', y);
      line.setAttribute('stroke', '#e0e0e0');
      line.setAttribute('stroke-width', '1');
      svg.appendChild(line);

      // 添加维度标签
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', centerX + (radius + 20) * Math.cos(angle));
      label.setAttribute('y', centerY + (radius + 20) * Math.sin(angle));
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('alignment-baseline', 'middle');
      label.setAttribute('font-size', '12');
      label.setAttribute('fill', '#666');
      label.textContent = dimensions[i];
      svg.appendChild(label);
    }
  };

  // 绘制数据线
  const drawDataLine = (svg, centerX, centerY, radius, dimensions, dataItem, color) => {
    const angleStep = (2 * Math.PI) / dimensions.length;
    const points = [];

    dimensions.forEach((dimension, index) => {
      const value = dataItem[dimension] || 0;
      const angle = index * angleStep - Math.PI / 2;
      const scaledRadius = (radius * value) / 100;
      const x = centerX + scaledRadius * Math.cos(angle);
      const y = centerY + scaledRadius * Math.sin(angle);
      points.push(`${x},${y}`);

      // 绘制数据点
      const point = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      point.setAttribute('cx', x);
      point.setAttribute('cy', y);
      point.setAttribute('r', '4');
      point.setAttribute('fill', color);
      point.setAttribute('stroke', '#fff');
      point.setAttribute('stroke-width', '2');
      point.setAttribute('data-dimension', dimension);
      point.setAttribute('data-value', value);
      point.setAttribute('data-scheme', dataItem.name);
      svg.appendChild(point);
    });

    // 绘制数据线
    const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygon.setAttribute('points', points.join(' '));
    polygon.setAttribute('fill', color + '40'); // 半透明填充
    polygon.setAttribute('stroke', color);
    polygon.setAttribute('stroke-width', '2');
    polygon.setAttribute('fill-opacity', '0.3');
    svg.appendChild(polygon);
  };

  // 添加交互功能
  const addInteractivity = (svg, dimensions, onPointClick) => {
    const points = svg.querySelectorAll('circle[data-dimension]');
    
    points.forEach(point => {
      // 悬停效果
      point.addEventListener('mouseenter', () => {
        point.setAttribute('r', '6');
        
        // 显示工具提示
        const tooltip = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        tooltip.setAttribute('x', parseFloat(point.getAttribute('cx')) + 10);
        tooltip.setAttribute('y', parseFloat(point.getAttribute('cy')) - 10);
        tooltip.setAttribute('class', 'tooltip');
        tooltip.setAttribute('font-size', '10');
        tooltip.setAttribute('fill', '#333');
        tooltip.textContent = `${point.getAttribute('data-scheme')}: ${point.getAttribute('data-value')}`;
        svg.appendChild(tooltip);
      });

      point.addEventListener('mouseleave', () => {
        point.setAttribute('r', '4');
        const tooltip = svg.querySelector('.tooltip');
        if (tooltip) {
          svg.removeChild(tooltip);
        }
      });

      // 点击事件
      if (onPointClick) {
        point.addEventListener('click', () => {
          onPointClick({
            dimension: point.getAttribute('data-dimension'),
            value: point.getAttribute('data-value'),
            scheme: point.getAttribute('data-scheme')
          });
        });
      }
    });
  };

  return (
    <div 
      ref={chartRef} 
      className={`decision-viz-radar ${className}`}
      style={{ width: `${width}px`, height: `${height}px` }}
    />
  );
};

export default RadarChart;