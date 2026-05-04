#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成示例数据脚本
用于创建中医药疗效预测项目的示例数据
"""

import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import json
import random
from pathlib import Path

# 初始化Faker
fake = Faker('zh_CN')

def generate_patient_data(n_samples=1000):
    """生成患者基本信息数据"""
    patients = []
    
    for i in range(n_samples):
        patient = {
            'patient_id': f'PT{10000 + i}',
            'name': fake.name(),
            'age': random.randint(18, 85),
            'gender': random.choice(['男', '女']),
            'height': round(random.uniform(150, 190), 1),
            'weight': round(random.uniform(40, 100), 1),
            'bmi': 0,  # 稍后计算
            'blood_type': random.choice(['A', 'B', 'AB', 'O']),
            'phone': fake.phone_number(),
            'address': fake.address(),
            'admission_date': fake.date_between(start_date='-2y', end_date='-1y'),
            'discharge_date': None,
            'medical_history': random.choice(['高血压', '糖尿病', '心脏病', '无']),
            'allergies': random.choice(['无', '青霉素', '海鲜', '花粉'])
        }
        
        # 计算BMI
        patient['bmi'] = round(patient['weight'] / (patient['height']/100) ** 2, 1)
        
        # 设置出院日期（住院7-30天）
        stay_days = random.randint(7, 30)
        patient['discharge_date'] = patient['admission_date'] + timedelta(days=stay_days)
        
        patients.append(patient)
    
    return pd.DataFrame(patients)

def generate_tcm_diagnosis_data(patient_df):
    """生成中医四诊数据"""
    diagnoses = []
    
    tongue_colors = ['淡红', '红', '绛', '紫', '淡白']
    tongue_coatings = ['薄白', '白腻', '黄腻', '少苔', '剥苔']
    pulse_types = ['弦脉', '滑脉', '细脉', '沉脉', '数脉', '迟脉', '涩脉', '浮脉']
    
    for _, patient in patient_df.iterrows():
        diagnosis = {
            'patient_id': patient['patient_id'],
            'tongue_color': random.choice(tongue_colors),
            'tongue_coating': random.choice(tongue_coatings),
            'pulse_type': random.choice(pulse_types),
            'symptom_score': round(random.uniform(10, 50), 1),
            'qi_deficiency': random.randint(0, 10),
            'blood_stasis': random.randint(0, 10),
            'dampness': random.randint(0, 10),
            'heat': random.randint(0, 10),
            'diagnosis_date': patient['admission_date']
        }
        diagnoses.append(diagnosis)
    
    return pd.DataFrame(diagnoses)

def generate_treatment_data(patient_df):
    """生成治疗方案数据"""
    treatments = []
    
    # 中药方剂库
    herbal_formulas = [
        {'herbs': [{'name': '黄芪', 'dosage': 15}, {'name': '当归', 'dosage': 10}]},
        {'herbs': [{'name': '党参', 'dosage': 12}, {'name': '白术', 'dosage': 9}]},
        {'herbs': [{'name': '甘草', 'dosage': 6}, {'name': '茯苓', 'dosage': 12}]},
        {'herbs': [{'name': '川芎', 'dosage': 9}, {'name': '红花', 'dosage': 6}]},
        {'herbs': [{'name': '熟地', 'dosage': 15}, {'name': '山药', 'dosage': 12}]}
    ]
    
    # 针灸穴位库
    acupuncture_points = [
        ['足三里', '合谷', '曲池'],
        ['百会', '风池', '太阳'],
        ['中脘', '天枢', '关元'],
        ['肺俞', '脾俞', '肾俞']
    ]
    
    treatment_types = ['中药', '针灸', '推拿', '综合']
    
    for _, patient in patient_df.iterrows():
        treatment = {
            'patient_id': patient['patient_id'],
            'treatment_type': random.choice(treatment_types),
            'herbal_formula': json.dumps(random.choice(herbal_formulas), ensure_ascii=False),
            'acupuncture_points': json.dumps(random.choice(acupuncture_points), ensure_ascii=False),
            'treatment_duration': random.randint(7, 30),
            'treatment_frequency': random.randint(1, 3),
            'dosage': round(random.uniform(10, 30), 1),
            'start_date': patient['admission_date'],
            'end_date': patient['discharge_date']
        }
        treatments.append(treatment)
    
    return pd.DataFrame(treatments)

def generate_efficacy_data(patient_df):
    """生成疗效评估数据"""
    efficacies = []
    
    for _, patient in patient_df.iterrows():
        # 基础疗效分数（0-100）
        base_score = random.uniform(60, 95)
        
        efficacy = {
            'patient_id': patient['patient_id'],
            'efficacy_score': round(base_score, 1),
            'symptom_improvement': round(random.uniform(50, 90), 1),
            'lab_improvement': round(random.uniform(40, 85), 1),
            'adverse_events': random.randint(0, 3),
            'follow_up_result': random.choice(['痊愈', '显效', '有效', '无效']),
            'assessment_date': patient['discharge_date'] + timedelta(days=7)
        }
        
        efficacies.append(efficacy)
    
    return pd.DataFrame(efficacies)

def main():
    """主函数"""
    print("开始生成示例数据...")
    
    # 创建数据目录
    data_dir = Path("data/raw")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成数据
    n_samples = 1000
    
    print(f"生成 {n_samples} 条患者记录...")
    patient_df = generate_patient_data(n_samples)
    patient_df.to_csv(data_dir / "patient_records.csv", index=False, encoding='utf-8')
    
    print("生成中医四诊数据...")
    tcm_df = generate_tcm_diagnosis_data(patient_df)
    tcm_df.to_csv(data_dir / "tcm_diagnosis.csv", index=False, encoding='utf-8')
    
    print("生成治疗方案数据...")
    treatment_df = generate_treatment_data(patient_df)
    treatment_df.to_csv(data_dir / "treatment_plans.csv", index=False, encoding='utf-8')
    
    print("生成疗效评估数据...")
    efficacy_df = generate_efficacy_data(patient_df)
    efficacy_df.to_csv(data_dir / "efficacy_assessment.csv", index=False, encoding='utf-8')
    
    print("数据生成完成！")
    print(f"患者记录: {len(patient_df)} 条")
    print(f"中医诊断: {len(tcm_df)} 条")
    print(f"治疗方案: {len(treatment_df)} 条")
    print(f"疗效评估: {len(efficacy_df)} 条")
    print(f"数据已保存至: {data_dir}")

if __name__ == "__main__":
    main()