import discord
from discord import Interaction, ui, Integration, app_commands, TextStyle
from discord.ui import TextInput, View, Modal, Select
from discord.ext import commands
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

url = "https://ddragon.leagueoflegends.com/api/versions.json"
response = requests.get(url)
vcs = response.json()[0]

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--log-level=3')
driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

url_jp = 'http://ddragon.leagueoflegends.com/cdn/' + vcs + '/data/ja_JP/item.json'
url_en = 'http://ddragon.leagueoflegends.com/cdn/' + vcs + '/data/en_US/item.json'
response_jp = requests.get(url_jp).json()["data"]
response_en = requests.get(url_en).json()["data"]

def engItem_to_jpName(item):
    global response_jp, response_en
    for key in response_jp:
        if response_en[key]["name"] == item:
            return response_jp[key]["name"]
    return item

print('LoL Version: ' + vcs)

def getDDragonVersion():
    return vcs

# build modal
class BuildModal(Modal):
    def __init__(self, title = "LoL Bot - チャンピオンを選択してください") -> None:
        super().__init__(title=title)
        self.campion = TextInput(
            label="チャンピオン名",
            placeholder="チャンピオン名を入力してください",
            min_length=1,
            max_length=32,
            custom_id="campion",
            style=TextStyle.short,
            required=True
        )
        self.lane = TextInput(
            label="ロール（略語可）",
            placeholder="ロールを入力してください",
            min_length=1,
            max_length=32,
            custom_id="lane",
            style=TextStyle.short,
            required=True
        )
        self.add_item(self.campion)
        self.add_item(self.lane)
        self.timeout = 180

    async def on_submit(self, interaction: Interaction) -> None:
        if self.timeout == 0:
            await interaction.response.send_message("タイムアウトしました。", ephemeral=True)
            return
        campion = self.campion.value
        lane = self.lane.value
        await interaction.response.send_message(content="検索中...", ephemeral=True)
        async with interaction.channel.typing():
            # getBuildの検索中にタイムアウトするとエラーになるので、tryで囲む
            try:
                embed = getBuild(campion, lane)
            except:
                await interaction.channel.send("タイムアウトしました。")
                return
            await interaction.channel.send(embed=embed)

def getBuild(campion, lane):
    if lane == "":
            return discord.Embed(title="エラー", description="ロールが見つかりませんでした。", color=0xff0000)
    else:
        maps = {
            "top/": ["トップ", "top"],
            "jungle/": ["ジャングル", "jungle", "jg"],
            "mid/": ["ミッド", "mid"],
            "adc/": ["adcarry", "adc", "ad"],
            "support/": ["サポート", "support", "sup", "sp"]
        }
        lane_flag = False
        lane_jp = ""
        for key in maps:
            if lane.lower() in maps[key]:
                lane = key
                lane_flag = True
                break
        if not lane_flag:
            return discord.Embed(title="エラー", description="ロールが見つかりませんでした。", color=0xff0000)
        
        mps = {
            "top": "トップ",
            "jungle": "ジャングル",
            "mid": "ミッド",
            "adc": "ADC",
            "support": "サポート"
        }
        lane_jp = mps[lane[:-1]]

    url = 'http://ddragon.leagueoflegends.com/cdn/' + vcs + '/data/ja_JP/champion.json';
    response = requests.get(url).json()["data"]
    champ_flag = False
    for champion in response:
        if response[champion]["name"] == campion:
            campion = champion
            champ_flag = True
            break
        elif champion.lower() == campion.lower():
            campion = champion
            champ_flag = True
            break
    if not champ_flag:
        return discord.Embed(title="エラー", description="チャンピオンが見つかりませんでした。", color=0xff0000)
    url = 'http://ddragon.leagueoflegends.com/cdn/' + vcs + '/data/ja_JP/champion/' + campion + '.json'
    response = requests.get(url).json()["data"][campion]
    embed = discord.Embed(title=response["name"] + " / " + lane_jp, description=response["title"], color=0x00ff00)
    embed.set_thumbnail(url='http://ddragon.leagueoflegends.com/cdn/' + vcs + '/img/champion/' + campion + '.png')
    embed.add_field(name="ロール", value=response["tags"][0], inline=True)

    # spacer (スマホでも対応するように\u200bは使わない）
    embed.add_field(name="--------", value="", inline=False)
    
    url_build = "https://www.op.gg/champions/" + champion.lower() + "/" + lane + "items?region=kr&tier=diamond_plus"
    url_runes = "https://lolmeta.info/champ/" + champion.lower() + "/runes/" + lane
    url_runes = url_runes[:-1]
    driver.get(url_build)
    driver.implicitly_wait(10)

    core_elems = driver.find_elements(by=By.XPATH, value="/html/body/div[1]/div[5]/div/div[1]/section[1]/table/tbody/tr[1]/td[1]/div/div")
    alts_elem = core_elems[0].find_elements(by=By.CLASS_NAME, value="bg-image")
    alts = []
    for elem in alts_elem:
        alts.append(elem.get_attribute("alt"))
    msg = ""
    nc = 1
    for alt in alts:
        msg += str(nc) + ". " + engItem_to_jpName(alt) + "\n"
        nc += 1
    embed.add_field(name="コアビルド", value=msg, inline=False)
    msg = ""

    boots_elem = driver.find_elements(by=By.XPATH, value="/html/body/div[1]/div[5]/div/div[1]/section[2]/table/tbody/tr[1]/td[1]/div/div")
    boots_elem = boots_elem[0].find_elements(by=By.CLASS_NAME, value="bg-image")
    boots = []
    for elem in boots_elem:
        boots.append(elem.get_attribute("alt"))
    for boot in boots:
        msg += engItem_to_jpName(boot) + "\n"
    embed.add_field(name="ブーツ", value=msg, inline=False)
    msg = ""

    first_elems = driver.find_elements(by=By.XPATH, value="/html/body/div[1]/div[5]/div/div[1]/section[3]/table/tbody/tr[1]/td[1]/div/div")
    first_elems = first_elems[0].find_elements(by=By.CLASS_NAME, value="bg-image")
    firsts = []
    for elem in first_elems:
        firsts.append(elem.get_attribute("alt"))
    for first in firsts:
        msg += engItem_to_jpName(first) + "\n"
    embed.add_field(name="初期アイテム", value=msg, inline=False)

    embed.add_field(name="--------", value="", inline=True)

    driver.get(url_runes)
    driver.implicitly_wait(10)

    # 8個
    runes = driver.find_elements(by=By.CLASS_NAME, value="rune_name")
    if len(runes) > 8:
        runes = runes[:8]
    else:
        return embed
    msg = ""
    # 5個
    for rune in runes[:5]:
        msg += rune.text + "\n"
    embed.add_field(name="ルーン", value=msg, inline=False)

    msg = ""
    # 3個
    for rune in runes[5:]:
        msg += rune.text + "\n"
    embed.add_field(name="サブルーン", value=msg, inline=False)
    

    # footer
    embed.set_footer(text="Created by y-#1234")

    return embed

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game(name="/lol or /build"))
    print('Ready!')
    await tree.sync()

