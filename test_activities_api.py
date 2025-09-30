#!/usr/bin/env python3
"""
测试活动API的各种查询参数组合
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_activities_api():
    """测试活动列表API的各种参数组合"""
    
    # 测试用例列表
    test_cases = [
        # 基本测试
        {"name": "无参数", "params": {}},
        {"name": "只有页码", "params": {"page": 1}},
        {"name": "只有限制", "params": {"limit": 10}},
        
        # 状态筛选
        {"name": "状态筛选-upcoming", "params": {"status": "upcoming"}},
        {"name": "状态筛选-ongoing", "params": {"status": "ongoing"}},
        {"name": "状态筛选-ended", "params": {"status": "ended"}},
        
        # 角色筛选
        {"name": "角色筛选-owner", "params": {"role": "owner"}},
        {"name": "角色筛选-collaborator", "params": {"role": "collaborator"}},
        
        # 搜索测试
        {"name": "搜索-单词", "params": {"search": "测试"}},
        {"name": "搜索-多词", "params": {"search": "测试 活动"}},
        {"name": "搜索-空字符串", "params": {"search": ""}},
        {"name": "搜索-空格", "params": {"search": "   "}},
        
        # 组合测试
        {"name": "完整组合", "params": {
            "page": 1, 
            "limit": 5, 
            "status": "upcoming", 
            "role": "owner", 
            "search": "会议"
        }},
        
        # 边界测试
        {"name": "大页码", "params": {"page": 999}},
        {"name": "最小限制", "params": {"limit": 1}},
        {"name": "最大限制", "params": {"limit": 100}},
    ]
    
    print("🚀 开始测试活动列表API...")
    print("=" * 50)
    
    for test_case in test_cases:
        print(f"\n📝 测试: {test_case['name']}")
        print(f"📋 参数: {test_case['params']}")
        
        try:
            # 发送请求 (注意：这里需要认证，实际测试时需要添加认证头)
            response = requests.get(
                f"{BASE_URL}/activities/",
                params=test_case['params']
            )
            
            print(f"📊 状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 成功! 返回 {len(data.get('items', []))} 条记录")
                print(f"📈 总计: {data.get('total', 0)}, 页码: {data.get('page', 0)}")
            elif response.status_code == 401:
                print("🔐 需要认证 (这是预期的)")
            else:
                print(f"❌ 错误: {response.text}")
                
        except Exception as e:
            print(f"💥 异常: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成!")

if __name__ == "__main__":
    test_activities_api()
