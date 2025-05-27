import tkinter as tk
from tkinter import ttk
import cv2
from pyzbar.pyzbar import decode
from PIL import Image, ImageTk
import pandas as pd
import qrcode
import tempfile
import threading
import time
import queue
import arabic_reshaper
import bidi.algorithm


class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("روبوت عربة مارت الذكي")
        self.root.configure(bg="black")
        self.root.geometry("800x600")

        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("TButton", font=("Segoe UI", 14), padding=10, background="#1E1E1E", foreground="white")

        # تحميل بيانات المنتجات
        self.products = pd.read_csv("products.csv")
        self.cart = []

        # إنشاء الإطارات
        self.main_frame = tk.Frame(self.root, bg="black")
        self.camera_frame = tk.Frame(self.root, bg="black")
        self.cart_frame = tk.Frame(self.root, bg="black")
        self.qr_frame = tk.Frame(self.root, bg="black")
        self.message_frame = tk.Frame(self.root, bg="black")
        self.manual_error_frame = tk.Frame(self.root, bg="black")

        # طابور للاتصال بين الثريدات
        self.queue = queue.Queue()

        self.setup_main_page()
        self.setup_camera_page()
        self.setup_cart_page()
        self.setup_qr_page()
        self.setup_message_page()
        self.setup_manual_error_page()

        self.show_frame(self.main_frame)
        self.camera_running = False
        self.last_update_time = 0
        self.cap = None

        # فحص الطابور بانتظام
        self.root.after(100, self.process_queue)

    def process_queue(self):
        try:
            while True:
                task = self.queue.get_nowait()
                task()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def setup_main_page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        self.main_frame.place(relx=0.5, rely=0.5, anchor="center")

        reshape_title = arabic_reshaper.reshape("روبوت عربة مارت الذكي")
        bidi_title = bidi.algorithm.get_display(reshape_title)
        title = tk.Label(self.main_frame, text=bidi_title, font=("Segoe UI", 24, "bold"), bg="black",
                         fg="white")
        title.pack(pady=20)

        reshape_scan = arabic_reshaper.reshape("📷مسح الباركود")
        bidi_scan = bidi.algorithm.get_display(reshape_scan)
        scan_btn = ttk.Button(self.main_frame, text=bidi_scan, command=self.start_scanning)
        scan_btn.pack(pady=10)

        reshape_cart = arabic_reshaper.reshape("🛒 عرض السلة")
        bidi_cart = bidi.algorithm.get_display(reshape_cart)
        cart_btn = ttk.Button(self.main_frame, text=bidi_cart, command=lambda: self.show_frame(self.cart_frame))
        cart_btn.pack(pady=10)

    def setup_camera_page(self):
        for widget in self.camera_frame.winfo_children():
            widget.destroy()

        self.camera_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.camera_label = tk.Label(self.camera_frame, bg="black")
        self.camera_label.pack(pady=20)

        reshape_cancel = arabic_reshaper.reshape("❌ إلغاء")
        bidi_cancel = bidi.algorithm.get_display(reshape_cancel)
        cancel_btn = ttk.Button(self.camera_frame, text=bidi_cancel, command=self.stop_camera)
        cancel_btn.pack(pady=10)

    def setup_cart_page(self):
        for widget in self.cart_frame.winfo_children():
            widget.destroy()

        self.cart_frame.place(relx=0.5, rely=0.5, anchor="center")

        reshape_cart_title = arabic_reshaper.reshape("🛒 سلة المشتريات")
        bidi_cart_title = bidi.algorithm.get_display(reshape_cart_title)
        title = tk.Label(self.cart_frame, text=bidi_cart_title, font=("Segoe UI", 20), bg="black", fg="white")
        title.pack(pady=10)

        # إدخال يدوي للباركود
        entry_frame = tk.Frame(self.cart_frame, bg="black")
        entry_frame.pack(pady=10)

        reshape_barcode_entry = arabic_reshaper.reshape("📥 أدخل الباركود:")
        bidi_barcode_entry = bidi.algorithm.get_display(reshape_barcode_entry)
        entry_label = tk.Label(entry_frame, text=bidi_barcode_entry, font=("Segoe UI", 14), bg="black", fg="white")
        entry_label.pack(side=tk.LEFT, padx=5)

        self.manual_entry = tk.Entry(entry_frame, font=("Segoe UI", 14), width=20)
        self.manual_entry.pack(side=tk.LEFT, padx=5)
        self.manual_entry.bind("<Return>", self.process_manual_entry)

        # إطار لعرض المنتجات مع شريط تمرير
        cart_container = tk.Frame(self.cart_frame, bg="black")
        cart_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(cart_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.cart_list = tk.Listbox(cart_container,
                                    width=50,
                                    height=10,
                                    font=("Segoe UI", 12),
                                    bg="#1E1E1E",
                                    fg="white",
                                    yscrollcommand=scrollbar.set)
        self.cart_list.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar.config(command=self.cart_list.yview)

        # إضافة زر حذف لكل عنصر
        self.cart_list.bind('<Double-Button-1>', self.delete_selected_item)

        reshape_total = arabic_reshaper.reshape("الإجمالي: 0.00 ريال")
        bidi_total = bidi.algorithm.get_display(reshape_total)
        self.total_label = tk.Label(self.cart_frame, text=bidi_total, font=("Segoe UI", 14), bg="black",
                                    fg="white")
        self.total_label.pack(pady=10)

        buttons_frame = tk.Frame(self.cart_frame, bg="black")
        buttons_frame.pack(pady=10)

        reshape_QR_generator = arabic_reshaper.reshape("🔲 توليد QR للسلة")
        bidi_QR_generator= bidi.algorithm.get_display(reshape_QR_generator)
        generate_qr_btn = ttk.Button(buttons_frame, text=bidi_QR_generator, command=self.generate_qr)
        generate_qr_btn.pack(side=tk.LEFT, padx=10)

        reshape_clear_cart = arabic_reshaper.reshape("🗑️ تفريغ السلة")
        bidi_clear_cart= bidi.algorithm.get_display(reshape_clear_cart)
        clear_cart_btn = ttk.Button(buttons_frame, text=bidi_clear_cart, command=self.clear_cart)
        clear_cart_btn.pack(side=tk.LEFT, padx=10)

        reshape_back = arabic_reshaper.reshape("⬅️ رجوع")
        bidi_back= bidi.algorithm.get_display(reshape_back)
        back_btn = ttk.Button(buttons_frame, text=bidi_back, command=lambda: self.show_frame(self.main_frame))
        back_btn.pack(side=tk.RIGHT, padx=10)

    def setup_qr_page(self):
        for widget in self.qr_frame.winfo_children():
            widget.destroy()

        self.qr_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.qr_label = tk.Label(self.qr_frame, bg="black")
        self.qr_label.pack(pady=20)

        reshape_back = arabic_reshaper.reshape("⬅️ رجوع")
        bidi_back= bidi.algorithm.get_display(reshape_back)
        back_btn = ttk.Button(self.qr_frame, text=bidi_back, command=lambda: self.show_frame(self.cart_frame))
        back_btn.pack(pady=10)

    def setup_message_page(self):
        for widget in self.message_frame.winfo_children():
            widget.destroy()

        self.message_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.message_label = tk.Label(self.message_frame, font=("Segoe UI", 16), bg="black", fg="white", wraplength=400)
        self.message_label.pack(pady=20)

        reshape_ok = arabic_reshaper.reshape("حسنًا")
        bidi_ok= bidi.algorithm.get_display(reshape_ok)
        ok_btn = ttk.Button(self.message_frame, text=bidi_ok, command=self.handle_message_ok)
        ok_btn.pack(pady=10)

    def setup_manual_error_page(self):
        for widget in self.manual_error_frame.winfo_children():
            widget.destroy()

        reshape_notindata = arabic_reshaper.reshape("🚫 المنتج المدخل غير موجود في قاعدة البيانات")
        bidi_notindata= bidi.algorithm.get_display(reshape_notindata)
        label = tk.Label(self.manual_error_frame, text=bidi_notindata,
                         font=("Segoe UI", 16), bg="black", fg="white", wraplength=400)
        label.pack(pady=20)

        reshape_ok = arabic_reshaper.reshape("حسنًا")
        bidi_ok= bidi.algorithm.get_display(reshape_ok)
        ok_btn = ttk.Button(self.manual_error_frame, text=bidi_ok, command=lambda: self.show_frame(self.cart_frame))
        ok_btn.pack(pady=10)

    def handle_message_ok(self):
        msg = self.message_label.cget("text")

    

        #if "السلة فارغة" in msg or "تم تفريغ السلة" in msg: for deside where to go after alart
        self.show_frame(self.cart_frame)
        

    def show_frame(self, frame):
        def _show_frame():
            for f in (self.main_frame, self.camera_frame, self.cart_frame, self.qr_frame, self.message_frame, self.manual_error_frame):
                f.place_forget()
            frame.place(relx=0.5, rely=0.5, anchor="center")
            if frame == self.cart_frame:
                self.update_cart_display()

        self.queue.put(_show_frame)

    def show_message(self, msg):
        def _show_message():

            reshape_msg = arabic_reshaper.reshape(msg)
            bidi_msg= bidi.algorithm.get_display(reshape_msg)

            self.message_label.config(text=bidi_msg)

            self.show_frame(self.message_frame)

        self.queue.put(_show_message)

    def start_scanning(self):
        self.show_frame(self.camera_frame)
        self.start_camera()

    def start_camera(self):
        if self.cap is not None:
            self.cap.release()

        self.camera_running = True
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        threading.Thread(target=self.scan_barcode, daemon=True).start()

    def stop_camera(self):
        self.camera_running = False
        time.sleep(0.1)

        def _clear_camera():
            if hasattr(self, 'camera_label') and self.camera_label.winfo_exists():
                self.camera_label.config(image="")
            if self.cap is not None:
                self.cap.release()
                self.cap = None

        self.queue.put(_clear_camera)
        self.show_frame(self.main_frame)

    def scan_barcode(self):
        while self.camera_running and self.cap is not None:
            try:
                current_time = time.time()
                if current_time - self.last_update_time < 0.1:
                    continue

                ret, frame = self.cap.read()
                if not ret:
                    continue

                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                img = img.resize((640, 480))
                imgtk = ImageTk.PhotoImage(image=img)

                def _update_camera():
                    if hasattr(self, 'camera_label') and self.camera_label.winfo_exists():
                        self.camera_label.imgtk = imgtk
                        self.camera_label.config(image=imgtk)

                self.queue.put(_update_camera)
                self.last_update_time = current_time

                try:
                    barcodes = decode(frame)
                    if barcodes:
                        barcode_data = barcodes[0].data.decode("utf-8")
                        try:
                            product_match = self.products[self.products["barcode"] == int(barcode_data)]
                            if not product_match.empty:
                                product = product_match.iloc[0].to_dict()
                                self.queue.put(lambda: self.show_product_confirmation(product))
                                self.camera_running = False
                                if self.cap is not None:
                                    self.cap.release()
                                    self.cap = None
                            else:
                                self.queue.put(lambda: self.show_message("المنتج غير موجود في قاعدة البيانات"))
                                self.camera_running = False
                                if self.cap is not None:
                                    self.cap.release()
                                    self.cap = None
                        except ValueError:
                            self.queue.put(lambda: self.show_message("باركود غير صالح"))
                            self.camera_running = False
                            if self.cap is not None:
                                self.cap.release()
                                self.cap = None
                except Exception as e:
                    print(f"Error in barcode decoding: {e}")
                    continue

            except Exception as e:
                print(f"Error in camera thread: {e}")
                break

    def show_product_confirmation(self, product):
        for widget in self.camera_frame.winfo_children():
            widget.destroy()

        self.camera_frame.place(relx=0.5, rely=0.5, anchor="center")

        product_label = tk.Label(self.camera_frame,
                                 text=f"{product['name']}\nPrice: {product['price']} SAR",
                                 font=("Segoe UI", 18),
                                 bg="black",
                                 fg="white")
        product_label.pack(pady=20)

        buttons_frame = tk.Frame(self.camera_frame, bg="black")
        buttons_frame.pack(pady=20)

        add_btn = ttk.Button(buttons_frame,
                             text="إضافة للسلة",
                             command=lambda: self.add_to_cart(product))
        add_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = ttk.Button(buttons_frame,
                                text="إلغاء",
                                command=self.return_to_camera)
        cancel_btn.pack(side=tk.RIGHT, padx=10)

    def add_to_cart(self, product):
        self.cart.append(product)
        self.update_cart_display()
        self.show_message(f"Added {product['name']} To the cart")

    def return_to_camera(self):
        for widget in self.camera_frame.winfo_children():
            widget.destroy()
        self.setup_camera_page()  # يعيد واجهة الكاميرا الأصلية
        self.show_frame(self.camera_frame)
        self.start_camera()

    def update_cart_display(self):
        self.cart_list.delete(0, tk.END)
        total = 0
        for item in self.cart:
            self.cart_list.insert(tk.END, f"{item['name']} - {item['price']} SAR")
            total += item['price']
        self.total_label.config(text=f"Total: {total:.2f} SAR")

    def delete_selected_item(self, event):
        selection = self.cart_list.curselection()
        if selection:
            index = selection[0]
            del self.cart[index]
            self.update_cart_display()

    def process_manual_entry(self, event):
        barcode = self.manual_entry.get().strip()
        if not barcode:
            return

        try:
            product_match = self.products[self.products["barcode"] == int(barcode)]
            if not product_match.empty:
                product = product_match.iloc[0].to_dict()
                self.cart.append(product)
                self.update_cart_display()
                self.manual_entry.delete(0, tk.END)
                # إظهار رسالة مؤقتة بدلاً من الانتقال لصفحة الرسائل
                self.show_temp_message(f"Added {product['name']} To the cart")
            else:
                self.manual_entry.delete(0, tk.END)
                self.show_frame(self.manual_error_frame)
        except ValueError:
            self.manual_entry.delete(0, tk.END)
            self.show_temp_message("Wrong Parcode!!")

    def show_temp_message(self, msg):
        # حفظ النص الأصلي إذا كان هناك رسالة سابقة
        if hasattr(self, 'temp_msg_label'):
            self.temp_msg_label.destroy()

        # إنشاء تسمية للرسالة المؤقتة
        self.temp_msg_label = tk.Label(self.cart_frame,
                                       text=msg,
                                       font=("Segoe UI", 12),
                                       bg="black",
                                       fg="green")
        self.temp_msg_label.pack(pady=5)

        # إزالة الرسالة بعد 3 ثواني
        self.root.after(3000, lambda: self.temp_msg_label.destroy() if hasattr(self, 'temp_msg_label') else None)

    def clear_cart(self):
        self.cart = []
        self.update_cart_display()
        self.show_message("تم تفريغ السلة بنجاح")

    def generate_qr(self):
        if not self.cart:
            self.show_message("السلة فارغة!")
            return

        barcodes = [str(item['barcode']) for item in self.cart]
        data = "\n".join(barcodes)

        qr = qrcode.make(data)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        qr.save(temp_file.name)

        img = Image.open(temp_file.name)
        img = img.resize((300, 300))
        imgtk = ImageTk.PhotoImage(image=img)

        def _update_qr():
            self.qr_label.imgtk = imgtk
            self.qr_label.config(image=imgtk)
            self.show_frame(self.qr_frame)

        self.queue.put(_update_qr)


if __name__ == "__main__":
    root = tk.Tk()
    app = POSApp(root)
    root.mainloop()
