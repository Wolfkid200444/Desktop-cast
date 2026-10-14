import json
import unittest
from unittest.mock import patch
from desktop_cast.workshop import parse_page, item_id, details

class WorkshopTests(unittest.TestCase):
    def test_nested_steam_results_and_app_filter(self):
        results={'current_page':2,'total_pages':7,'total_count':200,'results':[
            {'publishedfileid':'123','consumer_appid':3474900,'title':'Cat','file_size':'200'},
            {'publishedfileid':'456','consumer_appid':999,'title':'Other game'}]}
        nested={'queries':[{'state':{'data':results}}]}
        payload={'loaderData':[json.dumps(nested)]}
        html='<script type="application/json" id="valve-ssr-data">'+json.dumps(payload)+'</script>'
        parsed=parse_page(html)
        self.assertEqual(parsed['current_page'],2)
        self.assertEqual([i['id'] for i in parsed['results']],['123'])
        self.assertEqual(parsed['results'][0]['bytes'],200)

    def test_urls_are_restricted_to_steam(self):
        self.assertEqual(item_id('https://steamcommunity.com/sharedfiles/filedetails/?id=123'),'123')
        self.assertEqual(item_id('123'),'123')
        self.assertIsNone(item_id('https://example.com/?id=123'))
        self.assertIsNone(item_id('123; rm anything'))

    def test_reject_other_app_and_private_item(self):
        with patch('desktop_cast.workshop.request', return_value=json.dumps({'response':{'publishedfiledetails':[{'result':1,'consumer_app_id':999}]}}).encode()):
            with self.assertRaisesRegex(ValueError,'animaEngine'): details('123')
        with patch('desktop_cast.workshop.request', return_value=json.dumps({'response':{'publishedfiledetails':[{'result':9}]}}).encode()):
            with self.assertRaisesRegex(ValueError,'unavailable'): details('123')

    def test_unexpected_page_is_actionable(self):
        with self.assertRaisesRegex(ValueError,'unavailable'):parse_page('<html>Service unavailable</html>')

if __name__=='__main__':unittest.main()
