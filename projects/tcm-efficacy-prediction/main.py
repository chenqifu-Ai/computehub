#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中医药疗效预测机器学习项目 - 主入口文件

功能：
1. 数据预处理和特征工程
2. 机器学习模型训练
3. 模型评估和优化
4. 结果可视化和报告生成
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent / "src"))

from data_processing.data_loader import DataLoader
from feature_engineering.feature_extractor import FeatureExtractor
from model_training.xgboost_trainer import XGBoostTrainer
from evaluation.model_evaluator import ModelEvaluator
from utils.logger import setup_logger
from utils.config_loader import load_config

def main():
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="中医药疗效预测机器学习项目")
    parser.add_argument("--config", default="config/main_config.yaml", help="配置文件路径")
    parser.add_argument("--mode", choices=["train", "predict", "evaluate"], default="train", help="运行模式")
    parser.add_argument("--data_path", help="数据文件路径")
    parser.add_argument("--model_path", help="模型文件路径")
    parser.add_argument("--output_dir", default="results", help="输出目录")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 设置日志
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(log_level)
    logger = logging.getLogger(__name__)
    
    # 加载配置
    config = load_config(args.config)
    logger.info(f"加载配置文件: {args.config}")
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    if args.mode == "train":
        # 训练模式
        logger.info("开始训练模式...")
        
        # 1. 数据加载
        logger.info("步骤1: 数据加载")
        data_loader = DataLoader(config['data'])
        raw_data = data_loader.load_and_merge_data()
        
        # 2. 特征工程
        logger.info("步骤2: 特征工程")
        feature_extractor = FeatureExtractor(config['features'])
        features = feature_extractor.extract_all_features(raw_data)
        labels = raw_data[config['data']['target_column']]
        
        # 3. 模型训练
        logger.info("步骤3: 模型训练")
        trainer = XGBoostTrainer(config['model'])
        
        # 优化超参数
        if config['model']['optimize_hyperparameters']:
            best_params = trainer.optimize_hyperparameters(features, labels)
            trainer.config.update(best_params)
        
        # 训练最终模型
        model = trainer.train_model(features, labels)
        
        # 4. 模型评估
        logger.info("步骤4: 模型评估")
        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_model(model, features, labels)
        
        # 5. 保存结果
        logger.info("步骤5: 保存结果")
        trainer.save_model(model, output_dir / "trained_model.xgb")
        evaluator.save_evaluation_report(metrics, output_dir / "evaluation_report.md")
        
        logger.info("训练完成！")
        
    elif args.mode == "predict":
        # 预测模式
        logger.info("开始预测模式...")
        
        if not args.model_path:
            logger.error("预测模式需要指定模型路径")
            return
        
        # 加载模型
        trainer = XGBoostTrainer()
        model = trainer.load_model(args.model_path)
        
        # 加载预测数据
        if args.data_path:
            data_loader = DataLoader(config['data'])
            predict_data = data_loader.load_data(args.data_path)
            
            # 特征工程
            feature_extractor = FeatureExtractor(config['features'])
            features = feature_extractor.extract_all_features(predict_data)
            
            # 进行预测
            predictions = trainer.predict(model, features)
            
            # 保存预测结果
            predict_data['prediction'] = predictions
            predict_data.to_csv(output_dir / "predictions.csv", index=False)
            
            logger.info(f"预测完成，结果保存至: {output_dir / 'predictions.csv'}")
        
    elif args.mode == "evaluate":
        # 评估模式
        logger.info("开始评估模式...")
        
        if not args.model_path or not args.data_path:
            logger.error("评估模式需要指定模型路径和数据路径")
            return
        
        # 加载模型和数据
        trainer = XGBoostTrainer()
        model = trainer.load_model(args.model_path)
        
        data_loader = DataLoader(config['data'])
        eval_data = data_loader.load_data(args.data_path)
        
        # 特征工程
        feature_extractor = FeatureExtractor(config['features'])
        features = feature_extractor.extract_all_features(eval_data)
        labels = eval_data[config['data']['target_column']]
        
        # 评估模型
        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_model(model, features, labels)
        
        # 保存评估报告
        evaluator.save_evaluation_report(metrics, output_dir / "evaluation_report.md")
        
        logger.info("评估完成！")

if __name__ == "__main__":
    main()