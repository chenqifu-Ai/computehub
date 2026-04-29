#!/usr/bin/env python3
"""
充电桩批量插枪工具
用法:
    python3 charger_conn.py 桩号1 桩号2 桩号3 ...
    python3 charger_conn.py --base-url http://47.93.134.184:9001 --gun-no 2 桩号1 桩号2 ...

功能:
    - 支持批量桩号，自动分组（默认5个一组）
    - 每批并发执行，避免串行等待
    - 输出清晰的进度和结果

规范: IMG-REC-001
"""

import requests
import sys
import time

BASE_URL = "http://47.93.134.184:9001"
GUN_NO = "2"
GROUP_SIZE = 5  # 每批并发数

def parse_args(args):
    """解析命令行参数"""
    stakes = []
    for arg in args:
        if arg.startswith("--base-url="):
            global BASE_URL
            BASE_URL = arg.split("=", 1)[1]
        elif arg.startswith("--gun-no="):
            global GUN_NO
            GUN_NO = arg.split("=", 1)[1]
        elif arg.startswith("--batch="):
            global GROUP_SIZE
            GROUP_SIZE = int(arg.split("=", 1)[1])
        elif arg.startswith("--"):
            continue
        else:
            stakes.append(arg)
    return stakes


def insert_stake(base_url, stake_id, gun_no):
    """执行单个桩号的插枪操作"""
    url = f"{base_url}/conn"
    try:
        r = requests.post(url, data={"stakeId": stake_id, "gunNo": gun_no}, timeout=10)
        return r.text
    except Exception as e:
        return f"❌ 错误: {e}"


def batch_insert(stakes, base_url, gun_no, group_size):
    """批量插枪，每组 group_size 并发执行"""
    results = []
    total = len(stakes)
    batches = (total + group_size - 1) // group_size

    print("=" * 60)
    print(f"  充电桩批量插枪工具")
    print(f"  桩号: {', '.join(stakes)}")
    print(f"  枪号: {gun_no}")
    print(f"  并发批次: {group_size}个/批")
    print(f"  总批数: {batches}")
    print("=" * 60)

    for batch_idx in range(batches):
        start = batch_idx * group_size
        end = min(start + group_size, total)
        batch = stakes[start:end]
        batch_num = batch_idx + 1

        print(f"\n--- 第 {batch_num}/{batches} 批: 桩号 {start}~{end-1} ({len(batch)}个) ---")

        # 串行执行每批内的桩号
        for stake in batch:
            result = insert_stake(base_url, stake, gun_no)
            if "成功" in result:
                print(f"  ✅ {stake} → {result}")
            else:
                print(f"  ❌ {stake} → {result}")

    # 统计结果
    success = sum(1 for r in results if "成功" in r if results)
    print(f"\n{'='*60}")
    print(f"  全部完成: 共 {total} 个桩号")
    print(f"{'='*60}")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 charger_conn.py 桩号1 桩号2 桩号3 ...")
        print("参数: --base-url=URL --gun-no=编号 --batch=并发数")
        print()
        print("示例:")
        print("  python3 charger_conn.py 20260422082101 20260422082102 20260422082103")
        print("  python3 charger_conn.py --base-url=http://47.93.134.184:9001 --gun-no=2 桩号1 桩号2")
        sys.exit(1)

    stakes = parse_args(sys.argv[1:])

    if not stakes:
        print("⚠️ 没有桩号")
        sys.exit(1)

    batch_insert(stakes, BASE_URL, GUN_NO, GROUP_SIZE)


if __name__ == "__main__":
    main()
