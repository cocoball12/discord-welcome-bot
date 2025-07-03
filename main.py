import discord
from discord.ext import commands
import os
import asyncio
from datetime import datetime, timedelta
import json

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

# 처리 중인 멤버 추적 (중복 방지)
processing_members = set()
# 최근 처리된 멤버 추적 (5분간 기록)
recent_processed = {}
# 48시간 후 확인 대기 중인 멤버들
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
            value="""서버에 잘 적응하고 계신가요?
궁금한 것들이 있으시면 언제든 물어보세요!
          
적응을 완료하셨다면 아래 버튼을 눌러주세요.
          
🟢 6일 내에 응답이 없으면 자동으로 강퇴됩니다.""",
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
            try:
                await self.channel.delete()
            except:
                pass
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

class InitialView(discord.ui.View):
    def __init__(self, member, channel, doradori_role):
        super().__init__(timeout=300)
        self.member = member
        self.channel = channel
        self.doradori_role = doradori_role
    
    @discord.ui.button(label='삭제', style=discord.ButtonStyle.red, emoji='🗑️')
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.member.id:
            await interaction.response.send_message("❌ 채널이 삭제됩니다.", ephemeral=True)
            await asyncio.sleep(2)
            try:
                await self.channel.delete()
            except:
                pass
        else:
            await interaction.response.send_message("❌ 본인만 삭제할 수 있습니다.", ephemeral=True)
    
    @discord.ui.button(label='관리자 검토', style=discord.ButtonStyle.green, emoji='✅')
    async def admin_review_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.member.id:
            if self.doradori_role:
                await interaction.response.send_message(f"✅ {self.doradori_role.mention} 관리자 검토를 요청했습니다!")
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
    
    # 잠시 대기 (동시 처리 방지)
    await asyncio.sleep(0.5)
    
    try:
        # 도라도라미 역할을 가진 멤버들 찾기
        doradori_role = discord.utils.get(guild.roles, name=DORADORI_ROLE_NAME)
        
        if not doradori_role:
            print(f"'{DORADORI_ROLE_NAME}' 역할을 찾을 수 없습니다.")
            processing_members.discard(member_key)
            return
        
        # 비공개 채널 생성 전에 이미 존재하는 채널 확인
        channel_name = f"환영-{member.display_name}-{datetime.now().strftime('%m%d')}"
        
        # 같은 멤버를 위한 채널이 이미 있는지 확인 (더 강력한 체크)
        existing_channels = []
        for ch in guild.channels:
            if (ch.name.startswith(f"환영-{member.display_name}-") or 
                ch.name == f"환영-{member.display_name}-{datetime.now().strftime('%m%d')}"):
                existing_channels.append(ch)
        
        if existing_channels:
            print(f"{member.display_name}님을 위한 채널이 이미 존재합니다: {existing_channels[0].name}")
            await existing_channels[0].send(f"🔄 {member.mention}님이 다시 서버에 입장하셨습니다!")
            processing_members.discard(member_key)
            return
        
        # 최종 채널 이름 확정
        channel_name = f"환영-{member.display_name}-{datetime.now().strftime('%m%d')}"
        
        # 채널 생성 직전 한 번 더 확인
        final_check = discord.utils.get(guild.channels, name=channel_name)
        if final_check:
            print(f"최종 확인: {channel_name} 채널이 이미 존재합니다.")
            await final_check.send(f"🔄 {member.mention}님이 다시 서버에 입장하셨습니다!")
            processing_members.discard(member_key)
            return
        
        # 도라도라미 역할을 가진 멤버들 중 온라인인 사람 찾기
        online_doradori_members = [
            m for m in doradori_role.members 
            if m.status != discord.Status.offline and not m.bot
        ]
        
        if not online_doradori_members:
            online_doradori_members = [m for m in doradori_role.members if not m.bot]
        
        if not online_doradori_members:
            print("도라도라미 역할을 가진 멤버가 없습니다.")
            processing_members.discard(member_key)
            return
        
        # 채널 권한 설정
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            doradori_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # 카테고리 찾기
        category = discord.utils.get(guild.categories, name="신입환영")
        
        # 채널 생성
        try:
            welcome_channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=category,
                topic=f"{member.mention}님을 위한 환영 채널입니다."
            )
            print(f"채널 생성 성공: {welcome_channel.name}")
            
            # 채널 생성 직후 중복 확인 및 제거
            await asyncio.sleep(1)
            all_channels = await guild.fetch_channels()
            duplicate_channels = [ch for ch in all_channels if ch.name == channel_name and ch.id != welcome_channel.id]
            
            if duplicate_channels:
                print(f"중복 채널 {len(duplicate_channels)}개 감지, 삭제 진행...")
                for dup_ch in duplicate_channels:
                    try:
                        await dup_ch.delete()
                        print(f"중복 채널 삭제 완료: {dup_ch.name}")
                    except Exception as e:
                        print(f"중복 채널 삭제 실패: {e}")
                    
        except discord.HTTPException as e:
            print(f"채널 생성 실패: {e}")
            # 채널 생성 실패 시 같은 이름의 채널이 이미 있는지 확인
            existing = discord.utils.get(guild.channels, name=channel_name)
            if existing:
                print(f"생성 실패했지만 채널이 이미 존재: {existing.name}")
                await existing.send(f"🔄 {member.mention}님이 서버에 입장하셨습니다!")
            processing_members.discard(member_key)
            return
        
        # 첫 번째 환영 메시지
        initial_embed = discord.Embed(
            title="🎉 도라도라미와 축하축하",
            description=f"안녕하세요! 저희 서버에 오신 것을 환영합니다! 48시간 내로 적응 안내 메시지를 보내드릴 예정입니다.",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        initial_embed.add_field(
            name="📋 안내",
            value="서버 규칙을 확인하시고 편안하게 이용해주세요!",
            inline=False
        )
        
        if member.avatar:
            initial_embed.set_thumbnail(url=member.avatar.url)
        
        initial_view = InitialView(member, welcome_channel, doradori_role)
        await welcome_channel.send(embed=initial_embed, view=initial_view)
        
        # 추가 안내 메시지
        additional_info = f"""심심해서 들어온거면 관리진들이 불러줄떄 빨리 답장하고 부르면 음챗방 오셈
답도 안하고 활동 안할거면 걍 딴 서버 가라
그런 새끼 받아주는 서버 아님
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
        import traceback
        traceback.print_exc()
    finally:
        # 처리 완료 후 목록에서 제거
        processing_members.discard(member_key)

@bot.command(name='중복채널정리')
@commands.has_permissions(manage_channels=True)
async def cleanup_duplicate_channels(ctx):
    """중복된 환영 채널을 정리하는 명령어"""
    guild = ctx.guild
    welcome_channels = [ch for ch in guild.channels if ch.name.startswith('환영-')]
    
    channel_groups = {}
    for channel in welcome_channels:
        if channel.name in channel_groups:
            channel_groups[channel.name].append(channel)
        else:
            channel_groups[channel.name] = [channel]
    
    deleted_count = 0
    for name, channels in channel_groups.items():
        if len(channels) > 1:
            channels.sort(key=lambda x: x.created_at)
            for channel in channels[1:]:
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
        try:
            await channel.delete()
            if channel != ctx.channel:
                await ctx.send(f"채널 '{channel.name}'이 삭제되었습니다.")
        except:
            await ctx.send("채널 삭제 중 오류가 발생했습니다.")
    else:
        await ctx.send("환영 채널만 삭제할 수 있습니다.")

@bot.command(name='테스트환영')
@commands.has_permissions(manage_channels=True)
async def test_welcome(ctx, member: discord.Member):
    """환영 채널 생성을 테스트하는 명령어"""
    try:
        await on_member_join(member)
        await ctx.send(f"✅ {member.mention}님에 대한 환영 채널 생성을 테스트했습니다.")
    except Exception as e:
        await ctx.send(f"❌ 테스트 중 오류 발생: {e}")

@bot.command(name='권한확인')
@commands.has_permissions(manage_channels=True)
async def check_permissions(ctx):
    """봇의 권한을 확인하는 명령어"""
    guild = ctx.guild
    bot_member = guild.get_member(bot.user.id)
    doradori_role = discord.utils.get(guild.roles, name=DORADORI_ROLE_NAME)
    category = discord.utils.get(guild.categories, name="신입환영")
    
    embed = discord.Embed(title="권한 및 설정 확인", color=0x0099ff)
    embed.add_field(name="봇 권한", value=f"채널 관리: {bot_member.guild_permissions.manage_channels}", inline=True)
    embed.add_field(name="도라도라미 역할", value=f"존재: {doradori_role is not None}", inline=True)
    embed.add_field(name="신입환영 카테고리", value=f"존재: {category is not None}", inline=True)
    
    if doradori_role:
        embed.add_field(name="도라도라미 멤버 수", value=len(doradori_role.members), inline=True)
    
    await ctx.send(embed=embed)

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
async def on_member_remove(member):
    """멤버가 서버에서 나갔을 때 해당 환영 채널 삭제"""
    guild = member.guild
    
    # 봇인 경우 무시
    if member.bot:
        return
    
    try:
        # 해당 멤버의 환영 채널 찾기
        welcome_channels = [
            ch for ch in guild.channels 
            if ch.name.startswith(f"환영-{member.display_name}-")
        ]
        
        # 환영 채널이 있으면 삭제
        for channel in welcome_channels:
            try:
                await channel.delete()
                print(f"{member.display_name}님이 나가서 환영 채널 '{channel.name}'을 삭제했습니다.")
            except Exception as e:
                print(f"환영 채널 삭제 중 오류: {e}")
        
        # 48시간 후 확인 대기 목록에서도 제거
        member_key = f"{guild.id}-{member.id}"
        if member_key in pending_checks:
            del pending_checks[member_key]
            print(f"{member.display_name}님의 48시간 후 확인 일정을 취소했습니다.")
        
        # 처리 중 목록에서도 제거
        processing_members.discard(member_key)
        
        # 최근 처리 목록에서도 제거
        if member_key in recent_processed:
            del recent_processed[member_key]
            
    except Exception as e:
        print(f"멤버 퇴장 처리 중 오류: {e}")
        import traceback
        traceback.print_exc()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 이 명령어를 사용할 권한이 없습니다.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"오류 발생: {error}")
        import traceback
        traceback.print_exc()

# 봇 실행
if __name__ == "__main__":
    if TOKEN:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"봇 실행 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("DISCORD_TOKEN 환경 변수를 설정해주세요!")