@tree.command(
        name="build",
        description="ビルドを表示します。"
)
async def build(interaction: Interaction):
    modal = BuildModal()
    await interaction.response.send_modal(modal)
    


@tree.command(
    name="lol",
    description="プレイヤー情報を取得します。"
)
@discord.app_commands.describe(
    name="サモナーネームを入力してください。"
)
@discord.app_commands.describe(
    name="リージョンを入力してください。"
)
@discord.app_commands.guild_only()
async def lol(ctx, name: str, region: str = "jp1"):
    await ctx.response.defer()
    suffix = ".api.riotgames.com"
    url = "https://" + region + suffix + "/lol/summoner/v4/summoners/by-name/" + name + "?api_key=" + token_riot
    icon_id = 0
    response = requests.get(url)
    # print(url)
    if response.status_code == 200:
        data = response.json()
        summoner_id = data["id"]
        summoner_name = data["name"]
        summoner_level = data["summonerLevel"]
        icon_id = str(data["profileIconId"])
        url = "https://" + region + suffix + "/lol/league/v4/entries/by-summoner/" + summoner_id + "?api_key=" + token_riot
        response = requests.get(url)
        icon_url = 'http://ddragon.leagueoflegends.com/cdn/' + vcs + '/img/profileicon/' + icon_id + '.png'
        # print(icon_url)
        if response.status_code == 200:
            data = response.json()
            if len(data) == 0:
                embed = discord.Embed(title=summoner_name, description="Unranked", color=0x00ff00)
                footer_text = "created by y-#1234"
                embed.set_footer(text=footer_text)
                embed.set_thumbnail(url=icon_url)
                embed.add_field(name="Level", value=summoner_level, inline=True)
                await ctx.followup.send(embed=embed)
            else:
                tier = data[0]["tier"]
                rank = data[0]["rank"]
                lp = data[0]["leaguePoints"]
                wins = data[0]["wins"]
                losses = data[0]["losses"]
                win_rate = int(wins / (wins + losses) * 100)
                embed = discord.Embed(title=summoner_name, description=tier + " " + rank + " " + str(lp) + "LP", color=0x00ff00)
                embed.set_thumbnail(url=icon_url)
                footer_text = "Created by y-#1234"
                embed.set_footer(text=footer_text)
                embed.add_field(name="Level", value=summoner_level, inline=True)
                embed.add_field(name="Win Rate (Rank)", value=str(win_rate) + "%", inline=True)

                url_m = 'https://' + region + suffix + '/lol/champion-mastery/v4/champion-masteries/by-summoner/' + summoner_id + '?api_key=' + token_riot
                response_m = requests.get(url_m)
                # print(url_m)
                if response_m.status_code == 200:
                    # three most played champions
                    data_m = response_m.json()
                    txt = ""
                    masteries = []
                    url_c = 'http://ddragon.leagueoflegends.com/cdn/' + vcs + '/data/ja_JP/champion.json'
                    response_c = requests.get(url_c)
                    for i in range(10):
                        if i >= len(data_m):
                            break
                        champion_id = str(data_m[i]["championId"])
                        champion_level = str(data_m[i]["championLevel"])
                        champion_points = str(data_m[i]["championPoints"])
                        if response_c.status_code == 200:
                            data_c = response_c.json()
                            for champion in data_c["data"]:
                                if data_c["data"][champion]["key"] == champion_id:
                                    champion_name = data_c["data"][champion]["name"]
                                    masteries.append([champion_name, champion_level, champion_points])
                    
                    # マスタリーポイントを3桁ごとにカンマを入れる
                    for i in range(len(masteries)):
                        masteries[i][2] = "{:,}".format(int(masteries[i][2]))

                    for i in range(len(masteries)):
                        txt += masteries[i][0] + " (Lv." + masteries[i][1] + ") \n" + masteries[i][2] + "pt \n"
                    embed.add_field(name="Most Played Champions", value=txt, inline=False)
                else:
                    await ctx.followup.send("エラーが発生しました。")
                    
                await ctx.followup.send(embed=embed)
        else:
            # print('error 1')
            await ctx.followup.send("エラーが発生しました。")
    else:
        # print('error 2')
        await ctx.followup.send("エラーが発生しました。")

file = open("token.txt", "r")
token_discord = file.readline().split(": ")[1]
token_riot = file.readline().split(": ")[1]
file.close()

client.run(token_discord)