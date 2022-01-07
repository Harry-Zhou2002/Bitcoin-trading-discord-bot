import discord
import os
import requests
import json
import pymongo
from pymongo import MongoClient
import threading

## To run this bot on your computer, modify value of token to your Discord bot token and value of mongo_url to your mongoDB url.

client = discord.Client()
token = os.environ['token']
mongo_url = os.environ['aaa']
api = 'https://blockchain.info/ticker'

## MongoDB

cluster = pymongo.MongoClient(mongodburl)

db = cluster["userdata"]
collection = db["userdata"]

serverStatusResult = db.command("serverStatus")

sell = 0
buy = 0


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))


## Commands:
## /create x -Create an accouont with x USD, one user can have at most one account
## /delete -Delete your account
## /portfolio -Check your portfolio
## /rate -Check current price of the bitcoin
## /buy btc/usd xx -Buy xx btc or buy xx usd worth of btc
## /sell btc/usd xx -Sell xx btc or buy xx usd worth of btc
## /limit buy/sell btc/usd xx at yy -Place limit buy/sell order of xx btc or xx usd worth of btc at the price of yy usd.

@client.event
async def on_message(message):
    price = get_price()
    authorid = message.author.id

    if message.author == client.user:
        return
    #################################################
    # create
    if message.content.startswith('/create'):
        start = float(message.content.split("/create ", 1)[1])
        if (collection.count_documents({'_id': authorid}, limit=1)) == 1:
            await message.channel.send('You already have an account')
        else:
            entry = {'_id': authorid, 'btc': 0, 'usd': start, 'limit': ['none', 0, 0]}
            collection.insert_one(entry)
            await message.channel.send('Account created, starting balance ${}'.format(start))
    #################################################
    # delete
    if message.content.startswith('/delete'):
        if (collection.count_documents({'_id': authorid}, limit=1)) == 1:
            collection.delete_one({'_id': authorid})
            await message.channel.send('Deleted')
        else:
            await message.channel.send('You do not have an account')
    #################################################
    # portfolio
    if message.content.startswith('/portfolio'):
        if (collection.count_documents({'_id': authorid}, limit=1)) == 1:
            data = collection.find_one({'_id': authorid})
            btc = data['btc']
            usd = data["usd"]
            limittype = data['limit'][0]
            limitamount = data['limit'][2]
            limitprice = data['limit'][1]
            await message.channel.send(
                'Portfolio: USD {:f}\nBTC {:f}\nLimits Orders: {} order of {} BTC at {}'.format(usd, btc, limittype,
                                                                                                limitamount,
                                                                                                limitprice))

        else:
            await message.channel.send('Create an account first')

    if message.content.startswith('/rate'):
        await message.channel.send('Current exchange rate: 1BTC = ${}'.format(price))
    #################################################
    # buy

    if message.content.startswith('/buy'):
        amount = float(message.content.split()[2])
        btype = message.content.split()[1]
        data = collection.find_one({'_id': authorid})
        filter = {'_id': authorid}

        if btype == 'btc':

            if data != None:
                usdfloat = float(data["usd"])
                if ((amount * price) > usdfloat):
                    await message.channel.send('insufficient funds')
                    return
                else:
                    btcnew = {"$set": {'btc': float(data["btc"]) + amount}}
                    usdnew = {"$set": {'usd': float(data["usd"]) - amount * price}}
                    collection.update_one(filter, btcnew)
                    collection.update_one(filter, usdnew)
                    await message.channel.send(
                        'You have bought {:f} BTC, at the rate of: BTC/USD {:f}'.format(amount, price))
            else:
                await message.channel.send('Create account first')
                return

        elif btype == 'usd':

            if data != None:
                usdfloat = float(data["usd"])
                if (amount > usdfloat):
                    await message.channel.send('insufficient funds')
                    return
                else:
                    btcnew = {"$set": {'btc': float(data["btc"]) + amount / price}}
                    usdnew = {"$set": {'usd': float(data["usd"]) - amount}}
                    collection.update_one(filter, btcnew)
                    collection.update_one(filter, usdnew)
                    await message.channel.send(
                        'You have bought {:f} BTC, at the rate of: BTC/USD {:f}'.format(amount / price, price))
            else:
                await message.channel.send('Create account first')
                return

    #################################################
    # sell
    if message.content.startswith('/sell'):
        amount = float(message.content.split()[2])
        btype = message.content.split()[1]
        data = collection.find_one({'_id': authorid})

        filter = {'_id': authorid}

        if btype == 'btc':

            if data != None:
                btcfloat = float(data["usd"])

                if amount > btcfloat:
                    await message.channel.send('insufficient funds')
                    return
                else:
                    btcnew = {"$set": {'btc': float(data["btc"]) - amount}}
                    usdnew = {"$set": {'usd': float(data["usd"]) + amount * price}}
                    collection.update_one(filter, btcnew)
                    collection.update_one(filter, usdnew)
                    await message.channel.send(
                        'You have sold {:f} BTC, at the rate of: BTC/USD {:f}'.format(amount, price))
            else:
                await message.channel.send('Create account first')
                return

        elif btype == 'usd':
            if data != None:
                btcfloat = float(data["usd"])
                if amount > btcfloat * price:
                    await message.channel.send('insufficient funds')
                    return
                else:
                    btcnew = {"$set": {'btc': float(data["btc"]) - amount / price}}
                    usdnew = {"$set": {'usd': float(data["usd"]) + amount}}
                    collection.update_one(filter, btcnew)
                    collection.update_one(filter, usdnew)
                    await message.channel.send(
                        'You have sold {:f} BTC, at the rate of: BTC/USD {:f}'.format(amount, price))
            else:
                await message.channel.send('Create account first')
                return

    #################################################
    # limit sell/buy
    if message.content.startswith('/limit'):
        limittype = message.content.split()[1]
        curtype = message.content.split()[2]
        amount = float(message.content.split()[3])
        limitprice = float(message.content.split()[5])
        data = collection.find_one({'_id': authorid})
        filter = {'_id': authorid}
        if data != None:
            if limittype == 'buy':
                if curtype == 'btc':
                    new = {"$set": {'limit': ['buy', limitprice, amount]}}
                    collection.update_one(filter, new)
                    await message.channel.send('Buy order created')
                elif curtype == 'usd':
                    new = {"$set": {'limit': ['buy', limitprice, amount / price]}}
                    collection.update_one(filter, new)
                    await message.channel.send('Buy order created')
            elif limittype == 'sell':
                if curtype == 'btc':
                    new = {"$set": {'limit': ['buy', limitprice, amount]}}
                    collection.update_one(filter, new)
                    await message.channel.send('Sell order created')
                elif curtype == 'usd':
                    new = {"$set": {'limit': ['buy', limitprice, amount / price]}}
                    collection.update_one(filter, new)
                    await message.channel.send('Sell order created')
        else:
            await message.channel.send('Create account first')


