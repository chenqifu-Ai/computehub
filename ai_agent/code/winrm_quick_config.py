#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinRM极速配置 - 最简方案
"""

print("🚀 WinRM极速配置")
print("=" * 40)

print("🎯 目标设备: 192.168.2.134")
print("📊 状态: WinRM服务已运行 (端口5985开放)")
print("🔧 只需配置认证")

print("\n" + "=" * 40)
print("⚡ 执行命令 (在目标设备上):")
print("powershell -Command \"")
print("Enable-PSRemoting -Force;")
print("Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '*' -Force;")
print("Set-Item WSMan:\\localhost\\Service\\Auth\\Basic -Value $true;")
print("Restart-Service WinRM")
print("\"")

print("\n" + "=" * 40)
print("🔗 连接命令 (配置后):")
print("test-wsman -ComputerName 192.168.2.134")
print("Enter-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential)")

print("\n" + "=" * 40)
print("📋 凭据:")
print("地址: 192.168.2.134")
print("用户: chen")
print("密码: c9fc9f,.")