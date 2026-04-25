#!/usr/bin/env python3
"""
OpenClaw 系统完整备份脚本
- 备份所有配置文件
- 备份记忆和工作区文件  
- 创建时间戳备份目录
- 生成备份清单和校验和
"""

import os
import sys
import shutil
import hashlib
import time
from datetime import datetime
from pathlib import Path

class SystemBackup:
    def __init__(self):
        self.backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_root = "/root/.openclaw/backups"
        self.backup_dir = f"{self.backup_root}/openclaw_backup_{self.backup_time}"
        
        # 要备份的关键目录和文件
        self.backup_paths = [
            # 配置文件
            "/root/.openclaw/config",
            "/root/.openclaw/gateway.conf",
            "/root/.openclaw/plugins.json",
            "/root/.openclaw/security.json",
            
            # 工作区文件
            "/root/.openclaw/workspace",
            
            # 扩展插件
            "/root/.openclaw/extensions",
            
            # 内存和日志（如果存在）
            "/root/.openclaw/logs",
        ]
        
        self.manifest = []
        
    def calculate_checksum(self, filepath):
        """计算文件的MD5校验和"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return "ERROR"
    
    def backup_file_or_dir(self, source_path, dest_path):
        """备份单个文件或目录"""
        if not os.path.exists(source_path):
            print(f"   ⚠️  跳过不存在的路径: {source_path}")
            return
            
        try:
            if os.path.isfile(source_path):
                # 备份单个文件
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(source_path, dest_path)
                checksum = self.calculate_checksum(source_path)
                self.manifest.append({
                    "source": source_path,
                    "backup": dest_path,
                    "type": "file",
                    "size": os.path.getsize(source_path),
                    "checksum": checksum
                })
                print(f"   ✅ 文件: {source_path} -> {dest_path}")
            else:
                # 备份目录
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                # 计算目录中所有文件的校验和
                total_size = 0
                file_count = 0
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, source_path)
                        backup_file_path = os.path.join(dest_path, rel_path)
                        checksum = self.calculate_checksum(file_path)
                        self.manifest.append({
                            "source": file_path,
                            "backup": backup_file_path,
                            "type": "file_in_dir",
                            "size": os.path.getsize(file_path),
                            "checksum": checksum
                        })
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                
                self.manifest.append({
                    "source": source_path,
                    "backup": dest_path,
                    "type": "directory",
                    "file_count": file_count,
                    "total_size": total_size
                })
                print(f"   ✅ 目录: {source_path} -> {dest_path} ({file_count} files)")
                
        except Exception as e:
            print(f"   ❌ 备份失败 {source_path}: {str(e)}")
            self.manifest.append({
                "source": source_path,
                "backup": dest_path,
                "type": "failed",
                "error": str(e)
            })
    
    def create_backup(self):
        """执行完整备份"""
        print("💾 开始 OpenClaw 系统完整备份...")
        print(f"🕐 备份时间: {self.backup_time}")
        print(f"📁 备份目录: {self.backup_dir}")
        print("=" * 60)
        
        # 创建备份目录
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 备份每个路径
        for source_path in self.backup_paths:
            if os.path.exists(source_path):
                source_name = os.path.basename(source_path.rstrip('/'))
                if not source_name:  # 处理根目录情况
                    source_name = "root"
                dest_path = os.path.join(self.backup_dir, source_name)
                print(f"\n📦 备份: {source_path}")
                self.backup_file_or_dir(source_path, dest_path)
            else:
                print(f"\n⚠️  跳过不存在的路径: {source_path}")
        
        # 生成备份清单
        self.generate_manifest()
        
        # 显示备份摘要
        self.show_summary()
        
        print(f"\n✅ 备份完成!")
        print(f"📂 备份位置: {self.backup_dir}")
        print(f"📋 清单文件: {self.backup_dir}/BACKUP_MANIFEST.json")
        
        # 同时创建一个压缩包（可选）
        self.create_compressed_backup()
    
    def generate_manifest(self):
        """生成备份清单"""
        manifest_data = {
            "backup_info": {
                "timestamp": self.backup_time,
                "backup_directory": self.backup_dir,
                "openclaw_version": self.get_openclaw_version(),
                "system_info": self.get_system_info()
            },
            "files": self.manifest,
            "stats": self.get_backup_stats()
        }
        
        manifest_path = os.path.join(self.backup_dir, "BACKUP_MANIFEST.json")
        with open(manifest_path, 'w') as f:
            import json
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
    
    def get_openclaw_version(self):
        """获取 OpenClaw 版本信息"""
        try:
            result = os.popen("openclaw --version 2>/dev/null").read().strip()
            return result if result else "unknown"
        except:
            return "unknown"
    
    def get_system_info(self):
        """获取系统信息"""
        import platform
        return {
            "os": platform.system(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "user": os.getenv("USER", "unknown")
        }
    
    def get_backup_stats(self):
        """获取备份统计信息"""
        total_files = len([f for f in self.manifest if f.get("type") in ["file", "file_in_dir"]])
        total_size = sum([f.get("size", 0) for f in self.manifest if f.get("size")])
        failed_count = len([f for f in self.manifest if f.get("type") == "failed"])
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "failed_files": failed_count,
            "backup_directory": self.backup_dir
        }
    
    def show_summary(self):
        """显示备份摘要"""
        stats = self.get_backup_stats()
        print(f"\n📊 备份摘要:")
        print(f"   总文件数: {stats['total_files']}")
        print(f"   总大小: {stats['total_size_mb']} MB")
        print(f"   失败文件: {stats['failed_files']}")
    
    def create_compressed_backup(self):
        """创建压缩备份包"""
        print(f"\n📦 创建压缩备份包...")
        try:
            # 使用 tar.gz 压缩
            backup_parent = os.path.dirname(self.backup_dir)
            backup_name = os.path.basename(self.backup_dir)
            
            os.chdir(backup_parent)
            os.system(f"tar -czf {backup_name}.tar.gz {backup_name}")
            
            compressed_path = f"{self.backup_dir}.tar.gz"
            if os.path.exists(compressed_path):
                compressed_size = os.path.getsize(compressed_path)
                print(f"   ✅ 压缩包: {compressed_path}")
                print(f"   📏 压缩大小: {round(compressed_size / (1024 * 1024), 2)} MB")
            else:
                print(f"   ⚠️  压缩失败")
        except Exception as e:
            print(f"   ❌ 压缩失败: {str(e)}")

if __name__ == "__main__":
    backup = SystemBackup()
    backup.create_backup()