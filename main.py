import discord
from discord.ext import commands
import os
import asyncio
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

# 처리 중인 멤버 추적 (중복 방지)
processing_members = set()
# 최근 처리된 멤버 추적 (5분간 기록)
recent_processed = {}

@bot.event
async def on_ready():
    print(f'{bot.user}가 준비되었습니다!')
    print(f'봇이 {len(bot.guilds)}개의 서버에 연결되어 있습니다.')
    
    # 봇 상태 설정
    await bot.change_presence(
        activity=discord.Game(name="신입 환영하기"),
        status=discord.Status.online
    )
    
    # 처리 중인 멤버 목록 초기화
    processing_members.clear()
    recent_processed.clear()

@bot.event
async def on_member_join(member):
    """새로운 멤버가 서버에 입장했을 때 실행되는 함수"""
    guild = member.guild
    current_time = datetime.now()
    
    # 봇인 경우 무시
    if member.bot:
        return
    
    # 이미 처리 중인 멤버인지 확인
    member_key = f"{guild.id}-{member.id}"
    if member_key in processing_members:
        print(f"{member.display_name}님은 이미 처리 중입니다.")
        return
    
    # 최근 5분 내에 처리한 멤버인지 확인
    if member_key in recent_processed:
        time_diff = (current_time - recent_processed[member_key]).total_seconds()
        if time_diff < 300:  # 5분 = 300초
            print(f"{member.display_name}님은 최근에 이미 처리되었습니다.")
            return
    
    # 처리 중 목록에 추가
    processing_members.add(member_key)
    recent_processed[member_key] = current_time
    
    try:
        # 도라도라미 역할을 가진 멤버들 찾기
        doradori_role = discord.utils.get(guild.roles, name=DORADORI_ROLE_NAME)
        
        if not doradori_role:
            print(f"'{DORADORI_ROLE_NAME}' 역할을 찾을 수 없습니다.")
            return
        
        # 비공개 채널 생성 전에 이미 존재하는 채널 확인
        channel_name = f"환영-{member.display_name}-{datetime.now().strftime('%m%d')}"
        
        # 이미 같은 이름의 채널이 있는지 확인
        existing_channels = [ch for ch in guild.channels if ch.name == channel_name]
        if existing_channels:
            print(f"이미 {channel_name} 채널이 존재합니다: {len(existing_channels)}개")
            # 기존 채널이 있으면 그 채널에 환영 메시지만 추가
            existing_channel = existing_channels[0]
            await existing_channel.send(f"🔄 {member.mention}님이 다시 서버에 입장하셨습니다!")
            return
        
        # 같은 멤버를 위한 채널이 이미 있는지 확인 (날짜 상관없이)
        member_channels = [ch for ch in guild.channels if ch.name.startswith(f"환영-{member.display_name}-")]
        if member_channels:
            print(f"{member.display_name}님을 위한 채널이 이미 존재합니다: {member_channels[0].name}")
            # 기존 채널에 재입장 메시지 추가
            await member_channels[0].send(f"🔄 {member.mention}님이 다시 서버에 입장하셨습니다!")
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
        
        # 도라도라미 역할을 가진 각 멤버에게도 명시적으로 권한 부여
        for doradori_member in doradori_role.members:
            if not doradori_member.bot:  # 봇이 아닌 경우만
                overwrites[doradori_member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # 카테고리 찾기
        category = discord.utils.get(guild.categories, name="신입환영") 
        
        # 채널 생성 시도 (실패 시 재시도하지 않음)
        try:
            # 채널 생성 직전에 한 번 더 확인
            final_check = discord.utils.get(guild.channels, name=channel_name)
            if final_check:
                print(f"채널 생성 직전 확인: {channel_name} 채널이 이미 존재합니다.")
                return
                
            welcome_channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=category,
                topic=f"{member.mention}님을 위한 환영 채널입니다."
            )
            print(f"채널 생성 성공: {welcome_channel.name}")
            
            # 잠깐 대기 후 중복 채널 확인 및 제거
            await asyncio.sleep(1)
            duplicate_channels = [ch for ch in guild.channels if ch.name == channel_name and ch.id != welcome_channel.id]
            for dup_ch in duplicate_channels:
                print(f"중복 채널 감지, 삭제: {dup_ch.name}")
                try:
                    await dup_ch.delete()
                except:
                    pass
                    
        except discord.HTTPException as e:
            print(f"채널 생성 실패: {e}")
            return
        
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
        
        # 도라도라미들에게 알림 (역할로 태그)
        await welcome_channel.send(f"{doradori_role.mention} 새로운 멤버 {member.mention}님을 도와주세요! 😊")
        
        print(f"{member.display_name}님을 위한 환영 채널이 생성되었습니다: {welcome_channel.name}")
        
    except Exception as e:
        print(f"채널 생성 중 오류가 발생했습니다: {e}")
    finally:
        # 처리 완료 후 목록에서 제거
        processing_members.discard(member_key)

@bot.command(name='중복채널정리')
@commands.has_permissions(manage_channels=True)
async def cleanup_duplicate_channels(ctx):
    """중복된 환영 채널을 정리하는 명령어"""
    guild = ctx.guild
    welcome_channels = [ch for ch in guild.channels if ch.name.startswith('환영-')]
    
    # 같은 이름의 채널들을 그룹화
    channel_groups = {}
    for channel in welcome_channels:
        if channel.name in channel_groups:
            channel_groups[channel.name].append(channel)
        else:
            channel_groups[channel.name] = [channel]
    
    deleted_count = 0
    for name, channels in channel_groups.items():
        if len(channels) > 1:
            # 가장 오래된 채널 하나만 남기고 나머지 삭제
            channels.sort(key=lambda x: x.created_at)
            for channel in channels[1:]:  # 첫 번째를 제외하고 삭제
                try:
                    await channel.delete()
                    deleted_count += 1
                    print(f"중복 채널 삭제: {channel.name}")
                except:
                    pass
    
    await ctx.send(f"✅ 중복된 환영 채널 {deleted_count}개를 정리했습니다.")

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
