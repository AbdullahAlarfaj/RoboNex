from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/execute', methods=['POST'])
def handle_command():
    data = request.json  # استقبال البيانات القادمة من الجهاز 1
    command = data.get("command")
    value = data.get("value")
    
    print(f"تم استقبال أمر: {command} مع قيمة: {value}")
    
    # --- ابدأ عملية المعالجة هنا ---
    result = f"تمت معالجة {command} بنجاح، النتيجة هي {value * 2}" 
    # ----------------------------
    
    return jsonify({"status": "success", "result": result})

if __name__ == '__main__':
    # اترك host='0.0.0.0' لكي يسمح بالاتصال من أي جهاز في الشبكة
    app.run(host='0.0.0.0', port=5000)
