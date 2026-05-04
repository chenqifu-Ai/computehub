/**
 * 类型定义文件
 * 为库提供完整的TypeScript类型支持
 */

/**
 * 决策数据接口
 * @typedef {Object} DecisionData
 * @property {string[]} dimensions - 评估维度列表
 * @property {Scheme[]} schemes - 决策方案列表
 * @property {Expert[]} experts - 专家列表
 */

/**
 * 决策方案接口
 * @typedef {Object} Scheme
 * @property {string} name - 方案名称
 * @property {Object} scores - 在各维度的得分 (0-100)
 * @property {string} [description] - 方案描述
 * @property {string} [color] - 方案颜色
 */

/**
 * 专家接口
 * @typedef {Object} Expert
 * @property {string} name - 专家名称
 * @property {Object} preferences - 对各方案的偏好程度 (0-100)
 * @property {string} [role] - 专家角色
 * @property {number} [weight] - 专家权重
 */

/**
 * 加权得分接口
 * @typedef {Object} WeightedScores
 * @property {number} [schemeName] - 方案名称: 加权得分
 */

/**
 * 决策面板配置接口
 * @typedef {Object} DecisionPanelConfig
 * @property {DecisionData} decisionData - 决策数据
 * @property {Object} [initialWeights] - 初始权重配置
 * @property {Function} [onWeightsChange] - 权重变化回调
 * @property {Function} [onDecisionSelect] - 决策选择回调
 * @property {'light'|'dark'} [theme] - 主题模式
 * @property {'auto'|'compact'|'full'} [layout] - 布局模式
 * @property {string} [className] - 自定义类名
 */

/**
 * 雷达图配置接口
 * @typedef {Object} RadarChartConfig
 * @property {Array} data - 图表数据
 * @property {string[]} [dimensions] - 维度列表
 * @property {number} [width] - 图表宽度
 * @property {number} [height] - 图表高度
 * @property {string[]} [colors] - 颜色数组
 * @property {boolean} [interactive] - 是否交互
 * @property {Function} [onPointClick] - 点击回调
 * @property {string} [className] - 自定义类名
 */

/**
 * 热力图配置接口
 * @typedef {Object} HeatmapConfig
 * @property {Object} data - 热力图数据
 * @property {string[]} [experts] - 专家列表
 * @property {string[]} [schemes] - 方案列表
 * @property {number} [width] - 图表宽度
 * @property {number} [height] - 图表高度
 * @property {string} [colorScale] - 配色方案
 * @property {boolean} [showLegend] - 显示图例
 * @property {Function} [onCellClick] - 单元格点击回调
 * @property {string} [className] - 自定义类名
 */

// 导出类型定义
export {
  /** @type {DecisionData} */
  DecisionData,
  
  /** @type {Scheme} */
  Scheme,
  
  /** @type {Expert} */
  Expert,
  
  /** @type {WeightedScores} */
  WeightedScores,
  
  /** @type {DecisionPanelConfig} */
  DecisionPanelConfig,
  
  /** @type {RadarChartConfig} */
  RadarChartConfig,
  
  /** @type {HeatmapConfig} */
  HeatmapConfig
};