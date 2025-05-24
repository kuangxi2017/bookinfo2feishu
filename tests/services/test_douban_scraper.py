# -*- coding: UTF-8 -*-
import unittest
from services.douban_scraper import DoubanScraper

class TestDoubanScraperHelpers(unittest.TestCase):

    def setUp(self):
        self.scraper = DoubanScraper()

    def test_process_numeric_fields(self):
        """Test the _process_numeric_fields helper method."""
        # Test case 1: Valid numeric strings
        book_info_valid = {'price': '123.45', 'pages': '300', 'score': '8.5'}
        self.scraper._process_numeric_fields(book_info_valid)
        self.assertEqual(book_info_valid['price'], 123.45)
        self.assertEqual(book_info_valid['pages'], 300)
        self.assertEqual(book_info_valid['score'], 8.5)

        # Test case 2: Invalid numeric strings
        book_info_invalid = {'price': 'abc', 'pages': 'xyz', 'score': 'N/A'}
        self.scraper._process_numeric_fields(book_info_invalid)
        self.assertEqual(book_info_invalid['price'], 0.0)
        self.assertEqual(book_info_invalid['pages'], 0)
        self.assertEqual(book_info_invalid['score'], 0.0)

        # Test case 3: Empty strings or missing keys
        book_info_empty = {'price': '', 'pages': '', 'score': ''}
        self.scraper._process_numeric_fields(book_info_empty)
        self.assertEqual(book_info_empty['price'], 0.0)
        self.assertEqual(book_info_empty['pages'], 0)
        self.assertEqual(book_info_empty['score'], 0.0)
        
        book_info_missing = {}
        self.scraper._process_numeric_fields(book_info_missing)
        self.assertEqual(book_info_missing.get('price'), 0.0) # Should add key with default
        self.assertEqual(book_info_missing.get('pages'), 0)   # Should add key with default
        self.assertEqual(book_info_missing.get('score'), 0.0) # Should add key with default

        # Test case 4: Mixed valid and invalid
        book_info_mixed = {'price': '50', 'pages': 'invalid', 'score': '7'}
        self.scraper._process_numeric_fields(book_info_mixed)
        self.assertEqual(book_info_mixed['price'], 50.0)
        self.assertEqual(book_info_mixed['pages'], 0)
        self.assertEqual(book_info_mixed['score'], 7.0)
        
        # Test case 5: Price with currency symbol (should extract number)
        book_info_currency = {'price': 'USD 75.99', 'pages': '250', 'score': '9.0'}
        self.scraper._process_numeric_fields(book_info_currency)
        self.assertEqual(book_info_currency['price'], 75.99)
        self.assertEqual(book_info_currency['pages'], 250)
        self.assertEqual(book_info_currency['score'], 9.0)

    def test_format_publish_date(self):
        """Test the _format_publish_date helper method."""
        # Test case 1: Full date YYYY-MM-DD
        self.assertEqual(self.scraper._format_publish_date("2021-05-15"), "2021-05-15")
        
        # Test case 2: YYYY-MM
        self.assertEqual(self.scraper._format_publish_date("2020-3"), "2020-03-01")
        self.assertEqual(self.scraper._format_publish_date("2020-12"), "2020-12-01")

        # Test case 3: YYYY.MM.DD and YYYY.MM
        self.assertEqual(self.scraper._format_publish_date("2019.07.20"), "2019-07-20")
        self.assertEqual(self.scraper._format_publish_date("2019.7"), "2019-07-01")
        
        # Test case 4: YYYY/MM/DD and YYYY/MM
        self.assertEqual(self.scraper._format_publish_date("2018/09/05"), "2018-09-05")
        self.assertEqual(self.scraper._format_publish_date("2018/9"), "2018-09-01")

        # Test case 5: YYYY年MM月DD日, YYYY年MM月, YYYY年
        self.assertEqual(self.scraper._format_publish_date("2017年01月10日"), "2017-01-10")
        self.assertEqual(self.scraper._format_publish_date("2017年1月"), "2017-01-01")
        self.assertEqual(self.scraper._format_publish_date("2016年"), "2016-01-01")

        # Test case 6: Only YYYY
        self.assertEqual(self.scraper._format_publish_date("2015"), "2015-01-01")

        # Test case 7: Empty or invalid string
        self.assertEqual(self.scraper._format_publish_date(""), "2022-01-01") # Default for empty
        self.assertEqual(self.scraper._format_publish_date("Invalid Date"), "2022-01-01") # Default for invalid
        self.assertEqual(self.scraper._format_publish_date(None), "2022-01-01") # Default for None
        
        # Test case 8: Whitespace
        self.assertEqual(self.scraper._format_publish_date(" 2023-04 "), "2023-04-01")
        self.assertEqual(self.scraper._format_publish_date("2023 - 04 - 20"), "2023-04-20")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
