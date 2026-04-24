/**
 * 主决策面板组件 - 集成所有可视化组件的完整决策界面
 * 提供完整的决策分析和可视化功能
 */

import { useState, useEffect } from 'react';
import RadarChart from './RadarChart';
import Heatmap from './Heatmap';

const DecisionPanel = ({
  decisionData,
  initialWeights = {},
  onWeightsChange,
  onDecisionSelect,
  theme = 'light',
  layout = 'auto',
  className = ''
}) => {
  const [weights, setWeights] = useState(initialWeights);
  const [selectedDecision, setSelectedDecision] = useState(null);
  const [viewMode, setViewMode] = useState('overview'); // overview, detail, comparison

  // 初始化权重
  useEffect(() => {
    if (Object.keys(initialWeights).length === 0 && decisionData?.dimensions) {
      const defaultWeights = {};
      decisionData.dimensions.forEach(dim => {
        defaultWeights[dim] = 1 / decisionData.dimensions.length;
      });
      setWeights(defaultWeights);
    }
  }, [decisionData, initialWeights]);

  // 处理权重变化
  const handleWeightChange = (dimension, newWeight) => {
    const newWeights = { ...weights, [dimension]: newWeight };
    setWeights(newWeights);
    
    if (onWeightsChange) {
      onWeightsChange(newWeights);
    }
  };

  // 处理决策选择
  const handleDecisionSelect = (decision) => {
    setSelectedDecision(decision);
    if (onDecisionSelect) {
      onDecisionSelect(decision);
    }
  };

  // 计算加权得分
  const calculateWeightedScores = () => {
    if (!decisionData?.schemes) return {};

    const scores = {};
    decisionData.schemes.forEach(scheme => {
      let totalScore = 0;
      let totalWeight = 0;

      decisionData.dimensions.forEach(dimension => {
        const score = scheme.scores?.[dimension] || 0;
        const weight = weights[dimension] || 0;
        totalScore += score * weight;
        totalWeight += weight;
      });

      scores[scheme.name] = totalWeight > 0 ? totalScore / totalWeight : 0;
    });

    return scores;
  };

  // 准备雷达图数据
  const getRadarData = () => {
    if (!decisionData?.schemes) return [];

    return decisionData.schemes.map(scheme => ({
      name: scheme.name,
      ...scheme.scores
    }));
  };

  // 准备热力图数据
  const getHeatmapData = () => {
    if (!decisionData?.experts) return {};

    const data = {};
    decisionData.experts.forEach(expert => {
      data[expert.name] = {};
      decisionData.schemes.forEach(scheme => {
        data[expert.name][scheme.name] = expert.preferences?.[scheme.name] || 0;
      });
    });

    return data;
  };

  // 获取专家列表
  const getExperts = () => {
    return decisionData?.experts?.map(e => e.name) || [];
  };

  // 获取方案列表
  const getSchemes = () => {
    return decisionData?.schemes?.map(s => s.name) || [];
  };

  if (!decisionData) {
    return (
      <div className={`decision-panel loading ${className}`}>
        <div className="loading-message">加载决策数据中...</div>
      </div>
    );
  }

  const weightedScores = calculateWeightedScores();
  const radarData = getRadarData();
  const heatmapData = getHeatmapData();
  const experts = getExperts();
  const schemes = getSchemes();

  return (
    <div className={`decision-panel theme-${theme} layout-${layout} ${className}`}>
      <div className="panel-header">
        <h2>🎯 集体决策优化面板</h2>
        <div className="view-controls">
          <button 
            className={viewMode === 'overview' ? 'active' : ''}
            onClick={() => setViewMode('overview')}
          >
            概览
          </button>
          <button 
            className={viewMode === 'detail' ? 'active' : ''}
            onClick={() => setViewMode('detail')}
          >
            详情
          </button>
          <button 
            className={viewMode === 'comparison' ? 'active' : ''}
            onClick={() => setViewMode('comparison')}
          >
            对比
          </button>
        </div>
      </div>

      <div className="panel-content">
        <div className="control-section">
          <h3>评估维度权重</h3>
          <div className="weight-controls">
            {decisionData.dimensions?.map(dimension => (
              <div key={dimension} className="weight-control">
                <label>{dimension}</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={weights[dimension] || 0}
                  onChange={(e) => handleWeightChange(dimension, parseFloat(e.target.value))}
                />
                <span>{(weights[dimension] * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="visualization-section">
          <div className="chart-row">
            <div className="chart-container">
              <h3>多维度方案对比</h3>
              <RadarChart
                data={radarData}
                dimensions={decisionData.dimensions}
                width={400}
                height={400}
                onPointClick={handleDecisionSelect}
              />
            </div>

            <div className="chart-container">
              <h3>专家意见分布</h3>
              <Heatmap
                data={heatmapData}
                experts={experts}
                schemes={schemes}
                width={500}
                height={400}
                onCellClick={handleDecisionSelect}
              />
            </div>
          </div>

          <div className="results-section">
            <h3>决策结果</h3>
            <div className="results-grid">
              {Object.entries(weightedScores)
                .sort(([, a], [, b]) => b - a)
                .map(([scheme, score]) => (
                  <div 
                    key={scheme} 
                    className={`result-card ${selectedDecision?.scheme === scheme ? 'selected' : ''}`}
                    onClick={() => handleDecisionSelect({ scheme, score })}
                  >
                    <div className="scheme-name">{scheme}</div>
                    <div className="score">{score.toFixed(1)}</div>
                    <div className="score-bar">
                      <div 
                        className="score-fill" 
                        style={{ width: `${score}%` }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>

      {selectedDecision && (
        <div className="decision-detail">
          <h3>选中决策详情: {selectedDecision.scheme}</h3>
          <div className="detail-content">
            <p>综合得分: <strong>{selectedDecision.score?.toFixed(1)}</strong></p>
            <div className="dimension-scores">
              {decisionData.dimensions?.map(dimension => (
                <div key={dimension} className="dimension-score">
                  <span>{dimension}:</span>
                  <span>{
                    decisionData.schemes
                      ?.find(s => s.name === selectedDecision.scheme)
                      ?.scores?.[dimension] || 0
                  }</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DecisionPanel;