import base64
import json
import requests
requests.packages.urllib3.disable_warnings()
from prettytable import PrettyTable
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from re import sub
from decimal import Decimal

# read json settings
auth_json   = json.loads(open('auth.json').read())
params_json = json.loads(open('params.json').read())

# stubhub headers
headers = {
    'Content-Type'  : 'application/x-www-form-urlencoded',
    'Authorization' : 'Bearer '+ auth_json['auth_bearer']
}

sh_update_headers = {
    'Content-Type'  : 'application/json',
    'Authorization' : 'Bearer '+ auth_json['auth_bearer']
}

# stubhub URLS and vars
events_url    = 'https://api.stubhub.com/search/catalog/events/v3'
events_qs     = params_json['event_qs']
events        = requests.get(events_url, params=events_qs, headers=headers)
events_json   = json.loads(events.text)
sorted_events = sorted(events_json['events'], key=lambda d: d['id'])
inventory_url = 'https://api.stubhub.com/search/inventory/v2'
listings_url  = 'https://api.stubhub.com/accountmanagement/listings/v1/seller/%s' % auth_json['stubhub_userid']

# use creds to create a client to interact with the Google Drive API
scope  = ['https://spreadsheets.google.com/feeds']
creds  = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)

# Find a workbook by name and open the first sheet
# Make sure you use the right name here.
sheet = client.open(params_json['g_spreadsheet']).sheet1

# Find google sheet column to check if we need to update our price
find_update_col = sheet.find('Update?')
update_col      = find_update_col.col
# Get google sheet row count so we can iterate over it
row_count = sheet.row_count
# Get the column for the price we have listed
find_listed_col = sheet.find('Listed')
listed_col      = find_listed_col.col
# find the stubhub event id
find_event_id = sheet.find('SH event_id')
event_id_col  = find_event_id.col
# Iterate over all the rows
curr_row = 1
while curr_row <= row_count:
    # only act on rows that have Update? set to Y
    if sheet.cell(curr_row, update_col).value == 'Y':
        # get the price that we want to set
        update_price = sheet.cell(curr_row, listed_col).value
        # make our update price a float
        update_price2 = Decimal(sub(r'[^\d.]', '', update_price))
        event_id = sheet.cell(curr_row, event_id_col).value
        print("Need to update price to " + str(update_price) + " for event id " + str(event_id))
        # set the filter for the eventid so we can get the listing id
        listings_eventid = 'filters=EVENT:%s' % event_id
        my_listings = requests.get(listings_url, params=listings_eventid, headers=headers)
        my_listings_json = json.loads(my_listings.text)
        print(my_listings.status_code)
        # set the payload to update the listing
        update_json='{"listing": { "pricePerTicket": "%s" } }' % update_price2
        # update listing url with listingid we got from the last call
        update_listings_url = 'https://api.stubhub.com/inventory/listings/v1/%s' % my_listings_json['listings']['listing'][0]['id']
        update_listing = requests.put(update_listings_url, headers=sh_update_headers, data=update_json)
        update_listing.raw
        print(update_listing.status_code)
        # reset the Update? to N so we don't keep trying to update prices
        sheet.update_cell(curr_row, update_col, 'N')

    # increment the current row
    curr_row += 1

for i in sorted_events:
    eventid = 'eventid=' + str(i['id']) + '&sectionstats=true&sectionidlist=' + params_json['sectionidlist']
    inventory = requests.get(inventory_url, params=eventid, headers=headers)
    inventory_json = json.loads(inventory.text)
    eventid2 = 'eventid=' + str(i['id']) + '&sectionstats=true'
    inventory2 = requests.get(inventory_url, params=eventid2, headers=headers)
    inventory2_json = json.loads(inventory2.text)
    s_stats = inventory_json['section_stats']
    s_stats_table = PrettyTable(['Section',
                                 'Remaining',
                                 'Min price',
                                 'Avg price',
                                 'Max price'])
    event_table = PrettyTable(['EventID',
                               'Event Time',
                               'Opponent',
                               'Tickets Remaining'])
    event_table.add_row([str(i['id']),
                         str(i['eventDateLocal']),
                         str(i['performersCollection'][1]['name']),
                         str(inventory2_json['totalTickets'])])
    print event_table
    event_table = ''
    for sstats in s_stats:
        s_stats_table.add_row([str(sstats['sectionName']),
                               str(sstats['totalTickets']),
                               str(sstats['minTicketPriceWithCurrency']['amount']),
                               str(sstats['averageTicketPriceWithCurrency']['amount']),
                               str(sstats['maxTicketPriceWithCurrency']['amount'])])
        find_event_id = sheet.find(str(i['id']))
        row_find = find_event_id.row
        find_section_id = sheet.find(str(sstats['sectionId']))
        col_find = find_section_id.col
        e_t_remain = sheet.find('event_tix_remain')
        e_t_r_col_find = e_t_remain.col
        event_link_url_1 = 'https://www.stubhub.com/event/'
        event_link_url_2 = '?sort=price+asc&sid='
        sheet.update_cell(row_find, e_t_r_col_find, inventory2_json['totalTickets'])
        sheet.update_cell(row_find, col_find, '=HYPERLINK("' + event_link_url_1 + str(i['id']) + event_link_url_2 + find_section_id.value + '","' + str(sstats['minTicketPriceWithCurrency']['amount']) + '/' + str(sstats['averageTicketPriceWithCurrency']['amount']) + '/' + str(sstats['maxTicketPriceWithCurrency']['amount']) + '")' )

    print s_stats_table.get_string(sortby='Section')
