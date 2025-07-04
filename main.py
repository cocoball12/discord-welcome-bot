import discord
from discord.ext import commands
import os
import asyncio
from datetime import datetime, timedelta
import json

# 환경 변수에서 포트 가져오기 (Koyeb용)
PORT = os.environ.get('PORT', 8080)

# 봇 설정
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix='!', 
    intents=intents, 
    help_command=None
)

# 환경 변수 설정
TOKEN = os.getenv('DISCORD_TOKEN')
DORADORI_ROLE_NAME = "도라도라미"

# ... (기존 코드 유지) ...

# 봇 실행 부분 수정
if __name__ == "__main__":
    if TOKEN:
        try:
            # Koyeb에서 웹 서비스로 실행하기 위한 더미 HTTP 서버
            import threading
            from http.server import HTTPServer, SimpleHTTPRequestHandler
            
            def run_http_server():
                server = HTTPServer(('0.0.0.0', int(PORT)), SimpleHTTPRequestHandler)
                server.serve_forever()
            
            # HTTP 서버를 백그라운드에서 실행
            threading.Thread(target=run_http_server, daemon=True).start()
            
            # 봇 실행
            bot.run(TOKEN)
        except Exception as e:
            print(f"봇 실행 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("DISCORD_TOKEN 환경 변수를 설정해주세요!")
