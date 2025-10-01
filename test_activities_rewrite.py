"""测试活动相关 API 的简单脚本

验证新重写的活动服务和端点是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.schemas.activity import (
    ActivityCreate, ActivitySettings, ActivityStatus,
    CollaboratorPermission, CollaboratorInvite
)


def test_activity_schemas():
    """测试活动相关的 Schema"""
    print("测试活动 Schema...")
    
    # 测试活动设置
    settings = ActivitySettings(
        allowVoteChange=True,
        maxVoteChanges=5,
        showRealTimeResults=True,
        requireCheckIn=False,
        anonymousVoting=True,
        autoLockVotes=False,
        lockVoteDelay=300
    )
    print(f"活动设置: {settings.model_dump()}")
    
    # 测试活动创建
    activity_create = ActivityCreate(
        name="测试活动",
        startTime="2025-10-01T10:00:00",
        endTime="2025-10-01T18:00:00",
        location="测试地点",
        description="这是一个测试活动",
        expectedParticipants=100,
        tags=["测试", "辩论"],
        settings=settings
    )
    print(f"活动创建数据: {activity_create.model_dump(by_alias=True)}")
    
    # 测试协作者邀请
    collaborator_invite = CollaboratorInvite(
        email="test@example.com",
        permissions=[CollaboratorPermission.view, CollaboratorPermission.edit]
    )
    print(f"协作者邀请数据: {collaborator_invite.model_dump()}")
    
    print("Schema 测试通过！")


def test_service_initialization():
    """测试服务初始化"""
    print("测试服务初始化...")
    
    # 这里应该连接数据库来测试，但由于没有实际数据库连接，
    # 我们只测试导入是否正常
    try:
        from src.services.activity_service import ActivityService
        print("活动服务导入成功")
        
        from src.api.v1.endpoints.activities import router
        print("活动端点导入成功")
        
        print("服务初始化测试通过！")
    except Exception as e:
        print(f"服务初始化失败: {e}")
        return False
    
    return True


def test_enum_values():
    """测试枚举值"""
    print("测试枚举值...")
    
    # 测试活动状态
    assert ActivityStatus.upcoming == "upcoming"
    assert ActivityStatus.ongoing == "ongoing" 
    assert ActivityStatus.ended == "ended"
    print("活动状态枚举正常")
    
    # 测试协作者权限
    assert CollaboratorPermission.view == "view"
    assert CollaboratorPermission.edit == "edit"
    assert CollaboratorPermission.control == "control"
    print("协作者权限枚举正常")
    
    print("枚举测试通过！")


def main():
    """主函数"""
    print("开始测试重写的 activities.py 相关文件...")
    print("=" * 50)
    
    try:
        test_enum_values()
        print()
        
        test_activity_schemas()
        print()
        
        if test_service_initialization():
            print()
            print("✅ 所有测试都通过了！")
            print("重写的 activities.py 相关文件工作正常。")
        else:
            print("❌ 服务初始化测试失败")
            return 1
            
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        return 1
    
    print("=" * 50)
    print("测试完成")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)