import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path
import threading
from flask import Flask, request, jsonify

# 1. تعريف تطبيق Flask خارج الكلاس
app = Flask(__name__)
face_instance = None  # متغير عالمي للوصول للكائن

class RobotFace:
    def __init__(self, master):
        self.master = master
        self.setup_window()
        self.canvas = tk.Canvas(master, width=500, height=500, bg='black', highlightthickness=0)
        self.canvas.pack()

        self.expressions = {}
        self.current_expression = None
        self.load_expressions()
        self.set_expression("neutral")
        self.animate()

    def setup_window(self):
        self.master.title("Araba Mart Robot")
        self.master.geometry("500x500")
        self.master.configure(bg='black')
        self.master.resizable(False, False)

    def load_expressions(self):
        # ملاحظة: تأكد من وجود المجلد والصور فعلياً
        base_path = Path("assets") # استبدلها بـ config.ASSETS_DIR
        files = [("neutral", "neutral.gif"), ("happy", "happy.gif"), ("sad", "sad.gif")]

        for name, filename in files:
            path = base_path / filename
            if path.exists():
                gif = Image.open(path)
                frames = [ImageTk.PhotoImage(gif.copy().resize((500, 500))) for i in range(getattr(gif, 'n_frames', 1)) if not gif.seek(i)]
                self.expressions[name] = {"frames": frames, "total": len(frames), "idx": 0}

    def set_expression(self, name):
        name = name.lower()
        if name in self.expressions:
            self.expressions[name]["idx"] = 0
            self.current_expression = self.expressions[name]
            print(f"Changed to: {name}")

    def animate(self):
        if self.current_expression:
            idx = self.current_expression["idx"]
            frame = self.current_expression["frames"][idx]
            self.canvas.delete("all")
            self.canvas.create_image(250, 250, image=frame)
            self.current_expression["idx"] = (idx + 1) % self.current_expression["total"]
        self.master.after(100, self.animate)

# 2. تعريف الـ Route خارج الكلاس واستخدام المتغير العالمي
@app.route('/call_func', methods=['POST'])
def handle_call():
    data = request.json
    func_name = data.get("function")
    if face_instance:
        # استخدام master.after لضمان تنفيذ التغيير في خيط Tkinter الأساسي
        face_instance.master.after(0, face_instance.set_expression, func_name)
        return jsonify({"status": "success", "message": f"Face changed to {func_name}"})
    return jsonify({"status": "error", "message": "Face not initialized"}), 500

def run_flask():
    # تشغيل السيرفر في خيط منفصل
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    root = tk.Tk()
    face_instance = RobotFace(root)

    # 3. بدء خيط Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    root.mainloop()
