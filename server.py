from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import openai
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()
apikey = os.getenv('apikey')

app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "http://127.0.0.1:5501"}})

# OpenAI API 키 설정 (본인의 API 키로 교체하세요)
openai.api_key = apikey

# 전역 단기기억: 최대 3개 대화 쌍(최대 6 메시지)
short_term_memory = []
# 전역 영구기억 (서버 실행 중 유지)
long_term_memory = ""

def stream_response(user_input):
    global short_term_memory, long_term_memory

    # 프롬프트 구성: 시스템 메시지, 영구기억, 단기기억, 현재 사용자 메시지
    prompt_messages = [
        {"role": "system", "content": "너는 도움이 되는 챗봇이다. 대화 중 ₩원화 단위를 포함해 가격 정보를 안내할 때는 반드시 ₩원화 단위로 알려줘."}
    ]
    if long_term_memory:
        prompt_messages.append({"role": "system", "content": f"이전 영구 기억:\n{long_term_memory}"})
    for msg in short_term_memory:
        prompt_messages.append(msg)
    prompt_messages.append({"role": "user", "content": user_input})

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=prompt_messages,
        temperature=0.7,
        stream=True
    )
    full_answer = ""
    for chunk in response:
        if chunk['choices'][0]['delta'].get('content'):
            token = chunk['choices'][0]['delta']['content']
            full_answer += token
            yield token

    # 스트리밍이 끝난 후, 단기기억 및 영구기억 업데이트 (최근 3개 쌍 유지)
    short_term_memory.extend([
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": full_answer}
    ])
    while len(short_term_memory) > 6:
        short_term_memory.pop(0)

    # 영구기억에 추가 (이전 대화 모두 누적)
    long_term_memory += f"User: {user_input}\nAssistant: {full_answer}\n\n"

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get("message", "")
    if not user_input:
        return jsonify({"error": "메시지가 필요합니다."}), 400
    return Response(stream_response(user_input), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
