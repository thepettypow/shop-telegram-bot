import json
from telethon import TelegramClient, events
from pymongo import MongoClient
import logging

# Config logging lib
logging.basicConfig(format='[%(asctime)s %(levelname)s]: %(message)s', level=logging.INFO, datefmt='%I:%M:%S')



# Load configuration from JSON file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

api_id = config['api_id']
api_hash = config['api_hash']
bot_token = config['bot_token']
mongo_uri = config['mongo_uri']
mongo_db_name = config['mongo_db_name']
mongo_collection_name = config['mongo_collection_name']

# Connecting to the Telegram client
client = TelegramClient('shop_bot', api_id, api_hash).start(bot_token=bot_token)

# Connecting to MongoDB
mongo_client = MongoClient(mongo_uri)
db = mongo_client[mongo_db_name]
users_collection = db[mongo_collection_name]


# Handler for start messages
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    sender = await event.get_sender()
    user_id = sender.id
    user = {
        'user_id': user_id,
        'username': sender.username,
        'first_name': sender.first_name,
        'last_name': sender.last_name,
        'orders': []
    }
    users_collection.update_one({'user_id': user_id}, {'$set': user}, upsert=True)
    await event.respond('Welcome to the shop!')


# Handler to show products
@client.on(events.NewMessage(pattern='/products'))
async def show_products(event):
    # Here you can display a list of your products
    products = "1. First Product\n2. Second Product\n3. Third Product"
    await event.respond(f"Available products:\n{products}")


# Handler to place an order
@client.on(events.NewMessage(pattern='/order (.+)'))
async def order(event):
    sender = await event.get_sender()
    user_id = sender.id
    product = event.pattern_match.group(1)

    # Update order information in the database
    users_collection.update_one(
        {'user_id': user_id},
        {'$push': {'orders': product}}
    )

    # Add payment gateway information here
    payment_link = "http://yourpaymentgateway.com/pay?amount=100&product=" + product

    await event.respond(f"Your order has been placed! Please visit the following link to make payment:\n{payment_link}")

logging.info('Starting...')
client.start()
logging.info("Bot Started Successfully!")
client.run_until_disconnected()
