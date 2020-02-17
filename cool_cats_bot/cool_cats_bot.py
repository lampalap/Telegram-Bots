from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
import requests
import re

from pprint import pprint


TOKEN='1002397911:AAGE-5oK1NOE78may5VNeXRdAw9DXslFsOI'
REPLIES = {
    'like': "👍",
    'dislike': "👎"
}

def get_url():
    contents = requests.get('https://api.thecatapi.com/v1/images/search').json()[0]
    return contents['url']

def make_likes_markup():
    keyboard = [[InlineKeyboardButton(REPLIES['like'], callback_data='like'),
                 InlineKeyboardButton(REPLIES['dislike'], callback_data='dislike')]]
    return InlineKeyboardMarkup(keyboard)

def meow(update, context):
    url = get_url()
#    update.message.reply_photo(photo=url, reply_markup=make_likes_markup())
    update.message.reply_photo(photo=url)

def button(update, context):
    query = update.callback_query
    state = query.data
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Change my response from {}".format(REPLIES[state]), callback_data='rethink')]]) if state in REPLIES else make_likes_markup()
    query.edit_message_reply_markup(markup)
    query.answer()

def error(update, context):
    print(context.error)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('meow', meow))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    updater.dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()
                            
if __name__ == '__main__':
    main()
