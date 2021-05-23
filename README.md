# MK8DX-Spreadsheet-Bot

This is the old code for MK8DX Bot, designed to work with spreadsheets. As it's old, a lot of stuff here is extremely horribly written, but I have no reason to change it since our lounge uses a website now. However, this may still prove very useful to some lounge servers, so I'm uploading it here.

Before you do anything, you'll want to run **createdb.py**, it creates a database of submitted/updated tables and is required for the bot to work.

You'll also need API credentials from Google, which you can get by following instructions here: https://docs.gspread.org/en/latest/oauth2.html#enable-api-access-for-a-project

As the bot is designed to work with spreadsheets, a LOT of stuff is just hard coded; everything that is hard coded should be found in the **constants.py** file, along with some (hopefully) helpful comments as to what everything means.

The bot works on 3 sheets: 1) the sheet specifically designed for it to do lookups from the updating sheet, 2) the Player History sheet that most lounges should have, and 3) a special lookup sheet separate from the updating sheet to increase speed.

For your sanity, and to minimize the number of things in constants.py that you need to change, you should make copies of the following sheets and make changes to those for your lounge:

1: "Bot" sheet from this spreadsheet: https://docs.google.com/spreadsheets/d/1QGkQxiYncQBEyIxU049DUGA3QR0bP2JuHfenZrlVB6E/edit?usp=sharing

3: Everything from this spreadsheet: https://docs.google.com/spreadsheets/d/1ts17B2k8Hv5wnHB-4kCE3PNFL1EXEJ01lx-s8zPpECE/edit?usp=sharing

1 is equal to SH_KEY in constants.py, and 3 is equal to LOOKUP_KEY

Assuming you made copies of the above sheets, the following is what you'll need to change in constants.py for each lounge:
- SH_KEY
- LOOKUP_KEY
- rowOffset
- colOffset
- channels
- ranks
- place_MMRs
- getRank

After you've set all that up, it SHOULD work, let me know on Discord if it doesn't (Cynda#1979)
