import os
import platform
import textwrap
import threading
import logging
import time
import tempfile
import random
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont

# 解除 Python 对超大图片的“防炸弹”安全封锁
Image.MAX_IMAGE_PIXELS = None

# ================= v6.1 核心对抗配置区 =================
VERSION = "v6.1_人眼极清_AI混淆_GUI版"

# 【绝杀策略】：默认数字填充，逼迫 AI 陷入微观细节
DEFAULT_SMALL_TEXT = "123456789"

# 尺寸与排版控制 (单位：像素)
LARGE_MASK_SIZE = 35     # 【极大化】采样率 180，让大字厚实饱满
SMALL_TEXT_SIZE = 9      # 填充小字字号
GAP = 0                   # 【缩减间距】让数字挤在一起，大字更黑实
MAX_CHARS_PER_LINE = 12   # 因为字号变大，控制每行字数

JITTER_AMOUNT = 1         # 【微观抖动】1 像素错位，斩断 AI 轮廓连通域

# 颜色与对抗纹理设置
BG_COLOR = (255, 255, 255)     # 白色背景
TEXT_COLOR = (0, 0, 0)         # 纯黑色小字，增加人眼对比度

# 【防 LLM 核心】15% 的墨迹小字会变成低灰度噪点，扰乱 Grok 等大模型的语义识别
ANTI_AI_TEXTURE_PROB = 0.15    

# 45度深灰色切割线，逼疯常规 OCR
STRIPE_COLOR = (230, 230, 230) 
STRIPE_SPACING = 20            

# 日志路径 (跨平台兼容：自动存放在系统临时文件夹 /tmp 或 AppData/Local/Temp)
TEMP_DIR = tempfile.gettempdir()
LOG_FILE = os.path.join(TEMP_DIR, "字中字生成器_v6.1_运行日志.log")
# ======================================================

# 初始化无痕日志
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8' if platform.system() == "Windows" else 'utf-8'
)

