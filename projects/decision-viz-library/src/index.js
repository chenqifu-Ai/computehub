/**
 * 通用决策可视化库 - 主入口文件
 * 导出所有可复用组件和工具
 */

// 核心组件导出
export { default as RadarChart } from './components/RadarChart.js';
export { default as Heatmap } from './components/Heatmap.js';
export { default as DecisionPanel } from './components/DecisionPanel.js';

// 工具函数导出
export { calculateWeightedScores } from './utils/calculations.js';
export { normalizeData } from './utils/normalization.js';

// 主题系统导出
export { defaultTheme, darkTheme } from './themes/index.js';

// 类型定义 (TypeScript支持)
export {
  DecisionData,
  Expert,
  Scheme,
  WeightedScores
} from './types/index.js';

/**
 * 库版本信息
 */
export const version = '0.1.0';

/**
 * 库信息
 */
export const libraryInfo = {
  name: 'Decision Visualization Library',
  version: '0.1.0',
  description: '通用决策可视化组件库',
  author: '小智 AI助手',
  repository: 'https://github.com/your-org/decision-viz-library'
};

/**
 * 初始化库配置
 * @param {Object} config 配置对象
 */
export function init(config = {}) {
  const defaultConfig = {
    theme: 'light',
    locale: 'zh-CN',
    animation: true,
    ...config
  };
  
  // 应用配置到全局
  if (typeof window !== 'undefined') {
    window.__DECISION_VIZ_CONFIG__ = defaultConfig;
  }
  
  return defaultConfig;
}

/**
 * 获取当前配置
 */
export function getConfig() {
  if (typeof window !== 'undefined' && window.__DECISION_VIZ_CONFIG__) {
    return window.__DECISION_VIZ_CONFIG__;
  }
  return init();
}

// 默认初始化
if (typeof window !== 'undefined') {
  init();
}