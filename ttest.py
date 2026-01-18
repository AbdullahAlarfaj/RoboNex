from flask import Flask, request, jsonify

app = Flask(__name__)

# --- الدوال الخاصة بك ---
def turn_on_led():
    return "تم تشغيل الإضاءة (LED ON)"

def start_motor():
    return "تم تشغيل المحرك (Motor Started)"

def get_sensor_data():
    return {"temperature": 25, "humidity": 60}

# --- قاموس لربط النصوص بالدوال ---
functions_map = {
    "led_on": turn_on_led,
    "motor_on": start_motor,
    "get_data": get_sensor_data
}

@app.route('/call_func', methods=['POST'])
def handle_call():
    data = request.json
    func_name = data.get("function") # استخراج اسم الدالة المطلوب
    
    if func_name in functions_map:
        # تنفيذ الدالة المخزنة في القاموس
        result = functions_map[func_name]() 
        return jsonify({"status": "executed", "output": result})
    else:
        return jsonify({"status": "error", "message": "الدالة غير موجودة"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
