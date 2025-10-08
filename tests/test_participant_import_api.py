"""
参与者批量导入API测试示例

展示如何使用API进行参与者批量导入
"""

import requests
import json


# 配置
BASE_URL = "http://localhost:8000/api/v1"
ACTIVITY_ID = "your-activity-id"  # 替换为实际的活动ID
TOKEN = "your-access-token"  # 替换为实际的访问令牌


def get_headers():
    """获取请求头"""
    return {
        "Authorization": f"Bearer {TOKEN}"
    }


def test_download_csv_template():
    """测试下载CSV模板"""
    print("=" * 60)
    print("测试：下载CSV模板")
    print("=" * 60)
    
    url = f"{BASE_URL}/{ACTIVITY_ID}/participants/template"
    params = {"format": "csv"}
    
    response = requests.get(url, headers=get_headers(), params=params)
    
    if response.status_code == 200:
        # 保存模板文件
        with open("downloaded_template.csv", "wb") as f:
            f.write(response.content)
        print("✅ CSV模板下载成功")
        print(f"   文件大小: {len(response.content)} bytes")
    else:
        print(f"❌ 下载失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
    
    print()


def test_download_excel_template():
    """测试下载Excel模板"""
    print("=" * 60)
    print("测试：下载Excel模板")
    print("=" * 60)
    
    url = f"{BASE_URL}/{ACTIVITY_ID}/participants/template"
    params = {"format": "excel"}
    
    response = requests.get(url, headers=get_headers(), params=params)
    
    if response.status_code == 200:
        # 保存模板文件
        with open("downloaded_template.xlsx", "wb") as f:
            f.write(response.content)
        print("✅ Excel模板下载成功")
        print(f"   文件大小: {len(response.content)} bytes")
    else:
        print(f"❌ 下载失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
    
    print()


def test_import_csv(filename: str = "test_participants.csv"):
    """测试导入CSV文件"""
    print("=" * 60)
    print(f"测试：导入CSV文件 ({filename})")
    print("=" * 60)
    
    url = f"{BASE_URL}/{ACTIVITY_ID}/participants/batch"
    
    try:
        with open(filename, "rb") as f:
            files = {"file": (filename, f, "text/csv")}
            response = requests.post(url, headers=get_headers(), files=files)
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print("✅ 导入成功")
            print(f"   总数: {result['total']}")
            print(f"   成功: {result['success']}")
            print(f"   失败: {result['failed']}")
            
            if result['errors']:
                print("   错误信息:")
                for error in result['errors']:
                    print(f"     - {error}")
        else:
            print(f"❌ 导入失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
    
    except FileNotFoundError:
        print(f"❌ 文件不存在: {filename}")
    
    print()


def test_import_excel(filename: str = "test_participants.xlsx"):
    """测试导入Excel文件"""
    print("=" * 60)
    print(f"测试：导入Excel文件 ({filename})")
    print("=" * 60)
    
    url = f"{BASE_URL}/{ACTIVITY_ID}/participants/batch"
    
    try:
        with open(filename, "rb") as f:
            files = {"file": (filename, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            response = requests.post(url, headers=get_headers(), files=files)
        
        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print("✅ 导入成功")
            print(f"   总数: {result['total']}")
            print(f"   成功: {result['success']}")
            print(f"   失败: {result['failed']}")
            
            if result['errors']:
                print("   错误信息:")
                for error in result['errors']:
                    print(f"     - {error}")
        else:
            print(f"❌ 导入失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
    
    except FileNotFoundError:
        print(f"❌ 文件不存在: {filename}")
    
    print()


def test_export_participants():
    """测试导出参与者列表"""
    print("=" * 60)
    print("测试：导出参与者列表")
    print("=" * 60)
    
    url = f"{BASE_URL}/{ACTIVITY_ID}/participants/export"
    
    response = requests.get(url, headers=get_headers())
    
    if response.status_code == 200:
        # 保存导出文件
        with open("exported_participants.csv", "wb") as f:
            f.write(response.content)
        print("✅ 导出成功")
        print(f"   文件大小: {len(response.content)} bytes")
        
        # 读取并显示前几行
        try:
            content = response.content.decode('utf-8-sig')
            lines = content.split('\n')[:5]
            print("   前5行内容:")
            for line in lines:
                print(f"     {line}")
        except:
            pass
    else:
        print(f"❌ 导出失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
    
    print()


def test_get_participants():
    """测试获取参与者列表"""
    print("=" * 60)
    print("测试：获取参与者列表")
    print("=" * 60)
    
    url = f"{BASE_URL}/{ACTIVITY_ID}/participants"
    params = {
        "page": 1,
        "limit": 10
    }
    
    response = requests.get(url, headers=get_headers(), params=params)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 获取成功")
        print(f"   总数: {result['total']}")
        print(f"   当前页: {result['page']}")
        print(f"   每页数量: {result['limit']}")
        print(f"   总页数: {result['totalPages']}")
        print(f"   当前页记录数: {len(result['items'])}")
        
        if result['items']:
            print("   前3条记录:")
            for i, item in enumerate(result['items'][:3], 1):
                print(f"     {i}. {item['name']} - {item['code']}")
    else:
        print(f"❌ 获取失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
    
    print()


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("*" * 60)
    print("参与者批量导入API测试套件")
    print("*" * 60)
    print()
    
    # 检查配置
    if TOKEN == "your-access-token" or ACTIVITY_ID == "your-activity-id":
        print("⚠️  请先配置TOKEN和ACTIVITY_ID！")
        print()
        print("修改以下变量:")
        print(f"  - TOKEN: 你的访问令牌")
        print(f"  - ACTIVITY_ID: 活动ID")
        print()
        return
    
    # 运行测试
    try:
        # 1. 下载模板
        test_download_csv_template()
        test_download_excel_template()
        
        # 2. 导入数据
        test_import_csv("test_participants.csv")
        test_import_excel("test_participants.xlsx")
        
        # 3. 导入错误数据
        test_import_csv("test_invalid.csv")
        
        # 4. 查看结果
        test_get_participants()
        
        # 5. 导出数据
        test_export_participants()
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
    
    print("*" * 60)
    print("测试完成")
    print("*" * 60)
    print()


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        
        tests = {
            "csv-template": test_download_csv_template,
            "excel-template": test_download_excel_template,
            "import-csv": lambda: test_import_csv("test_participants.csv"),
            "import-excel": lambda: test_import_excel("test_participants.xlsx"),
            "export": test_export_participants,
            "list": test_get_participants,
        }
        
        if test_name in tests:
            tests[test_name]()
        else:
            print(f"未知的测试: {test_name}")
            print(f"可用的测试: {', '.join(tests.keys())}")
    else:
        run_all_tests()


if __name__ == "__main__":
    main()
