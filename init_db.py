#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建所有数据库表
"""

from src.models import *  # 导入所有模型以确保它们被注册
from src.core.database import Base, engine
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_tables():
    """创建所有数据库表"""
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功！")

        # 显示创建的表
        print("\n📋 已创建的表:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")

    except Exception as e:
        print(f"❌ 创建数据库表时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_tables()