def get_font_path():
    """跨平台动态识别系统并加载对应最粗字体"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_fonts = ["font.ttc", "font.ttf", "font.otf", "PingFang.ttc", "msyhbd.ttc"]
    
    # 1. 优先使用代码同级目录自带的字体
    for f in local_fonts:
        p = os.path.join(base_dir, f)
        if os.path.exists(p):
            logging.info(f"识别到本地自带字体: {p}")
            return p, 0 

    # 2. 备选系统级字体
    system = platform.system()
    if system == "Windows":
        win_fonts = ["C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]
        for p in win_fonts:
            if os.path.exists(p):
                logging.info(f"Windows 系统，加载字体: {p}")
                return p, 0
    else:
        # macOS 核心：硬编码 MobileAsset 绝密路径，防权限阻挡
        mac_fonts = [
            "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/3419f2a427639ad8c8e139149a287865a90fa17e.asset/AssetData/PingFang.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Supplemental/PingFang.ttc"
        ]
        for p in mac_fonts:
            if os.path.exists(p):
                logging.info(f"macOS 系统，加载字体: {p}")
                return p, 4  # index=4 强制召唤 macOS 盲盒里的 Semibold 粗体
                
    return None, 0

def smart_wrap_text(text, max_chars):
    final_lines = []
    for line in text.splitlines():
        line = line.rstrip() 
        if not line:
            final_lines.append("") 
            continue
        if len(line) <= max_chars:
            final_lines.append(line)
        else:
            wrapped = textwrap.wrap(line, width=max_chars, replace_whitespace=False, drop_whitespace=False)
            final_lines.extend(wrapped)
    return "\n".join(final_lines)

def process_image(large_text, small_text, save_path):
    start_time = time.time()
    logging.info(f"\n========== 【{VERSION}】开始生成任务 ==========")
    logging.info(f"大字: '{large_text}' | 小字: '{small_text}'")
    
    try:
        font_path, bold_index = get_font_path()
        if not font_path:
            raise FileNotFoundError("找不到任何支持的自带中文字体！")

        mask_font = ImageFont.truetype(font_path, LARGE_MASK_SIZE, index=bold_index)
        render_font = ImageFont.truetype(font_path, SMALL_TEXT_SIZE, index=0)

        # 1. 掩模生成与画板自适应 (解决大字被切断的问题)
        logging.info("1. 正在生成掩模轮廓与偏移修正...")
        wrapped_large_text = smart_wrap_text(large_text, MAX_CHARS_PER_LINE)

        temp_draw = ImageDraw.Draw(Image.new('1', (1, 1)))
        bbox = temp_draw.multiline_textbbox((0, 0), wrapped_large_text, font=mask_font)
        left, top, right, bottom = bbox

        margin = 40
        mask_w = int(right - left + margin * 2)
        mask_h = int(bottom - top + margin * 2)
        mask_img = Image.new('1', (mask_w, mask_h), color=1)
        ImageDraw.Draw(mask_img).multiline_text((margin - left, margin - top), wrapped_large_text, font=mask_font, fill=0, align="left")
        
        real_bbox = mask_img.getbbox()
        if not real_bbox:
            raise ValueError("生成失败，可能输入了不支持的符号。")
        mask_img = mask_img.crop(real_bbox)
        mask_w, mask_h = mask_img.size
        logging.info(f"掩模生成完毕，裁剪后尺寸: {mask_w}x{mask_h}")

        # 2. 渲染对抗画布
        logging.info("2. 开始进行对抗点阵填充 (包含Jitter与概率混淆)...")
        step = SMALL_TEXT_SIZE + GAP
        final_w, final_h = mask_w * step, mask_h * step
        final_img = Image.new('RGB', (final_w, final_h), color=BG_COLOR)
        final_draw = ImageDraw.Draw(final_img)

        # 绘制防 OCR 切割线
        for d in range(-final_h, final_w, int(STRIPE_SPACING * 1.5)): 
            final_draw.line([(d, 0), (d + final_h, final_h)], fill=STRIPE_COLOR, width=1)

        small_text_len = len(small_text)
        char_index = 0
        
        for y in range(mask_h):
            for x in range(mask_w):
                if mask_img.getpixel((x, y)) == 0:
                    char = small_text[char_index % small_text_len]
                    char_index += 1
                    
                    # 引入错位
                    jitter_x = random.randint(-JITTER_AMOUNT, JITTER_AMOUNT)
                    jitter_y = random.randint(-JITTER_AMOUNT, JITTER_AMOUNT)
                    
                    # 概率混淆策略
                    if random.random() < ANTI_AI_TEXTURE_PROB:
                        current_fill = (random.randint(60, 100), random.randint(60, 100), random.randint(80, 130))
                    else:
                        current_fill = TEXT_COLOR
                        
                    final_draw.text((x * step + jitter_x, y * step + jitter_y), char, font=render_font, fill=current_fill)

        # 3. 极致瘦身版保存 (L 模式 + JPG)
        logging.info("3. 正在执行灰度瘦身与图像压缩...")
        final_img.convert('L').save(
            save_path, 
            "JPEG", 
            quality=30,       
            optimize=True,    
            progressive=True, 
            subsampling=0
        )
        
        file_size_kb = round(os.path.getsize(save_path) / 1024, 2)
        elapsed_time = round(time.time() - start_time, 2)
        logging.info(f"✅ 任务成功！图片已保存至: {save_path} (体积: {file_size_kb}KB, 耗时: {elapsed_time}秒)")
        
        root.after(0, lambda: messagebox.showinfo("完成", f"生成成功！大模型休想看懂！\n文件大小: {file_size_kb} KB\n耗时: {elapsed_time} 秒"))

    except Exception as e:
        logging.error(f"❌ 发生异常: {str(e)}", exc_info=True)
        root.after(0, lambda err=e: messagebox.showerror("发生错误", f"发生错误：\n{str(err)}\n\n详情请查看日志文件。"))
    finally:
        root.after(0, reset_button)

def reset_button():
    btn_generate.config(text="一键生成绝杀图", state=tk.NORMAL)

def on_generate():
    large_text = entry_large.get().strip()
    small_text = entry_small.get().strip()
    
    if not large_text:
        messagebox.showerror("错误", "大字不能为空！")
        return
        
    if not small_text:
        small_text = DEFAULT_SMALL_TEXT
        
    safe_name = "".join(c for c in large_text[:4] if c.isalnum() or c in ['\u4e00', '\u9fa5'])
    
    save_path = filedialog.asksaveasfilename(
        defaultextension=".jpg",
        filetypes=[("JPEG图片", "*.jpg")],
        initialfile=f"字中字_{safe_name}.jpg",
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
    logging.info(f"========== {VERSION} 启动 ==========")
    root = tk.Tk()
    root.title("字中字生成器 v6.1 (防大模型版)")
    root.geometry("380x240")
    root.eval('tk::PlaceWindow . center')

    tk.Label(root, text="输入大轮廓字(支持长句)：", font=("Arial", 10, "bold")).pack(pady=5)
    entry_large = tk.Entry(root, width=35)
    entry_large.pack()

    tk.Label(root, text="输入填充小字(建议全数字)：", font=("Arial", 10, "bold")).pack(pady=5)
    entry_small = tk.Entry(root, width=35)
    entry_small.insert(0, DEFAULT_SMALL_TEXT)
    entry_small.pack()

    btn_generate = tk.Button(root, text="一键生成绝杀图", command=on_generate, height=2, width=25, bg="#4CAF50", fg="black")
    btn_generate.pack(pady=20)
    
    tk.Label(root, text=f"日志自动存放在: {TEMP_DIR}", font=("Arial", 8), fg="gray").pack()

    root.mainloop()
