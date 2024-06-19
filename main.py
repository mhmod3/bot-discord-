import discord
from discord.ext import commands
import requests
from deep_translator import GoogleTranslator
import os

# إعداد النوايا (intents)
intents = discord.Intents.default()
intents.message_content = True  # تمكين الوصول إلى محتوى الرسائل

# إعداد البوت
bot = commands.Bot(command_prefix='!', intents=intents)

# مفتاح API لـ MyAnimeList
api_key = '98f7b234cab96ae1f7fd7c31ab3aa3eb'
headers = {'X-MAL-CLIENT-ID': api_key}

# معرّفات القنوات والمستخدم المسموح به
command_channel_id = 1252277316948725792  # استبدل YOUR_COMMAND_CHANNEL_ID بمعرّف قناة الأوامر الخاصة بك
embed_channel_id = 1252263507601260574  # استبدل YOUR_EMBED_CHANNEL_ID بمعرّف قناة الـembed الخاصة بك
allowed_user_id = 1242616897610973217  # استبدل YOUR_USER_ID بمعرّف المستخدم الخاص بك

# إعداد مترجم Google
translator = GoogleTranslator(source='en', target='ar')


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


@bot.command()
async def anime(ctx):
    if ctx.channel.id != command_channel_id:
        return
    if ctx.author.id != allowed_user_id:
        return

    await ctx.send('ما هو اسم الأنمي؟')

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    try:
        message = await bot.wait_for('message', check=check, timeout=60)
        anime_name = message.content

        # طلب معلومات الأنمي من MyAnimeList
        response = requests.get(
            f'https://api.myanimelist.net/v2/anime?q={anime_name}&limit=1',
            headers=headers)
        data = response.json()

        if 'data' in data and data['data']:
            anime_info = data['data'][0]['node']

            # الحصول على تفاصيل الأنمي
            anime_id = anime_info['id']
            details_response = requests.get(
                f'https://api.myanimelist.net/v2/anime/{anime_id}?fields=id,title,main_picture,synopsis,num_episodes',
                headers=headers)
            details = details_response.json()

            # ترجمة القصة إلى العربية
            translated_synopsis = translator.translate(details['synopsis'])

            # إعداد الـ embed
            embed = discord.Embed(title=details['title'],
                                  description=translated_synopsis,
                                  color=0x00ff00)
            embed.set_image(url=details['main_picture']['large'])
            embed.add_field(name='عدد الحلقات',
                            value=details['num_episodes'],
                            inline=False)

            embed_channel = bot.get_channel(embed_channel_id)
            if embed_channel is not None:
                # الحصول على الرتبة @Full Anime
                role = discord.utils.get(ctx.guild.roles, name="Full Anime")
                if role:
                    mention = role.mention
                    await embed_channel.send(f'{mention}', embed=embed)
                else:
                    await ctx.send('تعذر العثور على الرتبة المحددة.')

            else:
                await ctx.send(
                    'تعذر العثور على القناة المحددة لإرسال الـ embed.')

            # انتظار ملف txt من المستخدم
            await ctx.send('من فضلك أرسل الملف النصي المطلوب.')

            def file_check(message):
                return message.author == ctx.author and message.channel == ctx.channel and len(
                    message.attachments) > 0

            file_message = await bot.wait_for('message',
                                              check=file_check,
                                              timeout=60)
            attachment = file_message.attachments[0]

            if attachment.filename.endswith('.txt'):
                file_path = attachment.filename
                await attachment.save(file_path)
                await ctx.send('تم استلام الملف بنجاح.')

                if embed_channel is not None:
                    await embed_channel.send(file=discord.File(file_path))
                    os.remove(file_path)  # حذف الملف بعد إرساله
                else:
                    await ctx.send(
                        'تعذر العثور على القناة المحددة لإرسال الملف.')
            else:
                await ctx.send('الملف المرسل ليس ملف نصي.')

        else:
            await ctx.send('لم يتم العثور على الأنمي.')

    except requests.RequestException as e:
        await ctx.send(f'حدث خطأ في الاتصال بموقع MyAnimeList: {e}')
    except Exception as e:
        await ctx.send(f'حدث خطأ غير متوقع: {e}')


@bot.command()
async def chk(ctx):
    await ctx.send('من فضلك أرسل الملف النصي المطلوب.')

    def file_check(message):
        return message.author == ctx.author and message.channel == ctx.channel and len(message.attachments) > 0

    try:
        file_message = await bot.wait_for('message', check=file_check, timeout=60)
        attachment = file_message.attachments[0]

        if attachment.filename.endswith('.txt'):
            file_path = attachment.filename
            await attachment.save(file_path)
            await ctx.send('تم استلام الملف بنجاح جاري فخص الروابط الرجاء الانتظار (قد يستغرق الأمر وقتا)')

            def check_url(url):
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 404:
                        return f"الرابط هذه لا يعمل: {url}"
                    else:
                        return f"الرابط هذه يعمل: {url}"
                except requests.RequestException as e:
                    return f"حدث خطأ أثناء محاولة الوصول إلى الرابط {url}: {e}"

            def check_urls_from_file(file_path):
                results = []
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        urls = file.readlines()
                        for url in urls:
                            url = url.strip()
                            if url:  # تأكد من أن السطر ليس فارغاً
                                results.append(check_url(url))
                except FileNotFoundError:
                    results.append(f"لم يتم العثور على الملف: {file_path}")
                except Exception as e:
                    results.append(f"حدث خطأ أثناء قراءة الملف: {e}")
                return results

            results = check_urls_from_file(file_path)
            os.remove(file_path)  # حذف الملف بعد التحقق من الروابط

            # إرسال النتائج في رسالة خاصة
            try:
                await ctx.author.send('\n'.join(results))
            except discord.Forbidden:
                await ctx.send('الرجاء فتح الخاص لاستلام النتائج.')
        else:
            await ctx.send('الملف المرسل ليس ملف نصي.')
    except Exception as e:
        await ctx.send(f'حدث خطأ غير متوقع: {e}')


# تشغيل البوت
if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ['token'])
