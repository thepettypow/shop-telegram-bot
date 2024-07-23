import json
from telethon import TelegramClient, events
from pymongo import MongoClient
import logging

# Configuring logging
logging.basicConfig(
    format='[%(asctime)s %(levelname)s]: %(message)s',
    level=logging.INFO,
    datefmt='%I:%M:%S'
)

# Load configuration from JSON file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

api_id = config['api_id']
api_hash = config['api_hash']
bot_token = config['bot_token']
mongo_uri = config['mongo_uri']
mongo_db_name = config['mongo_db_name']
mongo_collection_name = config['mongo_collection_name']
admin_usernames = config['admin_usernames']

# Connecting to the Telegram client
client = TelegramClient('shop_bot', api_id, api_hash).start(bot_token=bot_token)

# Connecting to MongoDB
mongo_client = MongoClient(mongo_uri)
db = mongo_client[mongo_db_name]
users_collection = db[mongo_collection_name]
products_collection = db['products']


# Check if the user is an admin
def is_admin(username):
    return username in admin_usernames


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
        'basket': []
    }
    users_collection.update_one({'user_id': user_id}, {'$set': user}, upsert=True)
    await event.respond('Welcome to the shop!')


# Handler to show products
@client.on(events.NewMessage(pattern='/products'))
async def show_products(event):
    products = products_collection.find()
    products_list = '\n'.join(
        [f"{idx + 1}. {product['name']} - ${product['price']}" for idx, product in enumerate(products)])
    await event.respond(f"Available products:\n{products_list}")


# Handler to add product to basket
@client.on(events.NewMessage(pattern='/add_to_basket (.+)'))
async def add_to_basket(event):
    sender = await event.get_sender()
    user_id = sender.id
    product_name = event.pattern_match.group(1)
    product = products_collection.find_one({'name': product_name})
    if product:
        users_collection.update_one(
            {'user_id': user_id},
            {'$push': {'basket': product}}
        )
        await event.respond(f"{product_name} has been added to your basket.")
    else:
        await event.respond(f"Product {product_name} not found.")


# Handler to view basket
@client.on(events.NewMessage(pattern='/view_basket'))
async def view_basket(event):
    sender = await event.get_sender()
    user_id = sender.id
    user = users_collection.find_one({'user_id': user_id})
    basket = user['basket']
    basket_list = '\n'.join([f"{idx + 1}. {item['name']} - ${item['price']}" for idx, item in enumerate(basket)])
    await event.respond(f"Your basket:\n{basket_list}")


# Handler to place an order
@client.on(events.NewMessage(pattern='/checkout'))
async def checkout(event):
    sender = await event.get_sender()
    user_id = sender.id
    user = users_collection.find_one({'user_id': user_id})
    basket = user['basket']
    if not basket:
        await event.respond("Your basket is empty.")
        return

    # Simulate payment process
    total_amount = sum(item['price'] for item in basket)
    payment_link = f"http://yourpaymentgateway.com/pay?amount={total_amount}"
    users_collection.update_one(
        {'user_id': user_id},
        {'$set': {'basket': []}, '$push': {'orders': {'items': basket, 'total': total_amount}}}
    )
    await event.respond(f"Your order has been placed! Please visit the following link to make payment:\n{payment_link}")


# Admin handler to add a product
@client.on(events.NewMessage(pattern='/admin_add_product (.+)'))
async def admin_add_product(event):
    sender = await event.get_sender()
    if not is_admin(sender.username):
        await event.respond("You don't have permission to use this command.")
        return

    try:
        product_info = event.pattern_match.group(1).split(',')
        product_name, product_price = product_info[0].strip(), float(product_info[1].strip())
        products_collection.insert_one({'name': product_name, 'price': product_price})
        await event.respond(f"Product {product_name} added successfully.")
    except Exception as e:
        await event.respond(f"Error adding product: {e}")


# Admin handler to edit a product
@client.on(events.NewMessage(pattern='/admin_edit_product (.+)'))
async def admin_edit_product(event):
    sender = await event.get_sender()
    if not is_admin(sender.username):
        await event.respond("You don't have permission to use this command.")
        return

    try:
        product_info = event.pattern_match.group(1).split(',')
        old_product_name, new_product_name, new_product_price = product_info[0].strip(), product_info[1].strip(), float(
            product_info[2].strip())
        products_collection.update_one(
            {'name': old_product_name},
            {'$set': {'name': new_product_name, 'price': new_product_price}}
        )
        await event.respond(f"Product {old_product_name} updated successfully.")
    except Exception as e:
        await event.respond(f"Error editing product: {e}")


# Admin handler to remove a product
@client.on(events.NewMessage(pattern='/admin_remove_product (.+)'))
async def admin_remove_product(event):
    sender = await event.get_sender()
    if not is_admin(sender.username):
        await event.respond("You don't have permission to use this command.")
        return

    product_name = event.pattern_match.group(1).strip()
    result = products_collection.delete_one({'name': product_name})
    if result.deleted_count > 0:
        await event.respond(f"Product {product_name} removed successfully.")
    else:
        await event.respond(f"Product {product_name} not found.")


# Start the bot
logging.info('Starting...')
client.start()
logging.info("Bot Started Successfully!")
client.run_until_disconnected()
