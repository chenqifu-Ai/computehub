#!/usr/bin/env python3
"""
《烽火三国：乱世棋局》- 项目任务分解结构 (WBS)
基于敏捷开发方法论的任务分解计划
"""

# ============================================================
# 项目总体信息
# ============================================================

PROJECT_INFO = {
    "project_name": "烽火三国：乱世棋局",
    "project_type": "3D策略战棋游戏",
    "development_methodology": "敏捷开发 (Scrum)",
    "team_size": "8-12人",
    "total_duration": "24周 (6个月)",
    "sprints": "12个双周迭代",
    "platforms": ["PC", "WebGL", "Mobile"]
}

# ============================================================
# 1. 项目阶段划分
# ============================================================

PROJECT_PHASES = {
    "phase_1": {
        "name": "预研和原型阶段",
        "duration": "4周",
        "milestone": "可玩原型",
        "priority": "高"
    },
    "phase_2": {
        "name": "核心功能开发",
        "duration": "12周", 
        "milestone": "功能完整的Alpha版本",
        "priority": "高"
    },
    "phase_3": {
        "name": "内容填充和优化",
        "duration": "6周",
        "milestone": "Beta测试版本",
        "priority": "中"
    },
    "phase_4": {
        "name": "发布准备",
        "duration": "2周",
        "milestone": "正式发布",
        "priority": "高"
    }
}

# ============================================================
# 2. 功能模块分解 (WBS Level 1)
# ============================================================

MODULE_BREAKDOWN = {
    "module_1": {
        "name": "核心游戏系统",
        "description": "基础游戏框架和核心机制",
        "priority": "最高",
        "estimated_hours": 480
    },
    "module_2": {
        "name": "3D图形和特效",
        "description": "3D渲染、模型、动画和特效系统",
        "priority": "高", 
        "estimated_hours": 360
    },
    "module_3": {
        "name": "战斗系统",
        "description": "兵棋推演战斗机制和AI",
        "priority": "高",
        "estimated_hours": 320
    },
    "module_4": {
        "name": "多人网络系统", 
        "description": "多人联机和匹配系统",
        "priority": "中",
        "estimated_hours": 280
    },
    "module_5": {
        "name": "UI/UX系统",
        "description": "用户界面和体验设计",
        "priority": "中",
        "estimated_hours": 240
    },
    "module_6": {
        "name": "内容和平衡",
        "description": "游戏内容填充和平衡调整",
        "priority": "中",
        "estimated_hours": 200
    }
}

# ============================================================
# 3. 详细任务分解 (WBS Level 2)
# ============================================================

DETAILED_TASKS = {
    "core_system": {
        "name": "核心游戏系统",
        "tasks": [
            {"id": "CORE-001", "name": "游戏状态管理", "hours": 40, "priority": "高", "dependencies": []},
            {"id": "CORE-002", "name": "回合制系统", "hours": 60, "priority": "高", "dependencies": ["CORE-001"]},
            {"id": "CORE-003", "name": "资源管理系统", "hours": 40, "priority": "中", "dependencies": ["CORE-001"]},
            {"id": "CORE-004", "name": "存档系统", "hours": 30, "priority": "中", "dependencies": ["CORE-001"]}
        ]
    },
    "graphics": {
        "name": "3D图形系统", 
        "tasks": [
            {"id": "GFX-001", "name": "3D地形系统", "hours": 80, "priority": "高", "dependencies": ["CORE-001"]},
            {"id": "GFX-002", "name": "单位模型和动画", "hours": 100, "priority": "高", "dependencies": ["GFX-001"]},
            {"id": "GFX-003", "name": "特效粒子系统", "hours": 80, "priority": "高", "dependencies": ["GFX-001"]},
            {"id": "GFX-004", "name": "摄像机系统", "hours": 40, "priority": "中", "dependencies": ["GFX-001"]}
        ]
    }
}

# ============================================================
# 4. 敏捷迭代计划
# ============================================================

SPRINT_PLAN = {
    "sprint_1": {
        "duration": "2周",
        "goal": "基础框架搭建",
        "tasks": ["CORE-001", "CORE-002", "GFX-001"],
        "team": ["程序x2", "美术x1"]
    },
    "sprint_2": {
        "duration": "2周", 
        "goal": "核心玩法原型",
        "tasks": ["CORE-003", "GFX-002", "BATTLE-001"],
        "team": ["程序x3", "美术x2", "策划x1"]
    }
}

# ============================================================
# 5. 资源需求和角色分配
# ============================================================

RESOURCE_REQUIREMENTS = {
    "roles": {
        "tech_lead": {"count": 1, "skills": "Unity/UE专家, 架构设计"},
        "backend_dev": {"count": 2, "skills": "C#/C++, 网络编程"},
        "graphics_dev": {"count": 2, "skills": "Shader, 3D图形, VFX"},
        "game_designer": {"count": 2, "skills": "游戏机制, 平衡设计"},
        "3d_artist": {"count": 3, "skills": "建模, 动画, 特效"},
        "ui_designer": {"count": 1, "skills": "UI/UX设计"},
        "qa_tester": {"count": 1, "skills": "测试, 质量保证"}
    },
    "tools": [
        "Unity 3D + URP",
        "Visual Studio / Rider", 
        "Blender / Maya",
        "Substance Painter",
        "Git + GitHub",
        "Jira / Trello"
    ]
}

# ============================================================
# 6. 风险评估和缓解措施
# ============================================================

RISK_MANAGEMENT = {
    "technical_risks": [
        {"risk": "3D性能优化", "impact": "高", "probability": "中", "mitigation": "早期性能测试, LOD优化"},
        {"risk": "网络同步问题", "impact": "高", "probability": "中", "mitigation": "采用权威服务器架构"}
    ],
    "schedule_risks": [
        {"risk": "内容开发延期", "impact": "中", "probability": "高", "mitigation": "敏捷迭代, 优先级调整"}
    ]
}

if __name__ == "__main__":
    print("✅ 三国游戏项目任务分解结构完成！")
    print("📋 包含:")
    print("  • 4个开发阶段和里程碑")
    print("  • 6大功能模块分解") 
    print("  • 详细任务列表和依赖关系")
    print("  • 敏捷迭代计划")
    print("  • 资源需求和角色分配")
    print("  • 风险评估和缓解措施")
    print("\n🎯 推荐采用敏捷开发，12个双周迭代完成")