from flask import Flask, render_template, request, jsonify
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)

# Render 环境修改：数据文件必须存储在 /tmp 目录
DATA_FILE = '/tmp/events.json'
# 从环境变量读取 DeepSeek API Key
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

def load_events():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_events(events):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/events', methods=['GET'])
def get_events():
    return jsonify(load_events())

@app.route('/api/add_event', methods=['POST'])
def add_event():
    data = request.json
    date_str = data.get('date') # YYYY-MM-DD
    event = {
        'title': data.get('title'),
        'priority': int(data.get('priority', 3)), # 1: High, 2: Med, 3: Low
        'id': datetime.now().timestamp()
    }
    
    events = load_events()
    if date_str not in events:
        events[date_str] = []
    events[date_str].append(event)
    save_events(events)
    return jsonify({'status': 'success', 'event': event})

@app.route('/api/ai_parse', methods=['POST'])
def ai_parse():
    user_input = request.json.get('text')
    today = datetime.now().strftime('%Y-%m-%d')
    
    prompt = f"""
    你是时间管理大师。请从用户的输入中提取任务信息，并以 JSON 格式返回。
    如果用户没提到日期，默认使用今天 ({today})。
    优先级 mapping: 
    - 紧急/重要/必须/今天内完成 -> 1
    - 应该/中等/普通 -> 2
    - 其他/有空再做/低优先级 -> 3
    JSON 字段: "title" (提取出的简洁标题), "date" (YYYY-MM-DD 格式), "priority" (1, 2, 或 3)。
    不要解释，只返回 JSON。
    输入: "{user_input}"
    """
    
    try:
        response = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {"role": "system", "content": "You are a helpful assistant that extracts task data into JSON."},
                    {'role': 'user', 'content': prompt}
                ],
                'response_format': {'type': 'json_object'}
            },
            timeout=10
        )
        result = response.json()
        content = result['choices'][0]['message']['content']
        return jsonify(json.loads(content))
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_event', methods=['POST'])
def delete_event():
    data = request.json
    date_str = data.get('date')
    event_id = data.get('id')
    
    events = load_events()
    if date_str in events:
        events[date_str] = [e for e in events[date_str] if e.get('id') != event_id]
        if not events[date_str]:
            del events[date_str]
        save_events(events)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    # Render 通过环境变量 PORT 提供端口号
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
