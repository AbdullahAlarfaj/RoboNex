from supabase import create_client
import config
from logger_config import logger

# ============================= قسم ادارة السلة والمينيو ====================================

class DatabaseManager:
    def __init__(self):
        self.supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        self.menu_db = {}
        self.menu_string = ""
        self.shopping_cart = {}

        # عند التشغيل: جلب المنيو والتأكد من وجود فاتورة مفتوحة
        self.fetch_menu()
        self.ensure_open_invoice()
        self.fetch_remote_cart()

    def fetch_menu(self):
        try:
            response = self.supabase.table("MENU_DB").select("*").execute()
            new_menu = {}
            if response.data:
                for item in response.data:
                    new_menu[str(item['id'])] = {
                        "name": item['name'],
                        "price": float(item['price']) if item['price'] else 0.0,
                        "stock": item['stock'],
                        "barcode": str(item['barcode']),
                        "type": item['type'],
                        "image": item.get('image_url')
                    }
            self.menu_db = new_menu
            self.menu_string = "\n".join(
                [f"- {key}: {val['name']} ({val['price']} ريال)"
                 for key, val in self.menu_db.items() if val['stock']]
            )
        except Exception as e:
            logger.error(f"⚠️ Menu Sync Error: {e}")

    def ensure_open_invoice(self):
        """التأكد عند التشغيل أن هناك فاتورة مفتوحة لاستقبال الطلبات"""
        try:
            # نجلب آخر فاتورة
            res = self.supabase.table("invoice").select("*").order("id", desc=True).limit(1).execute()
            if res.data:
                last_inv = res.data[0]
                # إذا كانت آخر فاتورة مدفوعة (مغلقة)، نفتح واحدة جديدة
                if last_inv.get('paid') is True:
                    self.supabase.table("invoice").insert({"total_invoice": 0.0, "paid": False}).execute()
                    logger.info("🆕 تم إنشاء فاتورة افتتاحية جديدة")
            else:
                # لا توجد فواتير أبداً، ننشئ الأولى
                self.supabase.table("invoice").insert({"total_invoice": 0.0, "paid": False}).execute()
        except:
            pass

    # ==============================================================================
    # 🌟 الدالة الجديدة: تحديث إجمالي الفاتورة المفتوحة لحظياً
    # ==============================================================================
    def update_live_invoice_total(self, invoice_id=None):
        """تحسب إجمالي السلة مع مراعاة نسبة الخصم المسجلة في الفاتورة"""
        try:
            # 1. تحديد رقم الفاتورة
            if invoice_id is None:
                res = self.supabase.table("invoice").select("id").order("id", desc=True).limit(1).execute()
                if res.data:
                    invoice_id = res.data[0]['id']
                else:
                    return

            # 2. حساب المجموع الفرعي (Subtotal) من السلة
            response_cart = self.supabase.table('cart').select('total_price').eq('invoice_num', invoice_id).execute()
            subtotal = 0.0
            if response_cart.data:
                subtotal = sum([float(item['total_price']) for item in response_cart.data])

            # 3. جلب نسبة الخصم الحالية من الفاتورة (للحفاظ عليها)
            response_inv = self.supabase.table('invoice').select('discount_percentage').eq('id', invoice_id).execute()
            discount_percent = 0.0
            if response_inv.data and response_inv.data[0].get('discount_percentage'):
                discount_percent = float(response_inv.data[0]['discount_percentage'])

            # 4. إعادة حساب القيم بناءً على المجموع الجديد
            discount_amount = subtotal * (discount_percent / 100)
            grand_total = max(0, subtotal - discount_amount)

            # 5. تحديث كافة التفاصيل في الفاتورة
            self.supabase.table("invoice").update({
                "subtotal": subtotal,  # المبلغ قبل الخصم
                "discount_amount": discount_amount,  # قيمة الخصم الجديدة
                "total_invoice": grand_total  # الإجمالي النهائي الصافي
            }).eq("id", invoice_id).execute()

            # logger.debug(f"💰 Invoice #{invoice_id} Synced: Sub={subtotal}, Disc={discount_percent}%, Total={grand_total}")

        except Exception as e:
            logger.error(f"⚠️ Failed to update live invoice total: {e}")

    def sync_cart_item(self, product_identifier, quantity_change, is_absolute=False):
        """
        is_absolute=False -> يضيف على الموجود (مثال: 3 + 1 = 4) [للأزرار وأوامر الإضافة]
        is_absolute=True  -> يحدد الرقم بالضبط (مثال: 3 -> 5) [لأوامر التعديل]
        """
        try:
            target_product = None
            raw_key = str(product_identifier).strip()

            # 1. البحث في القائمة المحلية
            if hasattr(self, 'menu_db') and self.menu_db:
                if raw_key in self.menu_db:
                    target_product = self.menu_db[raw_key]
                    target_product['id'] = raw_key

                if not target_product:
                    for pid, p_data in self.menu_db.items():
                        p_name = str(p_data.get('name', '')).strip().lower()
                        input_name = raw_key.lower()
                        if input_name in p_name or input_name == str(p_data.get('barcode', '')):
                            target_product = p_data
                            target_product['id'] = pid
                            break

            if not target_product:
                logger.warning(f"Product not found: {product_identifier}")
                return False

            # 2. تحديد الفاتورة
            inv_res = self.supabase.table('invoice').select("*").eq('paid', False).order("id", desc=True).limit(
                1).execute()
            invoice_id = inv_res.data[0]['id'] if inv_res.data else \
            self.supabase.table('invoice').insert({'total_invoice': 0, 'paid': False}).execute().data[0]['id']

            # 3. البحث عن المنتج في السلة
            existing_item = None
            check_id = self.supabase.table('cart').select("*").eq('invoice_num', invoice_id).eq('product_id',
                                                                                                target_product[
                                                                                                    'id']).execute()
            if check_id.data:
                existing_item = check_id.data[0]

            if not existing_item:
                check_name = self.supabase.table('cart').select("*").eq('invoice_num', invoice_id).eq('name',
                                                                                                      target_product[
                                                                                                          'name']).execute()
                if check_name.data:
                    existing_item = check_name.data[0]
                    self.supabase.table('cart').update({'product_id': target_product['id']}).eq('id', existing_item[
                        'id']).execute()

            # 4. التنفيذ (المنطق المفصول)
            if existing_item:
                # ✅ هنا يكمن السحر: نفصل المنطق حسب الطلب
                if is_absolute:
                    new_qty = quantity_change  # تثبيت الرقم كما هو (أمر Set)
                    logger.info(f"🔄 Setting Exact Quantity: {target_product['name']} -> {new_qty}")
                else:
                    new_qty = existing_item['quantity'] + quantity_change  # جمع تراكمي (أمر Add)
                    logger.info(
                        f"➕ Accumulating Quantity: {target_product['name']} ({existing_item['quantity']} + {quantity_change} = {new_qty})")

                if new_qty <= 0:
                    self.remove_cart_item(existing_item['id'])
                else:
                    new_total = new_qty * target_product['price']
                    self.supabase.table('cart').update({
                        'quantity': new_qty,
                        'total_price': new_total,
                        'product_id': target_product['id']
                    }).eq('id', existing_item['id']).execute()
            else:
                # إضافة جديدة
                if quantity_change > 0:
                    self.supabase.table('cart').insert({
                        'invoice_num': invoice_id,
                        'product_id': target_product['id'],
                        'name': target_product['name'],
                        'price': target_product['price'],
                        'quantity': quantity_change,
                        'total_price': target_product['price'] * quantity_change
                    }).execute()

            self.update_live_invoice_total(invoice_id)
            return True

        except Exception as e:
            logger.error(f"❌ Sync Cart Logic Error: {e}")
            return False

    def remove_cart_item(self, item_id):
        try:
            self.supabase.table("cart").delete().eq("product_id", item_id).execute()

            # حذف من المحلي
            if item_id in self.shopping_cart:
                del self.shopping_cart[item_id]

            logger.info(f"➖ Cart Item Removed: {item_id}")

            # 🔥 تحديث الفاتورة الحالية فوراً
            self.update_live_invoice_total()

        except Exception as e:
            logger.error(f"⚠️ Cart Remove Error: {e}")

    def fetch_remote_cart(self):
        """مزامنة ومراجعة الأسعار من الفلتر فلو"""
        try:
            response = self.supabase.table("cart").select("*").execute()
            new_cart = {}

            if response.data:
                for item in response.data:
                    pid = str(item['product_id'])
                    qty = int(item['quantity'])

                    if pid in self.menu_db and qty > 0:
                        unit_price = self.menu_db[pid]['price']
                        correct_total = unit_price * qty

                        # تصحيح السعر في جدول السلة لو كان خطأ
                        db_price = float(item['total_price']) if item['total_price'] else 0.0
                        if abs(correct_total - db_price) > 0.01:
                            self.supabase.table("cart").update({"total_price": correct_total}).eq("id",
                                                                                                  item['id']).execute()

                        new_cart[pid] = qty

            self.shopping_cart = new_cart

            # 🔥 تحديث الفاتورة الحالية بناءً على المزامنة
            self.update_live_invoice_total()

        except Exception as e:
            logger.error(f"⚠️ Remote Cart Fetch Error: {e}")

    def clear_cart(self):
        try:
            self.shopping_cart = {}
            self.supabase.table("cart").delete().gt("id", 0).execute()
            # نصفر الفاتورة الحالية أيضاً
            self.update_live_invoice_total()
            logger.info("🧹 Cart Cleared")
        except Exception as e:
            logger.error(f"Clear Cart Error: {e}")

    def get_cart_summary(self):
        return str(self.shopping_cart)

    def archive_current_order(self):
        """ترحيل الطلب وفتح فاتورة جديدة"""
        try:
            if not self.shopping_cart:
                return False

            grand_total = 0.0
            for pid, qty in self.shopping_cart.items():
                if pid in self.menu_db:
                    grand_total += self.menu_db[pid]['price'] * qty

            # 1. إغلاق الفاتورة الحالية
            # نجلب الفاتورة المفتوحة ونحدثها لتصبح مدفوعة وبالمبلغ النهائي
            res = self.supabase.table("invoice").select("id").order("id", desc=True).limit(1).execute()
            if not res.data: return False

            current_inv_id = res.data[0]['id']

            self.supabase.table("invoice").update({
                "total_invoice": grand_total,
                "paid": True
            }).eq("id", current_inv_id).execute()

            logger.info(f"✅ تم اعتماد وإغلاق الفاتورة رقم: {current_inv_id}")

            # 2. ترحيل المنتجات
            items_to_archive = []
            for pid, qty in self.shopping_cart.items():
                if pid in self.menu_db:
                    item_data = self.menu_db[pid]
                    items_to_archive.append({
                        "invoice_number": current_inv_id,
                        "product_id": str(pid),
                        "name": item_data['name'],
                        "quantity": int(qty),
                        "price": float(item_data['price']),
                        "total_price": float(item_data['price'] * qty)
                    })

            if items_to_archive:
                self.supabase.table("invoice_items").insert(items_to_archive).execute()

            # 3. تنظيف السلة
            self.clear_cart()

            # 4. فتح فاتورة جديدة للمستقبل
            response_next = self.supabase.table("invoice").insert({"total_invoice": 0.0, "paid": False}).execute()
            if response_next.data:
                logger.info(f"🆕 تم فتح فاتورة جديدة رقم {response_next.data[0]['id']}")

            return True

        except Exception as e:
            logger.error(f"Archiving Error: {e}")
            return False
