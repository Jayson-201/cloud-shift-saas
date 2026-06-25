import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# 初始化 OpenAI (需在 Render 環境變數中設定 OPENAI_API_KEY)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 模擬目前的員工資料庫
employee_db = ["小王", "小李", "小張", "小陳", "小林"]
# 儲存員工的註冊人臉 (Base64 格式)
face_db = {} 

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    # 將 face_db 傳到前端，用來判斷誰已經登錄過人臉
    return render_template("dashboard.html", employees=employee_db, registered_faces=list(face_db.keys()))

@app.route("/add_employee", methods=["POST"])
def add_employee():
    if len(employee_db) >= 5:
        return jsonify({"status": "upgrade_needed", "message": "您目前使用的是體驗版（限5人），升級標準版即可解鎖無上限功能！"})
    else:
        new_name = request.form.get("name")
        if new_name and new_name not in employee_db:
            employee_db.append(new_name)
        return jsonify({"status": "success", "message": "新增成功"})

@app.route("/delete_employee/<name>", methods=["POST"])
def delete_employee(name):
    if name in employee_db:
        employee_db.remove(name)
        if name in face_db:
            del face_db[name] # 同時刪除人臉資料
        return jsonify({"status": "success", "message": f"已成功將員工「{name}」刪除。"})
    return jsonify({"status": "error", "message": "找不到該員工。"})

# [新增] 後台登錄人臉 API
@app.route("/register_face", methods=["POST"])
def register_face():
    name = request.form.get("name")
    image_data = request.form.get("image")
    if not name or not image_data:
        return jsonify({"status": "error", "message": "資料不完整"})
    
    face_db[name] = image_data
    return jsonify({"status": "success", "message": f"✅ 已成功登錄 {name} 的人臉資料！"})

@app.route("/clockin")
def clockin_page():
    return render_template("clockin.html", employees=employee_db)

# [升級] 前台打卡 API (結合 OpenAI Vision 比對)
@app.route("/api/do_clockin", methods=["POST"])
def do_clockin():
    emp_name = request.form.get("name")
    lat = request.form.get("lat")
    lng = request.form.get("lng")
    current_image = request.form.get("image") # 打卡當下拍的照片

    if emp_name not in face_db:
        return jsonify({"status": "error", "message": f"❌ {emp_name} 尚未登錄人臉，請店長先至後台完成登錄。"})

    registered_image = face_db[emp_name] # 取出後台註冊的照片

    try:
        # 呼叫 OpenAI Vision API 進行人臉比對
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "你是一個人臉辨識系統。請嚴格比對這兩張圖片中的人臉。如果是同一個人，請只回答 'YES'；如果不是同一個人或沒有看到人臉，請只回答 'NO'。"},
                        {"type": "image_url", "image_url": {"url": registered_image}},
                        {"type": "image_url", "image_url": {"url": current_image}}
                    ]
                }
            ],
            max_tokens=10
        )
        result = response.choices[0].message.content.strip().upper()

        if "YES" in result:
            return jsonify({"status": "success", "message": f"✅ {emp_name} 人臉辨識成功！\n經緯度: {lat}, {lng}"})
        else:
            return jsonify({"status": "error", "message": f"🚨 辨識失敗！這不是 {emp_name} 的臉，拒絕打卡。"})

    except Exception as e:
        return jsonify({"status": "error", "message": "❌ AI 辨識發生錯誤，請確認 API 狀態。"})

@app.route("/generate_schedule", methods=["POST"])
def generate_schedule():
    prompt = request.form.get("prompt")
    # 將現有員工名單寫入提示詞，禁止 AI 瞎編
    employee_str = ", ".join(employee_db)
    system_prompt = f"""你是一個排班調度顧問。
    目前店內的合法員工清單為：{employee_str}。
    你在給予調度建議時，嚴格禁止提到清單以外的人名。
    如果需要調度，請只從這份名單中挑選可用的員工，並解釋原因。"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return jsonify({"schedule": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate_handover", methods=["POST"])
def generate_handover():
    prompt = request.form.get("prompt")
    system_prompt = "請將員工口語化的交接內容整理成專業日誌。標籤：「⚠️ 待辦事項」、「🔧 設備報修」、「📝 營運紀錄」。"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    )
    return jsonify({"handover_log": response.choices[0].message.content})

if __name__ == "__main__":
    app.run(debug=True)
