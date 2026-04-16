import os
import platform
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont

# 核心生成逻辑
def generate_mosaic_image(large_text, small_text):
    if not large_text:
        return False, "大字不能为空！"
    if not small_text:
        small_text = "生命在于运动"

    # 智能识别操作系统字体
    system = platform.system()
    if system == "Windows":
        font_path = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑
        if not os.path.exists(font_path): font_path = "C:/Windows/Fonts/simhei.ttf" # 黑体兜底
    else:
        font_path = "/System/Library/Fonts/PingFang.ttc" # Mac 苹方

    if not os.path.exists(font_path):
        return False, f"找不到系统字体: {font_path}"

    try:
        mask_font = ImageFont.truetype(font_path, 200)
        render_font = ImageFont.truetype(font_path, 12)
    except Exception as e:
        return False, f"字体加载失败: {e}"

    # 1. 制作大字掩模
    temp_img = Image.new('1', (200 * len(large_text), 250), color=1)
    ImageDraw.Draw(temp_img).text((0, 0), large_text, font=mask_font, fill=0)
    bbox = temp_img.getbbox()
    if not bbox: return False, "生成失败，请输入有效汉字"
    mask_img = temp_img.crop(bbox)
    mask_w, mask_h = mask_img.size

    # 2. 生成高清大图
    step = 13 # 12像素 + 1像素间距
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

    # 3. 保存到桌面
    desktop = os.path.join(os.path.expanduser("~"), 'Desktop')
    save_path = os.path.join(desktop, f"字中字_{large_text}.png")
    final_img.save(save_path, "PNG")
    return True, f"成功！图片已保存至桌面:\n{save_path}"

# 绘制图形界面
def on_generate():
    btn_generate.config(text="生成中...", state=tk.DISABLED)
    root.update()
    success, msg = generate_mosaic_image(entry_large.get(), entry_small.get())
    if success:
        messagebox.showinfo("完成", msg)
    else:
        messagebox.showerror("错误", msg)
    btn_generate.config(text="一键生成", state=tk.NORMAL)

root = tk.Tk()
root.title("字中字生成器")
root.geometry("300x200")
root.eval('tk::PlaceWindow . center')

tk.Label(root, text="输入大轮廓字：").pack(pady=5)
entry_large = tk.Entry(root, width=20)
entry_large.pack()

tk.Label(root, text="输入填充小字：").pack(pady=5)
entry_small = tk.Entry(root, width=20)
entry_small.insert(0, "生命在于运动")
entry_small.pack()

btn_generate = tk.Button(root, text="一键生成", command=on_generate, height=2)
btn_generate.pack(pady=20)

root.mainloop()
