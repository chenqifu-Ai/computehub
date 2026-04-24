#!/usr/bin/env python3
"""
批量停止所有cron任务脚本
"""
import json
import subprocess
import sys

def get_cron_jobs():
    """获取所有cron任务"""
    try:
        result = subprocess.run(['openclaw', 'cron', 'list'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"获取cron任务失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"执行命令出错: {e}")
        return None

def disable_cron_job(job_id):
    """禁用单个cron任务"""
    try:
        result = subprocess.run(['openclaw', 'cron', 'update', job_id, '--enabled', 'false'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ 已禁用任务: {job_id}")
            return True
        else:
            print(f"❌ 禁用任务失败 {job_id}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 禁用任务出错 {job_id}: {e}")
        return False

def main():
    """主函数"""
    print("🛑 开始停止所有cron任务...")
    
    # 获取所有cron任务
    cron_data = get_cron_jobs()
    if not cron_data or 'jobs' not in cron_data:
        print("❌ 无法获取cron任务列表")
        return False
    
    jobs = cron_data['jobs']
    print(f"📋 找到 {len(jobs)} 个cron任务")
    
    # 禁用所有任务
    success_count = 0
    for job in jobs:
        job_id = job['id']
        job_name = job.get('name', '未知任务')
        enabled = job.get('enabled', False)
        
        if enabled:
            print(f"\n🔄 正在禁用: {job_name} ({job_id})")
            if disable_cron_job(job_id):
                success_count += 1
        else:
            print(f"⏸️  任务已禁用: {job_name}")
    
    print(f"\n🎯 任务停止完成!")
    print(f"✅ 成功禁用: {success_count} 个任务")
    print(f"⏸️  已禁用: {len(jobs) - success_count} 个任务")
    print(f"📊 总共: {len(jobs)} 个任务")
    
    return True

if __name__ == "__main__":
    main()