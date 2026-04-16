import os
import platform
import textwrap
import threading
import logging
import time
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont

# ================= 配置区 =================
DEFAULT_SMALL_TEXT = "生命在于运动"

# 尺寸控制 (单位：像素)
LARGE_MASK_SIZE = 20     # 大字轮廓字号
SMALL_TEXT_SIZE = 12      # 填充小字的实际字号
GAP = 1                   # 小字之间的像素间距
MAX_CHARS_PER_LINE = 15   # 大字每行最大字数（超出自动换行）

# 颜色设置 (RGB格式)
BG_COLOR = (255, 255, 255) # 白色背景
TEXT_COLOR = (0, 0, 0)     # 黑色小字

# 日志与输出路径
LOG_FILE = os.path.expanduser("~/Desktop/字中字生成器_运行日志.log")
# =========================================

# 初始化日志模块
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8' if platform.system() == "Windows" else 'utf-8'
)

def get_font_path():
    """遍历系统，寻找合法的中文字体路径"""
    system = platform.system()
    if system == "Windows":
        possible_fonts = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf"
        ]
    else:
        possible_fonts = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Supplemental/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc"
        ]
        
    for f in possible_fonts:
        if os.path.exists(f):
            logging.info(f"成功找到系统字体: {f}")
            return f
            
    logging.error("未找到任何支持的系统级中文字体。")
    return None

def process_image(large_text, small_text, save_path):
    start_time = time.time()
    logging.info(f"开始生成任务 | 大字: '{large_text}' | 小字: '{small_text}'")
    
    try:
        font_path = get_font_path()
        if not font_path:
            raise FileNotFoundError("在您的系统上找不到任何自带的中文字体！")

        mask_font = ImageFont.truetype(font_path, LARGE_MASK_SIZE)
        render_font = ImageFont.truetype(font_path, SMALL_TEXT_SIZE)

        # 1. 掩模生成 (多行排版)
        logging.info("正在生成掩模轮廓...")
        wrapped_large_text = textwrap.fill(large_text, width=MAX_CHARS_PER_LINE)

        temp_draw = ImageDraw.Draw(Image.new('1', (1, 1)))
        bbox = temp_draw.multiline_textbbox((0, 0), wrapped_large_text, font=mask_font)
        wrapped_w = bbox[2] - bbox[0]
        wrapped_h = bbox[3] - bbox[1]

        margin = 20
        mask_w = wrapped_w + margin * 2
        mask_h = wrapped_h + margin * 2
        mask_img = Image.new('1', (mask_w, mask_h), color=1)
        ImageDraw.Draw(mask_img).multiline_text((margin, margin), wrapped_large_text, font=mask_font, fill=0, align="center")
        
        # 裁剪边缘
        real_bbox = mask_img.getbbox()
        if not real_bbox:
            raise ValueError("生成失败，可能输入了不支持的符号。")
        mask_img = mask_img.crop(real_bbox)
        mask_w, mask_h = mask_img.size
        logging.info(f"掩模生成完毕，裁剪后尺寸: {mask_w}x{mask_h}")

        # 2. 高清绘制
        logging.info("开始进行高清小字点阵填充...")
        step = SMALL_TEXT_SIZE + GAP
        final_img = Image.new('RGB', (mask_w * step, mask_h * step), color=BG_COLOR)
        final_draw = ImageDraw.Draw(final_img)

        small_text_len = len(small_text)
        char_index = 0
        
        for y in range(mask_h):
            for x in range(mask_w):
                if mask_img.getpixel((x, y)) == 0:
                    char = small_text[char_index % small_text_len]
                    char_index += 1
                    final_draw.text((x * step, y * step), char, font=render_font, fill=TEXT_COLOR)

        # 3. 保存文件
        final_img.save(save_path, "PNG")
        elapsed_time = round(time.time() - start_time, 2)
        logging.info(f"✅ 任务成功完成！图片已保存至: {save_path} (耗时: {elapsed_time}秒)")
        
        root.after(0, lambda: messagebox.showinfo("完成", f"图片已成功保存！\n耗时: {elapsed_time} 秒"))

    except Exception as e:
        logging.error(f"❌ 发生异常: {str(e)}", exc_info=True)
        root.after(0, lambda err=e: messagebox.showerror("发生错误", f"详情请查看桌面日志文件：\n{str(err)}"))
    finally:
        root.after(0, reset_button)

def reset_button():
    btn_generate.config(text="一键生成", state=tk.NORMAL)

def on_generate():
    large_text = entry_large.get().strip()
    small_text = entry_small.get().strip()
    
    if not large_text:
        messagebox.showerror("错误", "大字不能为空！")
        return
        
    if not small_text:
        small_text = DEFAULT_SMALL_TEXT
        
    # 主线程安全弹窗
    save_path = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG图片", "*.png")],
        initialfile=f"字中字_{large_text[:4]}.png",
        title="选择保存位置"
    )
    
    if not save_path:
        logging.info("用户取消了保存路径的选择。")
        return 

    btn_generate.config(text="拼命计算中(长句较慢)...", state=tk.DISABLED)
    root.update()
    
    threading.Thread(target=process_image, args=(large_text, small_text, save_path), daemon=True).start()

# ================= GUI 绘制部分 =================
if __name__ == "__main__":
    logging.info("========== 字中字生成器启动 ==========")
    root = tk.Tk()
    root.title("字中字生成器 v3.0")
    root.geometry("350x220")
    root.eval('tk::PlaceWindow . center')

    tk.Label(root, text="输入大轮廓字：").pack(pady=5)
    entry_large = tk.Entry(root, width=30)
    entry_large.pack()

    tk.Label(root, text="输入填充小字：").pack(pady=5)
    entry_small = tk.Entry(root, width=30)
    entry_small.insert(0, DEFAULT_SMALL_TEXT)
    entry_small.pack()

    btn_generate = tk.Button(root, text="一键生成", command=on_generate, height=2, width=25)
    btn_generate.pack(pady=20)

    root.mainloop()
