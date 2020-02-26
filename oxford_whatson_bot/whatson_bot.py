from collections import defaultdict
from datetime import date, datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Location
from telegram.ext import Filters, Updater, CommandHandler, CallbackQueryHandler, MessageHandler
import requests
import re

from pprint import pprint


TOKEN='1026335942:AAFSQCT3iXs5exDNSJZ6JxPtOTFAT4IdjQ0'

SOURCE_URL = 'https://www.dailyinfo.co.uk'
SOURCE_URL_EVENT_TEMPLATE = SOURCE_URL + '%s'

# For example:
# https://www.dailyinfo.co.uk/whats-on-listings-3?selectedDate=20-02-17&sortBy=name&numListingsLoaded=0&selectedCategory=all&tagMatching    Style=any&requestId=1&offset=0&size=1000&paramVer=0
SOURCE_URL_TEMPL = SOURCE_URL + '/whats-on-listings-3?selectedDate=%s&sortBy=name&numListingsLoaded=0&selectedCategory=%s&tagMatchingStyle=any&requestId=1&offset=0&size=300&paramVer=0'

MENU_CMD = 'menu'
HELP_CMD = 'help'
LIST_EVENTS_CMD = 'whatson'
LIST_CATEGORIES_CMD = 'categories'
PRINT_DATE_CMD = 'date'

CHANGE_DATE_TO_YESTERDAY_CMD = 'yesterday'
CHANGE_DATE_TO_TODAY_CMD = 'today'
CHANGE_DATE_TO_TOMORROW_CMD = 'tomorrow'

REQUEST_DATE=date.today().strftime("%-y-%m-%d")

TITLE_MAX_SYMBOLS = 44

HIDDEN_CATEGORIES = set() #set(['Cinema', 'Family-friendly', 'Outside Oxfordshire', 'Worship'])

ALL_CATEGORIES = {
    'Cinema': 3,
    'Exhibitions': 4,
    'Family-friendly': 5,
    'Outside Oxfordshire': 15,
    'Worship': 13,
    'Classes, Courses & Workshops': 8,
    'Gigs & Comedy': 1,
    'Concerts': 6,
    'Dance': 11,
    'Festivals': 10,
    'Sports & Fitness': 9,
    'Meetings & Lectures': 7,
    'Nightlife': 12,
    'Theatre': 2,
    'Tours': 14
}

ALL_CATEGORIES_BY_IDS = {v: k for k, v in ALL_CATEGORIES.items()}

CATEGORIES_STAT = {
    'Cinema': True,
    'Exhibitions': True,
    'Family-friendly': True,
    'Outside Oxfordshire': True,
    'Worship': True,
    'Classes, Courses & Workshops': True,
    'Gigs & Comedy': True,
    'Concerts': True,
    'Dance': True,
    'Festivals': True,
    'Sports & Fitness': True,
    'Meetings & Lectures': True,
    'Nightlife': True,
    'Theatre': True,
    'Tours': True
}

MENU_TEXT = """
default date is today
/whatson, /categories -- show categories
/today -- set the date to today
/tomorrow -- set the date to tomorrow
/yesterday -- set the date to yesterday
/date <date> -- set the date to <date>, for example: /date 25 05 2020
"""


CURRENT_EVENTS = {}

def get_url():
    return SOURCE_URL

def get_data(category_id=None):
    events = defaultdict(list)

    json = requests.get(SOURCE_URL_TEMPL % (REQUEST_DATE, 'all' if not category_id else category_id)).json()
    print(SOURCE_URL_TEMPL % (REQUEST_DATE, 'all' if not category_id else category_id))
    for event in json['hits']['hits']:
       print(event)
       info = event.get('_source', {})
       category = info.get('columnName')
       if (category and category not in HIDDEN_CATEGORIES):
         events[category].append(info)

    print(events)
    return events

def cache_events(event_infos):
    global CURRENT_EVENTS
    CURRENT_EVENTS = {info.get('id'): info for info in event_infos}

def save_stat(cat_id, has_events):
    global CATEGORIES_STAT
    CATEGORIES_STAT[ALL_CATEGORIES_BY_IDS[cat_id]] = has_events

def change_date_to_(update, context):
    day, month, year = int(context.match[1]), int(context.match[2]), int(context.match[3])
    d = date(year, month, day)
    REQUEST_DATE = d.strftime("%-y-%m-%d")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Date has been changed to %s" % d.strftime("%d.%m.%Y"), parse_mode=ParseMode.HTML)