def get_price():
    response = requests.get(api)
    myjson = json.loads(response.text)
    price = myjson['USD']['15m']

    return float(price)


def is_valid(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

## A function for checking limit orders. Executes every 15 seconds.
def check():
    global sell
    global buy
    threading.Timer(15.0, check).start()
    price = get_price()

    for x in collection.find():
        if x["limit"][0] == 'buy':
            if price < x['limit'][1]:

                authorid = x["_id"]
                filter = {'_id': authorid}
                amount = x['limit'][2]
                if amount * price <= x['usd']:
                    # clear the set limit
                    newdata = {"$set": {'limit': ['none', 0, 0]}}
                    collection.update_one(filter, newdata)
                    print('Limit bought for id {}'.format(authorid))
                    # now actually buy

                    btcnew = {"$set": {'btc': float(x["btc"]) + amount}}
                    usdnew = {"$set": {'usd': float(x["usd"]) - amount * price}}
                    collection.update_one(filter, btcnew)
                    collection.update_one(filter, usdnew)

        elif x['limit'][0] == 'sell':
            if price > x['limit'][1]:

                authorid = x["_id"]
                filter = {'_id': authorid}
                amount = x['limit'][2]
                if amount <= x['btc']:
                    # clear the set limit
                    newdata = {"$set": {'limit': ['none', 0, 0]}}
                    collection.update_one(filter, newdata)
                    print('Limit sold for id {}'.format(authorid))
                    # now actually sell
                    btcnew = {"$set": {'btc': float(x["btc"]) - amount}}
                    usdnew = {"$set": {'usd': float(x["usd"]) + amount * price}}
                    collection.update_one(filter, btcnew)
                    collection.update_one(filter, usdnew)


check()
client.run(os.getenv('token'))




