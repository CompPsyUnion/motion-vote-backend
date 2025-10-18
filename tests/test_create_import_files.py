"""
参与者批量导入功能测试脚本

用于测试CSV和Excel文件的批量导入功能
"""

import csv

from openpyxl import Workbook


def create_test_csv(filename: str = "test_participants.csv"):
    """创建测试用CSV文件"""
    data = [
        ["姓名", "手机号", "备注"],
        ["张三", "13800138000", "VIP会员"],
        ["李四", "13900139000", ""],
        ["王五", "", "普通参与者"],
        ["赵六", "13600136000", "特邀嘉宾"],
        ["钱七", "13700137000", "媒体记者"],
    ]

    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    print(f"✅ CSV测试文件已创建: {filename}")


def create_test_excel(filename: str = "test_participants.xlsx"):
    """创建测试用Excel文件"""
    wb = Workbook()
    ws = wb.active

    if ws is None:
        print("❌ 创建工作表失败")
        return

    ws.title = "参与者列表"

    # 添加数据
    data = [
        ["姓名", "手机号", "备注"],
        ["张三", "13800138000", "VIP会员"],
        ["李四", "13900139000", ""],
        ["王五", "", "普通参与者"],
        ["赵六", "13600136000", "特邀嘉宾"],
        ["钱七", "13700137000", "媒体记者"],
    ]

    for row_data in data:
        ws.append(row_data)

    # 设置列宽
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 30

    wb.save(filename)
    print(f"✅ Excel测试文件已创建: {filename}")


def create_invalid_csv(filename: str = "test_invalid.csv"):
    """创建包含错误的CSV文件，用于测试错误处理"""
    data = [
        ["姓名", "手机号", "备注"],
        ["张三", "13800138000", "正常数据"],
        ["", "13900139000", "姓名为空"],  # 错误：姓名为空
        ["李四", "13900139000", "正常数据"],
        ["张三", "13800138000", "重复姓名"],  # 错误：重复姓名
        ["王五", "", "正常数据"],
    ]

    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    print(f"✅ 包含错误的CSV测试文件已创建: {filename}")


def create_large_csv(filename: str = "test_large.csv", count: int = 100):
    """创建大量数据的CSV文件，用于测试性能"""
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["姓名", "手机号", "备注"])

        for i in range(1, count + 1):
            name = f"参与者{i:04d}"
            phone = f"138{i:08d}"
            note = f"测试数据{i}"
            writer.writerow([name, phone, note])

    print(f"✅ 大批量CSV测试文件已创建: {filename} (包含 {count} 条记录)")


def verify_csv_encoding(filename: str):
    """验证CSV文件编码"""
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']

    for encoding in encodings:
        try:
            with open(filename, 'r', encoding=encoding) as f:
                content = f.read()
                print(f"✅ 文件可以使用 {encoding} 编码读取")
                print(f"   前100个字符: {content[:100]}")
                break
        except UnicodeDecodeError:
            print(f"❌ 文件无法使用 {encoding} 编码读取")


def main():
    """主函数：创建所有测试文件"""
    print("=" * 60)
    print("创建参与者批量导入测试文件")
    print("=" * 60)
    print()

    # 创建正常的测试文件
    print("1. 创建正常测试文件:")
    create_test_csv("test_participants.csv")
    create_test_excel("test_participants.xlsx")
    print()

    # 创建包含错误的测试文件
    print("2. 创建错误数据测试文件:")
    create_invalid_csv("test_invalid.csv")
    print()

    # 创建大批量测试文件
    print("3. 创建性能测试文件:")
    create_large_csv("test_large.csv", 100)
    print()

    # 验证编码
    print("4. 验证CSV文件编码:")
    verify_csv_encoding("test_participants.csv")
    print()

    print("=" * 60)
    print("✅ 所有测试文件创建完成！")
    print("=" * 60)
    print()
    print("测试文件列表:")
    print("  - test_participants.csv    (正常数据)")
    print("  - test_participants.xlsx   (正常数据)")
    print("  - test_invalid.csv         (包含错误)")
    print("  - test_large.csv           (大批量数据)")
    print()
    print("使用方法:")
    print("  1. 使用API上传这些文件进行测试")
    print("  2. 检查导入结果中的success和failed数量")
    print("  3. 查看错误信息是否准确")
    print()


if __name__ == "__main__":
    main()
