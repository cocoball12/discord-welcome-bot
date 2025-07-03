import discord
from discord.ext import commands
import os
import asyncio
from datetime import datetime, timedelta
import json

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
# 48시간 후 확인 대기 중인 멤버들 (메모리 저장)
pending_checks = {}

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
    
    # 48시간 후 확인 작업 시작
    bot.loop.create_task(check_adaptation_loop())

async def check_adaptation_loop():
    """48시간 후 적응 확인을 위한 백그라운드 작업"""
    while True:
        try:
            current_time = datetime.now()
            to_remove = []
            
            for key, check_data in pending_checks.items():
                if current_time >= check_data['check_time']:
                    guild_id, member_id = key.split('-')
                    guild = bot.get_guild(int(guild_id))
                    member = guild.get_member(int(member_id)) if guild else None
                    
                    if guild and member:
                        await send_adaptation_check(guild, member, check_data['channel_id'])
                    
                    to_remove.append(key)
            
            # 처리된 항목들 제거
            for key in to_remove:
                del pending_checks[key]
            
        except Exception as e:
            print(f"적응 확인 루프 오류: {e}")
        
        # 1시간마다 확인
        await asyncio.sleep(3600)

async def send_adaptation_check(guild, member, channel_id):
    """48시간 후 적응 확인 메시지 전송"""
    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🌟 서버 적응 안내",
            description=f"{member.mention}님, 서버에 잘 적응하고 계신가요?",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 적응 확인",
            value="""서버 초기 목록 넣었으니 잘 따라해주셔서 감사합니다!
이제 조금 넣었으니 있다면, 급할 안천에서 궁금한 것들이 있으시면 물어보세요!
          
이미 적응하셨다면 → [서버 버튼을 눌러 적응하면 → (주제 버튼을 눌러주세요]

[정착하는 농도의 자유로운 임의 설정해주세요!
[서버에 누구신 들으시 나중에 다시 들어온 방법하신 건]
          
🟢 완료하셨 → 무엇이자 안내 →  (완료도라미를 통해 증세로]
          
🟢 6일 내에 이후 응답이 없으면 자동으로 강퇴됩니다.
도라도라미가 없싶어 적응을 완료하고!""",
            inline=False
        )
        
        # 버튼 생성
        view = AdaptationView(member, channel)
        await channel.send(embed=embed, view=view)
        
        print(f"{member.display_name}님에게 48시간 후 적응 확인 메시지를 보냈습니다.")
        
    except Exception as e:
        print(f"적응 확인 메시지 전송 오류: {e}")

class AdaptationView(discord.ui.View):
    def __init__(self, member, channel):
        super().__init__(timeout=518400)  # 6일 = 518400초
        self.member = member
        self.channel = channel
    
    @discord.ui.button(label='삭제', style=discord.ButtonStyle.red, emoji='🗑️')
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.member.id:
            await interaction.response.send_message("❌ 채널이 삭제됩니다.", ephemeral=True)
            await asyncio.sleep(2)
            await self.channel.delete()
        else:
            await interaction.response.send_message("❌ 본인만 삭제할 수 있습니다.", ephemeral=True)
    
    @discord.ui.button(label='관리자 검토', style=discord.ButtonStyle.green, emoji='✅')
    async def admin_review_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.member.id:
            doradori_role = discord.utils.get(interaction.guild.roles, name=DORADORI_ROLE_NAME)
            if doradori_role:
                await interaction.response.send_message(f"✅ {doradori_role.mention} 관리자 검토를 요청했습니다!")
            else:
                await interaction.response.send_message("✅ 관리자 검토를 요청했습니다!")
        else:
            await interaction.response.send_message("❌ 본인만 관리자 검토를 요청할 수 있습니다.", ephemeral=True)

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
        
        # 채널 권한 설정 - 완전한 비공개 채널
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            doradori_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # 도라도라미 역할을 가진 각 멤버에게도 명시적으로 권한 부여
        for doradori_member in doradori_role.members:
            if not doradori_member.bot:  # 봇이 아닌 경우만
                overwrites[doradori_member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # 다른 새로운 멤버들이 이 채널을 보지 못하도록 설정
        # 현재 서버의 모든 멤버 중 도라도라미 역할이 없는 멤버들은 접근 불가
        for guild_member in guild.members:
            if (not guild_member.bot and 
                guild_member.id != member.id and 
                doradori_role not in guild_member.roles):
                overwrites[guild_member] = discord.PermissionOverwrite(read_messages=False, send_messages=False)
        
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
        
        # 첫 번째 환영 메시지 (이미지와 같은 내용)
        initial_embed = discord.Embed(
            title="🎉 도라도라미와 축하축하",
            description=f"안녕하세요 저희 대화방 가족입니다! 48시간 내로 적응 설명 짧은 메시지를 도착 예정입니다.",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        initial_embed.add_field(
            name="📋 안내",
            value="서버 규칙을 확인하시고 관리자 이용해주세요!",
            inline=False
        )
        
        if member.avatar:
            initial_embed.set_thumbnail(url=member.avatar.url)
        
        # 첫 번째 메시지의 버튼
        class InitialView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)
            
            @discord.ui.button(label='삭제', style=discord.ButtonStyle.red, emoji='🗑️')
            async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id == member.id:
                    await interaction.response.send_message("❌ 채널이 삭제됩니다.", ephemeral=True)
                    await asyncio.sleep(2)
                    await welcome_channel.delete()
                else:
                    await interaction.response.send_message("❌ 본인만 삭제할 수 있습니다.", ephemeral=True)
            
            @discord.ui.button(label='관리자 검토', style=discord.ButtonStyle.green, emoji='✅')
            async def admin_review_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id == member.id:
                    await interaction.response.send_message(f"✅ {doradori_role.mention} 관리자 검토를 요청했습니다!")
                else:
                    await interaction.response.send_message("❌ 본인만 관리자 검토를 요청할 수 있습니다.", ephemeral=True)
        
        initial_view = InitialView()
        await welcome_channel.send(embed=initial_embed, view=initial_view)
        
        # 추가 안내 메시지 - 도라도라미 역할 멘션으로 수정
        additional_info = f"""심심해서 들어와서 말 없이 나가는 건 상관없지만
담는 한국인 웹진 간편하게 장난 쳐서 가져 그건 서
개 받아내는 서버 이라구
{doradori_role.mention}"""
        
        await welcome_channel.send(additional_info)
        
        # 48시간 후 적응 확인 스케줄 등록
        check_time = current_time + timedelta(hours=48)
        pending_checks[member_key] = {
            'check_time': check_time,
            'channel_id': welcome_channel.id,
            'member_id': member.id,
            'guild_id': guild.id
        }
        
        print(f"{member.display_name}님을 위한 환영 채널이 생성되었습니다: {welcome_channel.name}")
        print(f"48시간 후 적응 확인 예정: {check_time}")
        
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

@bot.command(name='적응확인테스트')
@commands.has_permissions(manage_channels=True)
async def test_adaptation_check(ctx, member: discord.Member):
    """48시간 적응 확인 메시지를 즉시 테스트하는 명령어"""
    await send_adaptation_check(ctx.guild, member, ctx.channel.id)
    await ctx.send(f"✅ {member.mention}님에 대한 적응 확인 메시지를 테스트로 전송했습니다.")

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
    embed.add_field(name="대기 중인 적응 확인", value=len(pending_checks), inline=True)
    
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
