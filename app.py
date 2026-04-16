import os
import platform
import textwrap
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont
import threading

def process_image(large_text, small_text, save_path):
    try:
        # 1. 识别系统字体
        system = platform.system()
        font_path = None
        if system == "Windows":
            # Windows 标准苹方或黑体路径
            possible_fonts = [
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simhei.ttf"
            ]
        else:
            # Mac 所有新老版本可能的中文字体路径（天罗地网版）
            possible_fonts = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Supplemental/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/System/Library/Fonts/STHeiti Medium.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc"
            ]
            
        for f in possible_fonts:
            if os.path.exists(f):
                font_path = f
                break

        if not font_path:
            raise FileNotFoundError("在您的系统上找不到任何系统自带的中文字体！")

        mask_font_size = 100
        mask_font = ImageFont.truetype(font_path, mask_font_size)
        render_font = ImageFont.truetype(font_path, 12)

        # 2. 掩模生成 (修复版：支持多行排版大字)
        # 【核心修复】：设置大字每行最多多少个字，超过自动换行
        max_mask_width_chars = 15 
        wrapped_large_text = textwrap.fill(large_text, width=max_mask_width_chars)

        # 创建临时画布来测量多行大字的实际尺寸 (使用新版 multiline 方法)
        temp_draw = ImageDraw.Draw(Image.new('1', (1, 1)))
        bbox = temp_draw.multiline_textbbox((0, 0), wrapped_large_text, font=mask_font)
        wrapped_w = bbox[2] - bbox[0]
        wrapped_h = bbox[3] - bbox[1]

        # 创建精准的掩模画布（留一点边距）
        mask_w = wrapped_w + 20
        mask_h = wrapped_h + 20
        mask_img = Image.new('1', (mask_w, mask_h), color=1)
        # 居中绘制多行大字
        ImageDraw.Draw(mask_img).multiline_text((10, 10), wrapped_large_text, font=mask_font, fill=0, align="center")
        
        # 3. 高清绘制
        step = 13
        # 自动换行后，final_img 的比例会趋于合理
        final_img = Image.new('RGB', (mask_w * step, mask_h * step), color=(255, 255, 255))
        final_draw = ImageDraw.Draw(final_img)

        small_text_len = len(small_text)
        char_index = 0
        
        for y in range(mask_h):
            for x in range(mask_w):
                if mask_img.getpixel((x, y)) == 0:
                    char = small_text[char_index % small_text_len]
                    char_index += 1
                    final_draw.text((x * step, y * step), char, font=render_font, fill=(0, 0, 0))

        # 4. 保存文件 (使用主线程传进来的安全路径)
        final_img.save(save_path, "PNG")
        
        root.after(0, lambda: messagebox.showinfo("完成", f"图片已成功保存！"))

    except Exception as e:
        root.after(0, lambda err=e: messagebox.showerror("发生错误", str(err)))
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
        small_text = "生命在于运动"
        
    # 在主线程弹出保存窗口
    save_path = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG图片", "*.png")],
        initialfile=f"字中字_{large_text[:4]}.png",
        title="选择保存位置"
    )
    
    if not save_path:
        return # 用户点了取消

    # 禁用按钮，提示状态
    btn_generate.config(text="拼命计算中(长句较慢)...", state=tk.DISABLED)
    root.update()
    
    # 启动后台线程，把选好的路径传进去
    threading.Thread(target=process_image, args=(large_text, small_text, save_path), daemon=True).start()

# ================= GUI 绘制部分 =================
root = tk.Tk()
root.title("字中字生成器 v2.1")
root.geometry("350x220")
root.eval('tk::PlaceWindow . center')

tk.Label(root, text="输入大轮廓字：").pack(pady=5)
entry_large = tk.Entry(root, width=30)
entry_large.pack()

tk.Label(root, text="输入填充小字：").pack(pady=5)
entry_small = tk.Entry(root, width=30)
entry_small.insert(0, "生命在于运动")
entry_small.pack()

btn_generate = tk.Button(root, text="一键生成", command=on_generate, height=2, width=25)
btn_generate.pack(pady=20)

root.mainloop()
