/**
 * 计算工具函数
 * 提供决策分析相关的数学计算
 */

/**
 * 计算加权得分
 * @param {Array} schemes 方案列表
 * @param {Object} weights 权重对象
 * @param {Array} dimensions 维度列表
 * @returns {Object} 加权得分对象
 */
export function calculateWeightedScores(schemes, weights, dimensions) {
  const scores = {};
  
  schemes.forEach(scheme => {
    let totalScore = 0;
    let totalWeight = 0;

    dimensions.forEach(dimension => {
      const score = scheme.scores?.[dimension] || 0;
      const weight = weights[dimension] || 0;
      totalScore += score * weight;
      totalWeight += weight;
    });

    scores[scheme.name] = totalWeight > 0 ? totalScore / totalWeight : 0;
  });

  return scores;
}

/**
 * 计算共识度
 * @param {Array} experts 专家列表
 * @param {Array} schemes 方案列表
 * @returns {number} 共识度 (0-1)
 */
export function calculateConsensus(experts, schemes) {
  if (!experts.length || !schemes.length) return 0;

  // 计算每个方案的专家偏好平均值
  const schemePreferences = {};
  schemes.forEach(scheme => {
    schemePreferences[scheme.name] = 0;
    experts.forEach(expert => {
      schemePreferences[scheme.name] += expert.preferences?.[scheme.name] || 0;
    });
    schemePreferences[scheme.name] /= experts.length;
  });

  // 计算方差来衡量共识度
  let totalVariance = 0;
  experts.forEach(expert => {
    schemes.forEach(scheme => {
      const preference = expert.preferences?.[scheme.name] || 0;
      const meanPreference = schemePreferences[scheme.name];
      totalVariance += Math.pow(preference - meanPreference, 2);
    });
  });

  // 归一化到0-1范围 (方差越小共识度越高)
  const maxVariance = schemes.length * experts.length * Math.pow(100, 2);
  const consensus = 1 - (totalVariance / maxVariance);
  
  return Math.max(0, Math.min(1, consensus));
}

/**
 * 计算方案排名
 * @param {Object} weightedScores 加权得分对象
 * @returns {Array} 排名数组
 */
export function calculateRanking(weightedScores) {
  return Object.entries(weightedScores)
    .sort(([, a], [, b]) => b - a)
    .map(([scheme, score], index) => ({
      rank: index + 1,
      scheme,
      score
    }));
}

/**
 * 计算敏感性分析
 * @param {Array} schemes 方案列表
 * @param {Object} baseWeights 基础权重
 * @param {Array} dimensions 维度列表
 * @param {number} variation 变化幅度 (0-1)
 * @returns {Object} 敏感性分析结果
 */
export function sensitivityAnalysis(schemes, baseWeights, dimensions, variation = 0.1) {
  const results = {};
  
  dimensions.forEach(dimension => {
    // 测试该维度权重增加的情况
    const increasedWeights = { ...baseWeights };
    increasedWeights[dimension] = Math.min(1, baseWeights[dimension] + variation);
    
    // 重新分配其他权重
    const otherDimensions = dimensions.filter(d => d !== dimension);
    const totalOtherWeight = otherDimensions.reduce((sum, d) => sum + baseWeights[d], 0);
    const scaleFactor = (1 - increasedWeights[dimension]) / totalOtherWeight;
    
    otherDimensions.forEach(d => {
      increasedWeights[d] = baseWeights[d] * scaleFactor;
    });

    const increasedScores = calculateWeightedScores(schemes, increasedWeights, dimensions);
    
    results[dimension] = {
      increased: increasedScores,
      base: calculateWeightedScores(schemes, baseWeights, dimensions),
      sensitivity: {}
    };

    // 计算每个方案的敏感性
    Object.keys(increasedScores).forEach(scheme => {
      const baseScore = results[dimension].base[scheme];
      const increasedScore = increasedScores[scheme];
      results[dimension].sensitivity[scheme] = increasedScore - baseScore;
    });
  });

  return results;
}

/**
 * 计算决策置信度
 * @param {Object} weightedScores 加权得分
 * @param {number} consensus 共识度
 * @returns {number} 置信度 (0-1)
 */
export function calculateConfidence(weightedScores, consensus) {
  const scores = Object.values(weightedScores);
  if (scores.length < 2) return 0;

  // 计算得分差异 (差异越大置信度越高)
  const maxScore = Math.max(...scores);
  const secondMaxScore = Math.max(...scores.filter(s => s < maxScore));
  const scoreDifference = maxScore - secondMaxScore;
  
  // 归一化差异 (假设最大差异为50分)
  const normalizedDifference = Math.min(1, scoreDifference / 50);
  
  // 结合共识度计算最终置信度
  return (normalizedDifference * 0.6) + (consensus * 0.4);
}