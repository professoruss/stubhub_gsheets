import base64
import json
import requests
requests.packages.urllib3.disable_warnings()
from prettytable import PrettyTable

auth_json   = json.loads(open('auth.json').read())
params_json = json.loads(open('params.json').read())

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
                         str(inventory_json['totalTickets'])])
    print event_table
    event_table = ''
    for sstats in s_stats:
        s_stats_table.add_row([str(sstats['sectionName']),
                               str(sstats['totalTickets']),
                               str(sstats['minTicketPriceWithCurrency']['amount']),
                               str(sstats['averageTicketPriceWithCurrency']['amount']),
                               str(sstats['maxTicketPriceWithCurrency']['amount'])])

    print s_stats_table.get_string(sortby='Section')