def print_request_date(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Date set to %s" % REQUEST_DATE, parse_mode=ParseMode.HTML)

def change_date_to_tomorrow(update, context):
    change_date(update, context, +1)

def change_date_to_today(update, context):
    change_date(update, context, 0)

def change_date_to_yesterday(update, context):
    change_date(update, context, -1)

def change_date(update, context, days):
    global REQUEST_DATE
    d = date.today() + timedelta(days=days)
    REQUEST_DATE = d.strftime("%-y-%m-%d")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Date has been changed to %s" % d.strftime("%d.%m.%Y"), parse_mode=ParseMode.HTML)

def make_text(events, one_category=False):
    text = ''
    for category, infos in events.items():
        category_text = '<b>===== %s =====</b>' % category
        titles_text = ''
        for i, info in enumerate(infos[:20 if one_category else 5]):
            event_code = info.get('id')
            titles_text += '\n<b>%s</b> %s /details_%s' % (
                info.get('timesAndPrices', [''])[0],
                info.get('nameNoHtml'),
                event_code
            )[:TITLE_MAX_SYMBOLS]
#            additional_text = '''\n        Time: %s\n        <a href="%s">website</a>''' % (info.get("timesAndPrices", [''])[0], info.get("web"))
#            titles_text += additional_text
        titles_text += '\n\n'

        text += category_text + titles_text

    if not one_category:
        text += '\n\n<b>Hidden categories:</b> ' + ', '.join(HIDDEN_CATEGORIES)

    return text

def make_text_as_buttons(events):
    keyboard = []
    for category, infos in events.items():
        category_text = '<b>%s</b>' % category
        for info in infos[:20]:
            keyboard.append([InlineKeyboardButton(info.get('nameNoHtml'), callback_data='name_click')])

    return InlineKeyboardMarkup(keyboard)

def make_event_details(event):
    info = []

    time_string, price_string = event.get('timesAndPrices', [None, None])
    info.append(['Time', time_string]) if time_string else None
    info.append(['Price', price_string]) if price_string else None
    description = event.get('description')
    info.append(['Description', description]) if description else None
    venue_name = event.get('venueName')
    info.append(['Where', venue_name]) if venue_name else None
    venue_address = event.get('venueAddress')
    info.append(['Address', venue_address.replace('\n', ' ')]) if venue_address else None
    site = event.get('web')
    info.append(['Site', site]) if site else None
    daily_info = event.get('url')
    info.append(['DailyInfo', '<a href="%s">%s</a>' % (SOURCE_URL_EVENT_TEMPLATE % daily_info, SOURCE_URL)]) if daily_info else None
    location = event.get('location')
    info.append(['Map', '<a href="https://www.google.com/maps?q=%s">Google maps</a>' % location]) if location else None

    return '\n'.join(['<b>%s</b> %s' % (key, value) for key, value in info])

def send_details(update, context):
  clean = context.match[1]
  event_id = int(clean)
  event = CURRENT_EVENTS.get(event_id)
  if event:
      text = make_event_details(event)
  else:
      text = "No details about this event"

#  location = Location(51.75158,-1.20078)

  context.bot.send_message(
      chat_id=update.effective_chat.id,
      text=text, parse_mode=ParseMode.HTML,
      reply_markup=make_event_menu_buttons(event_id, event.get('columnName')))
#      location=location)

#def send_map(update, context, event_id):
#  event = CURRENT_EVENTS.get(event_id)
#  if event:
#      text = make_event_details(event)
#  else:
#      text = "No details about this event"
#
#  lat, lon = [float(l) for l in event.get('location').split(',')]
#  context.bot.send_location(
#      chat_id=update.effective_chat.id,
#      latitude=lat,longitude=lon)


def make_category_buttons():
    global CATEGORIES_STAT
    keyboard = []
    line = []
    for i, (name, id_) in enumerate(ALL_CATEGORIES.items()):
        cat_stat = CATEGORIES_STAT.get(name)
        line.append(InlineKeyboardButton(name + (" (empty)" if not cat_stat else ''), callback_data=id_))
        # Grouping buttons by two
        if i % 2 != 0:
            keyboard.append(line)
            line = []
    return InlineKeyboardMarkup(keyboard)

def make_back_to_categories_button():
    keyboard = [[InlineKeyboardButton('Categories', callback_data='categories')]]
    return InlineKeyboardMarkup(keyboard)

def make_event_menu_buttons(event_id, category_name):
    keyboard = [[
        InlineKeyboardButton('Back to %s' % category_name, callback_data='send_category_%s' % ALL_CATEGORIES.get(category_name)),
        InlineKeyboardButton('Save the event', callback_data='save_event_%s' % event_id )]]
    return InlineKeyboardMarkup(keyboard)

def make_event_show_map_button(event_id):
    keyboard = [[
        InlineKeyboardButton('Show on the map', callback_data='show_map_%s' % event_id)
    ]]
    return InlineKeyboardMarkup(keyboard)

#def send_main_menu_buttons(update, context):
#    keyboard = [[
#        InlineKeyboardButton("What's on?", callback_data='send_categories'),
#        InlineKeyboardButton('Set date to today', callback_data='today'),
#    ]]
#    context.bot.send_message(chat_id=update.effective_chat.id, text="Menu", reply_markup=InlineKeyboardMarkup(keyboard))

def send_main_menu(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=MENU_TEXT, reply_markup=make_back_to_categories_button())

#def make_event_menu_buttons(event_id):
#    keyboard = [[
#        InlineKeyboardButton('Categories', callback_data='categories'),
#        InlineKeyboardButton('Send map', callback_data='map_%s' % event_id)]]
#    return InlineKeyboardMarkup(keyboard)

def list_events(update, context):
    events = get_data()
#    update.message.reply_photo(photo=url, reply_markup=make_likes_markup())
    context.bot.send_message(chat_id=update.effective_chat.id, text=make_text(events), parse_mode=ParseMode.HTML, reply_markup=make_back_to_categories_button())

def list_categories(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Filter by category:', reply_markup=make_category_buttons())

def menu(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Menu:', reply_markup=make_menu_buttons())

def click_category(update, context):
    query = update.callback_query
    click_data = query.data
    if click_data == 'categories':
        query.edit_message_text('Filter by category:', reply_markup=make_category_buttons())
    elif click_data.startswith('save_event'):
        event_id = int(click_data.split('_')[2])
        event = CURRENT_EVENTS.get(event_id)
        query.edit_message_text(text = make_event_details(event), parse_mode=ParseMode.HTML, reply_markup=make_event_show_map_button(event_id))
    elif click_data.startswith('send_category'):
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.effective_message.message_id - 1)
    elif click_data == 'today':
        change_date_to_today(update, context)
    elif click_data == 'send_categories':
        list_categories(update, context)
    elif click_data.startswith('show_map'):
        event_id = int(click_data.split('_')[2])
        event = CURRENT_EVENTS.get(event_id)
        lat, lon = [float(l) for l in event.get('location').split(',')]
        context.bot.send_location(
            chat_id=update.effective_chat.id,
            latitude=lat,longitude=lon)
#        send_main_menu(update, context)
    else:
        events = get_data(click_data)
        save_stat(int(click_data), bool(events))
        if not events:
            query.edit_message_text(text='Filter by category:', reply_markup=make_category_buttons())
        else:
            cache_events(list(events.values())[0])
            query.edit_message_text(text=make_text(events, click_data), parse_mode=ParseMode.HTML, reply_markup=make_back_to_categories_button())
    query.answer()
#    context.bot.send_message(chat_id=update.effective_chat.id, text='test')

def error(update, context):
    print(context.error)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler(CHANGE_DATE_TO_YESTERDAY_CMD, change_date_to_yesterday))
    dp.add_handler(CommandHandler(CHANGE_DATE_TO_TOMORROW_CMD, change_date_to_tomorrow))
    dp.add_handler(CommandHandler(CHANGE_DATE_TO_TODAY_CMD, change_date_to_today))
    dp.add_handler(MessageHandler(Filters.regex('^/date ([\d]+)[\s/\.]+([\d]+)[\s/\.]+([\d]+)$'), change_date_to_))
    dp.add_handler(CommandHandler(PRINT_DATE_CMD, print_request_date))
    dp.add_handler(CommandHandler(LIST_EVENTS_CMD, list_categories))
    dp.add_handler(CommandHandler(LIST_CATEGORIES_CMD, list_categories))
    dp.add_handler(CommandHandler(MENU_CMD, send_main_menu))
    dp.add_handler(CommandHandler(HELP_CMD, send_main_menu))
    dp.add_handler(MessageHandler(Filters.regex('^/details_([\d]+)(?:@oxford_whatson_bot)?$'), send_details))

    updater.dispatcher.add_handler(CallbackQueryHandler(click_category))

    updater.dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()
                            
if __name__ == '__main__':
    main()
