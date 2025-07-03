import discord
from discord.ext import commands
import os
from datetime import datetime

# 봇 설정 - 음성 기능 비활성화
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# 음성 기능을 사용하지 않도록 설정
bot = commands.Bot(
    command_prefix='!', 
    intents=intents, 
    help_command=None
)

# 환경 변수 설정
TOKEN = os.getenv('DISCORD_TOKEN')
DORADORI_ROLE_NAME = "도라도라미"

@bot.event
async def on_ready():
    print(f'{bot.user}가 준비되었습니다!')
    print(f'봇이 {len(bot.guilds)}개의 서버에 연결되어 있습니다.')
    
    # 봇 상태 설정
    await bot.change_presence(
        activity=discord.Game(name="신입 환영하기"),
        status=discord.Status.online
    )

@bot.event
async def on_member_join(member):
    """새로운 멤버가 서버에 입장했을 때 실행되는 함수"""
    guild = member.guild
    
    try:
        # 도라도라미 역할을 가진 멤버들 찾기
        doradori_role = discord.utils.get(guild.roles, name=DORADORI_ROLE_NAME)
        
        if not doradori_role:
            print(f"'{DORADORI_ROLE_NAME}' 역할을 찾을 수 없습니다.")
            return
        
        # 도라도라미 역할을 가진 멤버들 중 온라인인 사람 찾기
        online_doradori_members = [
            m for m in doradori_role.members 
            if m.status != discord.Status.offline and not m.bot
        ]
        
        if not online_doradori_members:
            # 온라인인 사람이 없으면 모든 도라도라미 멤버를 대상으로
            online_doradori_members = [m for m in doradori_role.members if not m.bot]
        
        if not online_doradori_members:
            print("도라도라미 역할을 가진 멤버가 없습니다.")
            return
        
        # 비공개 채널 생성
        channel_name = f"환영-{member.display_name}-{datetime.now().strftime('%m%d')}"
        
        # 채널 권한 설정
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            doradori_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),  # 도라도라미 역할 전체에게 권한 부여
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # 카테고리 찾기
        category = discord.utils.get(guild.categories, name="신입환영") 
        
        # 채널 생성
        welcome_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            topic=f"{member.mention}님을 위한 환영 채널입니다."
        )
        
        # 환영 메시지 전송
        embed = discord.Embed(
            title="🎉 새로운 멤버를 환영합니다!",
            description=f"{member.mention}님, 서버에 오신 것을 환영합니다!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👋 안내",
            value=f"{doradori_role.mention} 역할을 가진 분들이 도움을 드릴 예정입니다.\n궁금한 것이 있으시면 언제든 물어보세요!",
            inline=False
        )
        
        embed.add_field(
            name="📋 다음 단계",
            value="• 서버 규칙을 확인해주세요\n• 자기소개를 해주세요\n• 궁금한 점을 자유롭게 질문하세요",
            inline=False
        )
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        if guild.icon:
            embed.set_footer(text="채널 생성됨", icon_url=guild.icon.url)
        
        await welcome_channel.send(embed=embed)
        
        # 도라도라미들에게 알림
        doradori_mentions = " ".join([m.mention for m in online_doradori_members])
        await welcome_channel.send(f"{doradori_mentions} 새로운 멤버 {member.mention}님을 도와주세요! 😊")
        
        print(f"{member.display_name}님을 위한 환영 채널이 생성되었습니다: {welcome_channel.name}")
        
    except Exception as e:
        print(f"채널 생성 중 오류가 발생했습니다: {e}")

@bot.command(name='채널삭제')
@commands.has_permissions(manage_channels=True)
async def delete_welcome_channel(ctx, channel_id: int = None):
    """환영 채널을 삭제하는 명령어"""
    if channel_id:
        channel = bot.get_channel(channel_id)
    else:
        channel = ctx.channel
    
    if channel and channel.name.startswith('환영-'):
        await channel.delete()
        if channel != ctx.channel:
            await ctx.send(f"채널 '{channel.name}'이 삭제되었습니다.")
    else:
        await ctx.send("환영 채널만 삭제할 수 있습니다.")

@bot.command(name='도라도라미설정')
@commands.has_permissions(administrator=True)
async def set_doradori_role(ctx, role_name: str):
    """도라도라미 역할 이름을 설정하는 명령어"""
    global DORADORI_ROLE_NAME
    DORADORI_ROLE_NAME = role_name
    await ctx.send(f"도라도라미 역할이 '{role_name}'으로 설정되었습니다.")

@bot.command(name='상태확인')
async def check_status(ctx):
    """봇 상태를 확인하는 명령어"""
    guild = ctx.guild
    doradori_role = discord.utils.get(guild.roles, name=DORADORI_ROLE_NAME)
    
    embed = discord.Embed(title="봇 상태 확인", color=0x0099ff)
    embed.add_field(name="서버", value=guild.name, inline=True)
    embed.add_field(name="총 멤버 수", value=len(guild.members), inline=True)
    
    if doradori_role:
        doradori_count = len([m for m in doradori_role.members if not m.bot])
        embed.add_field(name=f"{DORADORI_ROLE_NAME} 멤버 수", value=doradori_count, inline=True)
    else:
        embed.add_field(name="도라도라미 역할", value="역할을 찾을 수 없음", inline=True)
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 이 명령어를 사용할 권한이 없습니다.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"오류 발생: {error}")

# 봇 실행
if __name__ == "__main__":
    if TOKEN:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"봇 실행 중 오류 발생: {e}")
            print("Python 3.13 호환성 문제일 수 있습니다. Python 3.11 또는 3.12 사용을 권장합니다.")
    else:
        print("DISCORD_TOKEN 환경 변수를 설정해주세요!")
