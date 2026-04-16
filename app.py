import os
import platform
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont
import threading

def process_image(large_text, small_text):
    try:
        if not large_text:
            raise ValueError("大字不能为空！")
        if not small_text:
            small_text = "生命在于运动"

        # 1. 弹出保存路径选择框 (让用户自己选存哪里，完美避开 OneDrive 路径问题)
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG图片", "*.png")],
            initialfile=f"字中字_{large_text[:4]}.png",
            title="选择保存位置"
        )
        if not save_path:
            # 如果用户点了取消，直接重置按钮并退出
            root.after(0, reset_button)
            return

        # 2. 识别系统字体
        system = platform.system()
        if system == "Windows":
            font_path = "C:/Windows/Fonts/msyh.ttc"
            if not os.path.exists(font_path): font_path = "C:/Windows/Fonts/simhei.ttf"
        else:
            font_path = "/System/Library/Fonts/PingFang.ttc"

        if not os.path.exists(font_path):
            raise FileNotFoundError(f"找不到系统字体: {font_path}")

        # 【关键优化】：将采样率从 200 降到 100。
        # 对于长句子，100 已经非常清晰了，且计算速度能提升 4 倍以上！
        mask_font_size = 20
        mask_font = ImageFont.truetype(font_path, mask_font_size)
        render_font = ImageFont.truetype(font_path, 12)

        # 3. 掩模生成
        temp_w = mask_font_size * len(large_text)
        temp_img = Image.new('1', (temp_w, mask_font_size + 50), color=1)
        ImageDraw.Draw(temp_img).text((0, 0), large_text, font=mask_font, fill=0)
        
        bbox = temp_img.getbbox()
        if not bbox:
            raise ValueError("生成失败，可能输入了不支持的符号。")
        
        mask_img = temp_img.crop(bbox)
        mask_w, mask_h = mask_img.size

        # 4. 高清绘制
        step = 13
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

        # 5. 保存文件
        final_img.save(save_path, "PNG")
        
        # 成功提示 (使用 root.after 确保在界面主线程中弹出)
        root.after(0, lambda: messagebox.showinfo("完成", f"图片已成功保存！"))

    except Exception as e:
        # 捕获任何潜在崩溃，并以弹窗形式告诉用户，而不是卡死
        root.after(0, lambda err=e: messagebox.showerror("发生错误", str(err)))
    finally:
        # 无论成功失败，最后一定把按钮恢复原样
        root.after(0, reset_button)

def reset_button():
    btn_generate.config(text="一键生成", state=tk.NORMAL)

def on_generate():
    large_text = entry_large.get().strip()
    small_text = entry_small.get().strip()
    
    # 禁用按钮，提示状态
    btn_generate.config(text="拼命计算中(长句较慢)...", state=tk.DISABLED)
    root.update()
    
    # 【黑科技】：启动一个后台新线程去干脏活累活，让界面保持流畅响应
    threading.Thread(target=process_image, args=(large_text, small_text), daemon=True).start()

# ================= GUI 绘制部分 =================
root = tk.Tk()
root.title("字中字生成器 v2.0")
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
