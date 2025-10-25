#!/usr/bin/env python3
"""
离线脚本：为二维码图片添加文字图注
读取图片文件名的前六个字符，叠加到图片下方

默认路径：
- 输入: ./input/
- 输出: ./output/
"""
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def add_text_to_image(image_path: Path, output_path: Path = None, font_size: int = 48):
    """
    为图片添加文字图注
    
    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径（如果为None，则覆盖原图）
        font_size: 字体大小
    """
    # 读取原图
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image {image_path}: {e}")
        return False
    
    # 确保是RGB模式
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 获取文件名（不含扩展名）的前六个字符
    filename = image_path.stem  # 不含扩展名的文件名
    text = filename[:6] if len(filename) >= 6 else filename
    
    # 创建新画布（在原图下方添加文字区域）
    img_width, img_height = img.size
    text_height = 120  # 文字区域高度
    new_height = img_height + text_height
    
    canvas = Image.new('RGB', (img_width, new_height), 'white')
    canvas.paste(img, (0, 0))
    
    # 准备绘制文字
    draw = ImageDraw.Draw(canvas)
    
    # 尝试加载字体
    font = None
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "arial.ttf",
    ]
    
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except:
            continue
    
    # 如果找不到字体，使用默认字体
    if font is None:
        print(f"Warning: Could not load TrueType font, using default font")
        font = ImageFont.load_default()
        # 使用默认字体时，通过多次绘制产生加粗效果
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = (img_width - text_width) // 2
        text_y = img_height + (text_height // 2) - 10
        
        # 多次绘制以加粗
        for offset_x in range(-2, 3):
            for offset_y in range(-2, 3):
                draw.text((text_x + offset_x, text_y + offset_y), text, fill='black', font=font)
    else:
        # 使用TrueType字体
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height_actual = bbox[3] - bbox[1]
        
        # 文字居中
        text_x = (img_width - text_width) // 2
        text_y = img_height + (text_height - text_height_actual) // 2
        
        draw.text((text_x, text_y), text, fill='black', font=font)
    
    # 保存图片
    if output_path is None:
        output_path = image_path
    
    try:
        canvas.save(output_path, format='PNG')
        print(f"✓ Processed: {image_path.name} -> {output_path.name}")
        return True
    except Exception as e:
        print(f"Error saving image {output_path}: {e}")
        return False


def process_directory(input_dir: str, output_dir: str = None, font_size: int = 48):
    """
    批量处理目录中的所有图片
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录（如果为None，则覆盖原图）
        font_size: 字体大小
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        return
    
    # 创建输出目录
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = None
    
    # 支持的图片格式
    image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
    
    # 查找所有图片文件
    image_files = [
        f for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ]
    
    if not image_files:
        print(f"No image files found in '{input_dir}'")
        return
    
    print(f"Found {len(image_files)} image(s) to process\n")
    
    success_count = 0
    for image_file in image_files:
        if output_path:
            out_file = output_path / image_file.name
        else:
            out_file = None
        
        if add_text_to_image(image_file, out_file, font_size):
            success_count += 1
    
    print(f"\n✓ Successfully processed {success_count}/{len(image_files)} images")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='为二维码图片添加文字图注（读取文件名前六个字符）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用默认路径（当前目录的 input/ 和 output/）
  python add_text_to_qrcode.py
  
  # 处理单个文件
  python add_text_to_qrcode.py -i image.png -o output.png
  
  # 批量处理目录
  python add_text_to_qrcode.py -i input_folder/ -o output_folder/
  
  # 自定义字体大小
  python add_text_to_qrcode.py -i input_folder/ -o output_folder/ --font-size 60
        """
    )
    
    parser.add_argument('-i', '--input', default='./input', help='输入图片文件或目录（默认: ./input）')
    parser.add_argument('-o', '--output', default='./output', help='输出图片文件或目录（默认: ./output）')
    parser.add_argument('--font-size', type=int, default=48, help='字体大小（默认48）')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"Error: '{args.input}' does not exist")
        print(f"\n请确保已创建 '{args.input}' 目录并放入需要处理的图片")
        sys.exit(1)
    
    # 判断是文件还是目录
    if input_path.is_file():
        # 处理单个文件
        output_path = Path(args.output)
        if add_text_to_image(input_path, output_path, args.font_size):
            print("\n✓ Image processed successfully")
        else:
            print("\n✗ Failed to process image")
            sys.exit(1)
    
    elif input_path.is_dir():
        # 批量处理目录
        process_directory(args.input, args.output, args.font_size)
    
    else:
        print(f"Error: '{args.input}' is not a file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
