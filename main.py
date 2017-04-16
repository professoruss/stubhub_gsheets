import base64
import json
import requests
requests.packages.urllib3.disable_warnings()
from prettytable import PrettyTable
import gspread
from oauth2client.service_account import ServiceAccountCredentials

auth_json   = json.loads(open('auth.json').read())
params_json = json.loads(open('params.json').read())

# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)

# Find a workbook by name and open the first sheet
# Make sure you use the right name here.
sheet = client.open(params_json['g_spreadsheet']).sheet1

headers = {
        'Content-Type':'application/x-www-form-urlencoded',
        'Authorization':'Bearer '+ auth_json['auth_bearer']
        }

events_url = 'https://api.stubhub.com/search/catalog/events/v3'
events_qs = params_json['event_qs']
events = requests.get(events_url, params=events_qs, headers=headers) #, data=body)
events_json = json.loads(events.text)

inventory_url = 'https://api.stubhub.com/search/inventory/v2'

for i in events_json['events']:
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
        sheet.update_cell(row_find, 18, inventory2_json['totalTickets'])
        sheet.update_cell(row_find, col_find, str(sstats['minTicketPriceWithCurrency']['amount']) + '/' + str(sstats['averageTicketPriceWithCurrency']['amount']) + '/' + str(sstats['maxTicketPriceWithCurrency']['amount']))

    print s_stats_table.get_string(sortby='Section')
