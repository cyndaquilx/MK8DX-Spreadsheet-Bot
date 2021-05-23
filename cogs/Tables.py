import discord
from discord.ext import commands

import aiosqlite
import gspread_asyncio
from oauth2client.service_account import ServiceAccountCredentials

import urllib
import re
import io
import aiohttp
import json
import random

from constants import (channels, ranks, bot_channels, SH_KEY, LOOKUP_KEY)

def get_creds():
    return ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json",
        [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    )
agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)

class Tables(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open('./config.json', 'r') as cjson:
            self.config = json.load(cjson)

    @commands.command(aliases=['l2t'])
    async def lorenzi2table(self, ctx, *, data):
        def isGps(scores:str):
            #gps = scores.split("|")
            gps = re.split("[|+]", scores)
            for gp in gps:
                if gp.strip().isdigit() == False:
                    return False
        def sumGps(scores:str):
            #gps = scores.split("|")
            gps = re.split("[|+]", scores)
            sum = 0
            for gp in gps:
                sum += int(gp.strip())
            return sum
        def removeExtra(line):
            splitLine = line.split()
            if line.strip() == "":
                return False
            if len(splitLine) == 1:
                return False
            scores = splitLine[len(splitLine)-1]
            if scores.isdigit() == False and isGps(scores) == False:
                return False
            else:
                return True
        
        lines = filter(removeExtra, data.split("\n"))
        players = []
        scores = []
        for line in lines:
            # removes country flag brackets
            newline = re.sub("[\[].*?[\]]", "", line).split()
            players.append(" ".join(newline[0:len(newline)-1]))
            #scores.append(int(newline[len(newline)-1]))
            gps = newline[len(newline)-1]
            scores.append(sumGps(gps))
        if len(players) != 12:
            await ctx.send("Your table does not contain 12 valid score lines, try again!")
            return
        msg = "`!submit table <size> <tier> "
        playerScoreStrings = []
        for i in range(12):
            playerScoreStrings.append("%s, %d" % (players[i], scores[i]))
        msg += ", ".join(playerScoreStrings)
        msg += "`"
        await ctx.send(msg)

    @commands.command()
    async def pending(self, ctx):
        if ctx.guild.id != self.config["server"]:
            await ctx.send("You cannot use this command in this server!")
            return
        try:
            db = await aiosqlite.connect('updating.db')
            c = await db.cursor()
            await c.execute("""SELECT * from tables""")
            tables = await c.fetchall()
            msg = ""
            for tier in channels.keys():
                tierTables = [table for table in tables if table[2].upper() == tier]
                count = len(tierTables)
                if count > 0:
                    msg += ("Tier %s: %d tables\n"
                            % (tier, count))
                    for table in tierTables:
                        msg += ("\tSubmission ID %s\n"
                                % table[0])
            if len(msg) == 0:
                msg = "There are no pending tables to be updated"
            await ctx.send(msg)
        except:
            return
        finally:
            await db.close()

    @commands.command()
    async def view(self, ctx, tableid: int):
        if ctx.guild.id != self.config["server"]:
            await ctx.send("You cannot use this command in this server!")
            return
        try:
            db = await aiosqlite.connect('updating.db')
            c = await db.cursor()
            await c.execute("SELECT * from tables WHERE tableid = ?", (tableid,))
            table = await c.fetchone()
            #await ctx.send(table)
            messageid = table[6]
            lorenziurl = table[5]
            tier = table[2]
            channel = ctx.guild.get_channel(channels[tier.upper()])
            
            #await ctx.send(tableMsg.jump_url)
            e = discord.Embed(title="Table")
            try:
                tableMsg = await channel.fetch_message(messageid)
                msgLink = "[Link](%s)" % tableMsg.jump_url
                e.add_field(name="Message Link", value=msgLink)
            except:
                pass
            e.set_image(url=lorenziurl)
            #e.set_thumbnail(url=ctx.guild.icon)
            await ctx.send(embed=e)
            return
        except:
            await ctx.send("Table couldn't be found")
            return
        finally:
            await db.close()

    @commands.group()
    async def submit(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @submit.command()
    @commands.has_any_role("Administrator", "Updater", "Staff-S", "Reporter ‍")
    #@commands.cooldown(3, 60, commands.BucketType.member)
    async def delete(self, ctx, tableid:int):
        if ctx.guild.id != self.config["server"]:
            await ctx.send("You cannot use this command in this server!")
            return
        try:
            db = await aiosqlite.connect('updating.db')
            c = await db.cursor()
            await c.execute("SELECT * from tables WHERE tableid = ?", (tableid,))
            table = await c.fetchone()
            msgid = table[6]
            authorid = table[7]
            tier = table[2]
            #print(msgid)
        except:
            await ctx.send("Database error: Table ID %d not found" % (tableid))
            return
        finally:
            await db.close()
        try:
            #print(authorid)
            channel = ctx.guild.get_channel(channels[tier.upper()])
            tableMsg = await channel.fetch_message(msgid)
            if authorid == ctx.author.id:
                await tableMsg.delete()
            else:
                await ctx.send("You are not the author of this table")
                return
        except:
            await ctx.send("Table message is already deleted")
            return
        try:
            db = await aiosqlite.connect('updating.db')
            c = await db.cursor()
            await c.execute("DELETE from tables WHERE tableid = ?", (tableid,))
            await db.commit()
            await ctx.send("Removed table %d from approval queue" % tableid)
        except:
            await ctx.send("Database error removing table from approval queue")
            return
        finally:
            await db.close()
        

    @submit.command()
    #@commands.max_concurrency(number=1,wait=True)
    @commands.has_any_role("Administrator", "Updater", "Staff-S", "Reporter ‍")
    @commands.cooldown(3, 60, commands.BucketType.member)
    async def table(self, ctx, size: int, tier, *, args):
        if ctx.guild.id != self.config["server"]:
            await ctx.send("You cannot use this command in this server!")
            return
        agc = await agcm.authorize()
        #sh = await agc.open_by_key(SH_KEY)
        #botSheet = await sh.worksheet("Bot")
        sh = await agc.open_by_key(LOOKUP_KEY)
        botSheet = await sh.worksheet("search")
        

        VALID_SIZES = [1, 2, 3, 4, 6]
        if size not in VALID_SIZES:
            await ctx.send("Your size is not valid. Correct sizes are: %s"
                           % (VALID_SIZES))
            return

        if tier.upper() not in channels.keys():
            await ctx.send("Your tier is not valid. Correct tiers are: %s"
                           % (list(channels.keys())))
            return
        
        arguments = args.split(",")
        if len(arguments) != 24:
            if len(arguments) % 2 == 0:
                ns = "names"
            else:
                ns = "scores"
            await ctx.send("There must be exactly 12 players and 12 scores for each table, but you typed %d %s"
                           % (int(len(arguments)/2), ns))
            return
        names = []
        scores = []
        for i in range(12):
            names.append(arguments[2*i].strip())
            try:
                scores.append(int(arguments[2*i+1].strip()))
            except:
                await ctx.send("%s is not a valid score!" %
                               (arguments[2*i+1].strip()))
                return
        is984 = sum(scores)

        teamscores = []
        teamnames = []
        teamplayerscores = []
        for i in range(int(12/size)):
            teamscore = 0
            tnames = []
            pscores = []
            for j in range(size):
                teamscore += scores[i*size+j]
                tnames.append(names[i*size+j])
                pscores.append(scores[i*size+j])
            teamscores.append(teamscore)
            teamnames.append(tnames)
            teamplayerscores.append(pscores)

        sortedScoresTeams = sorted(zip(teamscores, teamnames, teamplayerscores), reverse=True)
        sortedScores = [x for x, _, _ in sortedScoresTeams]
        sortedTeams = [x for _, x, _ in sortedScoresTeams]
        sortedpScores = [x for _, _, x in sortedScoresTeams]
        sortedNames = []
        tableScores = []
        placements = []
        for i in range(len(sortedScores)):
            sortedNames += sortedTeams[i]
            tableScores += sortedpScores[i]
            if i == 0:
                placements.append(1)
                continue
            if sortedScores[i] == sortedScores[i-1]:
                placements.append(placements[i-1])
                continue
            placements.append(i+1)
        

        updateCells = [{
            #'range': "C84:C95",
            'range': "B9:B20",
            'values': [[name] for name in sortedNames]
            }]

        await botSheet.batch_update(updateCells)

        #gotBatch = await botSheet.batch_get(["D84:E95"])
        gotBatch = await botSheet.batch_get(["C9:C20"])
        goodNames = [gotBatch[0][i][0] for i in range(12)]
        #print(goodNames)
        #mmrs = [gotBatch[0][i][1] for i in range(12)]

        errors = ""
        for i in range(12):
            if goodNames[i] == "N/A":
                #await ctx.send("Player %s is not on the leaderboard; check your input"
                #               % (sortedNames[i]))
                errors += ("Player %s is not on the leaderboard; check your input\n"
                               % (sortedNames[i]))
                #return
        if len(errors) > 0:
            await ctx.send(errors)
            return

        base_url_lorenzi = "https://gb.hlorenzi.com/table.png?data="
        if size > 1:
            table_text = ("#title Tier %s %dv%d\n"
                          % (tier.upper(), size, size))
        else:
            table_text = ("#title Tier %s FFA\n"
                          % (tier.upper()))
        if size == 1:
            table_text += "FFA - Free for All #4A82D0\n"
        for i in range(int(12/size)):
            #table_text += "Team %d - A\n" % (i+1)
            if size != 1:
                if i % 2 == 0:
                    teamcolor = "#1D6ADE"
                else:
                    teamcolor = "#4A82D0"
                table_text += "%d %s\n" % (placements[i], teamcolor)
                #table_text += ("%s - A\n"
                #               % (chr(random.randrange(65, 65+26))))
            #else:
            #    table_text += "Team %d - A\n" % (i+1)
            for j in range(size):
                index = size * i + j
                table_text += ("%s %d\n"
                               % (goodNames[index], sortedpScores[i][j]))

        url_table_text = urllib.parse.quote(table_text)
        image_url = base_url_lorenzi + url_table_text

        e = discord.Embed(title="Table")
        e.set_image(url=image_url)
        content = "Please react to this message with \U00002611 within the next 30 seconds to confirm the table is correct"
        if is984 != 984:
            warning = ("The total score of %d might be incorrect! Most tables should add up to 984 points"
                       % is984)
            e.add_field(name="Warning", value=warning)
        embedded = await ctx.send(content=content, embed=e)
        #ballot box with check emoji
        CHECK_BOX = "\U00002611"
        X_MARK = "\U0000274C"
        await embedded.add_reaction(CHECK_BOX)
        await embedded.add_reaction(X_MARK)

        def check(reaction, user):
            if user != ctx.author:
                return False
            if reaction.message != embedded:
                return False
            if str(reaction.emoji) == X_MARK:
                #raise Exception()
                return True
            if str(reaction.emoji) == CHECK_BOX:
                return True
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except:
            await embedded.delete()
            return

        if str(reaction.emoji) == X_MARK:
            await embedded.delete()
            return

        #print(str(reaction.emoji))
        #return
            
        namesstr = ",".join(goodNames)
        placesstr = ",".join(str(p) for p in placements)
        db_entry = (size, tier.upper(), namesstr, placesstr, image_url, 0, ctx.author.id)
            
        try:
            db = await aiosqlite.connect('updating.db')
            c = await db.cursor()
            await c.execute("""INSERT INTO tables
                            (size, tier, names, placements, tableurl, messageid, authorid)
                            VALUES (?,?,?,?,?,?,?)
                            """, db_entry)
            newid = c.lastrowid
            await db.commit()
            
            #await ctx.send("Table ID: %d" % (newid))
        except Exception as e:
            print(e)
            return
        finally:
            await db.close()
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return await ctx.send("Could not download image...")
                data = io.BytesIO(await resp.read())
                f = discord.File(data, filename="MogiTable.png")
        e = discord.Embed(title="Mogi Table", colour=int("0A2D61", 16))
        #e.add_field(name="Format", value="%dv%d" % (size, size))
        e.add_field(name="ID", value=newid)
        e.add_field(name="Tier", value=tier.upper())
        e.add_field(name="Submitted by", value=ctx.author.mention)
        update_command = ("`!update approve %d`\n`!update text %d %s %s; %s`"
                          % (newid, size, tier.upper(),
                             ", ".join(goodNames),
                             " ".join(str(p) for p in placements)))
        e.add_field(name="Updating command", value=update_command, inline=False)
        e.set_image(url="attachment://MogiTable.png")
        channel = ctx.guild.get_channel(channels[tier.upper()])
        tableMsg = await channel.send(file=f, embed=e)
        await embedded.delete()
        if channel == ctx.channel:
            await ctx.message.delete()
        else:
            await ctx.send("Successfully sent table to %s `(ID: %d)`" %
                           (channel.mention, newid))

        try:
            db = await aiosqlite.connect('updating.db')
            c = await db.cursor()
            await c.execute("""UPDATE tables SET messageid = ?
                                WHERE tableid = ?
                            """, (tableMsg.id, newid))
            await db.commit()
        except Exception as e:
            print(e)
            return
        finally:
            await db.close()

    @submit.command()
    #@commands.max_concurrency(number=1,wait=True)
    @commands.has_any_role("Administrator", "Updater", "Staff-S", "Reporter ‍")
    @commands.cooldown(3, 60, commands.BucketType.member)
    async def lorenzi(self, ctx, size: int, tier, *, data):
        def isGps(scores:str):
            #gps = scores.split("|")
            gps = re.split("[|+]", scores)
            for gp in gps:
                if gp.strip().isdigit() == False:
                    return False
        def sumGps(scores:str):
            #gps = scores.split("|")
            gps = re.split("[|+]", scores)
            sum = 0
            for gp in gps:
                sum += int(gp.strip())
            return sum
        def removeExtra(line):
            splitLine = line.split()
            if line.strip() == "":
                return False
            if len(splitLine) == 1:
                return False
            scores = splitLine[len(splitLine)-1]
            if scores.isdigit() == False and isGps(scores) == False:
                return False
            else:
                return True
        
        lines = filter(removeExtra, data.split("\n"))
        names = []
        scores = []
        for line in lines:
            # removes country flag brackets
            newline = re.sub("[\[].*?[\]]", "", line).split()
            names.append(" ".join(newline[0:len(newline)-1]))
            #scores.append(int(newline[len(newline)-1]))
            gps = newline[len(newline)-1]
            scores.append(sumGps(gps))
        if len(names) != 12:
            await ctx.send("Your table does not contain 12 valid score lines, try again!")
            return
        if ctx.guild.id != self.config["server"]:
            await ctx.send("You cannot use this command in this server!")
            return
        agc = await agcm.authorize()
        #sh = await agc.open_by_key(SH_KEY)
        #botSheet = await sh.worksheet("Bot")
        sh = await agc.open_by_key(LOOKUP_KEY)
        botSheet = await sh.worksheet("search")
        

        VALID_SIZES = [1, 2, 3, 4, 6]
        if size not in VALID_SIZES:
            await ctx.send("Your size is not valid. Correct sizes are: %s"
                           % (VALID_SIZES))
            return

        if tier.upper() not in channels.keys():
            await ctx.send("Your tier is not valid. Correct tiers are: %s"
                           % (list(channels.keys())))
            return
        is984 = sum(scores)

        teamscores = []
        teamnames = []
        teamplayerscores = []
        for i in range(int(12/size)):
            teamscore = 0
            tnames = []
            pscores = []
            for j in range(size):
                teamscore += scores[i*size+j]
                tnames.append(names[i*size+j])
                pscores.append(scores[i*size+j])
            teamscores.append(teamscore)
            teamnames.append(tnames)
            teamplayerscores.append(pscores)

        sortedScoresTeams = sorted(zip(teamscores, teamnames, teamplayerscores), reverse=True)
        sortedScores = [x for x, _, _ in sortedScoresTeams]
        sortedTeams = [x for _, x, _ in sortedScoresTeams]
        sortedpScores = [x for _, _, x in sortedScoresTeams]
        sortedNames = []
        tableScores = []
        placements = []
        for i in range(len(sortedScores)):
            sortedNames += sortedTeams[i]
            tableScores += sortedpScores[i]
            if i == 0:
                placements.append(1)
                continue
            if sortedScores[i] == sortedScores[i-1]:
                placements.append(placements[i-1])
                continue
            placements.append(i+1)
        

        updateCells = [{
            #'range': "C84:C95",
            'range': "B9:B20",
            'values': [[name] for name in sortedNames]
            }]

        await botSheet.batch_update(updateCells)

        #gotBatch = await botSheet.batch_get(["D84:E95"])
        gotBatch = await botSheet.batch_get(["C9:C20"])
        goodNames = [gotBatch[0][i][0] for i in range(12)]
        #print(goodNames)
        #mmrs = [gotBatch[0][i][1] for i in range(12)]

        errors = ""
        for i in range(12):
            if goodNames[i] == "N/A":
                #await ctx.send("Player %s is not on the leaderboard; check your input"
                #               % (sortedNames[i]))
                errors += ("Player %s is not on the leaderboard; check your input\n"
                               % (sortedNames[i]))
                #return
        if len(errors) > 0:
            await ctx.send(errors)
            return

        base_url_lorenzi = "https://gb.hlorenzi.com/table.png?data="
        if size > 1:
            table_text = ("#title Tier %s %dv%d\n"
                          % (tier.upper(), size, size))
        else:
            table_text = ("#title Tier %s FFA\n"
                          % (tier.upper()))
        if size == 1:
            table_text += "FFA - Free for All #4A82D0\n"
        for i in range(int(12/size)):
            #table_text += "Team %d - A\n" % (i+1)
            if size != 1:
                if i % 2 == 0:
                    teamcolor = "#1D6ADE"
                else:
                    teamcolor = "#4A82D0"
                table_text += "%d %s\n" % (placements[i], teamcolor)
            for j in range(size):
                index = size * i + j
                table_text += ("%s %d\n"
                               % (goodNames[index], sortedpScores[i][j]))

        url_table_text = urllib.parse.quote(table_text)
        image_url = base_url_lorenzi + url_table_text + "&lounge=true"

        e = discord.Embed(title="Table")
        e.set_image(url=image_url)
        content = "Please react to this message with \U00002611 within the next 30 seconds to confirm the table is correct"
        if is984 != 984:
            warning = ("The total score of %d might be incorrect! Most tables should add up to 984 points"
                       % is984)
            e.add_field(name="Warning", value=warning)
        embedded = await ctx.send(content=content, embed=e)
        #ballot box with check emoji
        CHECK_BOX = "\U00002611"
        X_MARK = "\U0000274C"
        await embedded.add_reaction(CHECK_BOX)
        await embedded.add_reaction(X_MARK)

        def check(reaction, user):
            if user != ctx.author:
                return False
            if reaction.message != embedded:
                return False
            if str(reaction.emoji) == X_MARK:
                #raise Exception()
                return True
            if str(reaction.emoji) == CHECK_BOX:
                return True
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except:
            await embedded.delete()
            return

        if str(reaction.emoji) == X_MARK:
            await embedded.delete()
            return

        #print(str(reaction.emoji))
        #return
            
        namesstr = ",".join(goodNames)
        placesstr = ",".join(str(p) for p in placements)
        db_entry = (size, tier.upper(), namesstr, placesstr, image_url, 0, ctx.author.id)
            
        try:
            db = await aiosqlite.connect('updating.db')
            c = await db.cursor()
            await c.execute("""INSERT INTO tables
                            (size, tier, names, placements, tableurl, messageid, authorid)
                            VALUES (?,?,?,?,?,?,?)
                            """, db_entry)
            newid = c.lastrowid
            await db.commit()
            
            #await ctx.send("Table ID: %d" % (newid))
        except Exception as e:
            print(e)
            return
        finally:
            await db.close()
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return await ctx.send("Could not download image...")
                data = io.BytesIO(await resp.read())
                f = discord.File(data, filename="MogiTable.png")
        e = discord.Embed(title="Mogi Table", colour=int("0A2D61", 16))
        #e.add_field(name="Format", value="%dv%d" % (size, size))
        e.add_field(name="ID", value=newid)
        e.add_field(name="Tier", value=tier.upper())
        e.add_field(name="Submitted by", value=ctx.author.mention)
        update_command = ("`!update approve %d`\n`!update text %d %s %s; %s`"
                          % (newid, size, tier.upper(),
                             ", ".join(goodNames),
                             " ".join(str(p) for p in placements)))
        e.add_field(name="Updating command", value=update_command, inline=False)
        e.set_image(url="attachment://MogiTable.png")
        channel = ctx.guild.get_channel(channels[tier.upper()])
        tableMsg = await channel.send(file=f, embed=e)
        await embedded.delete()
        if channel == ctx.channel:
            await ctx.message.delete()
        else:
            await ctx.send("Successfully sent table to %s `(ID: %d)`" %
                           (channel.mention, newid))

        try:
            db = await aiosqlite.connect('updating.db')
            c = await db.cursor()
            await c.execute("""UPDATE tables SET messageid = ?
                                WHERE tableid = ?
                            """, (tableMsg.id, newid))
            await db.commit()
        except Exception as e:
            print(e)
            return
        finally:
            await db.close()

def setup(bot):
    bot.add_cog(Tables(bot))
