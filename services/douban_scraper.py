# -*- coding: UTF-8 -*-
# 豆瓣爬虫服务

from typing import Optional
import requests
import re
from lxml import etree
from config import DoubanConfig
from utils.logger import logger

class DoubanScraper:
    """豆瓣爬虫类"""
    def __init__(self):
        self.headers = {
            'User-Agent': DoubanConfig.USER_AGENT
        }
    
    def get_book_info(self, isbn: str) -> Optional[dict]:
        """
        获取指定ISBN号的豆瓣图书信息。

        Args:
            isbn: 图书的ISBN号。

        Returns:
            一个包含图书信息的字典，如果获取失败或图书不存在则返回None。
        """
        url = f"{DoubanConfig.BASE_URL}{isbn}"
        logger.info(f"Attempting to scrape Douban for ISBN: {isbn} at URL: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=DoubanConfig.REQUEST_TIMEOUT)
            response.raise_for_status()  # 检查请求是否成功
            html = etree.HTML(response.text)
            
            # 提取书名 - XPath: //*[@id='mainpic']/a/@title (Title from main picture link)
            book_name_element = html.xpath("//*[@id='mainpic']/a/@title")
            book_name = ''.join(book_name_element).strip()
            if not book_name:
                logger.info(f"豆瓣页面 {url} 未找到书名信息，可能无该图书信息，跳过录入。")
                return None
                
            # 提取图书信息
            book_info = {
                'book_name': book_name,
                # XPath: //*[@id='mainpic']/a/img/@src (Cover image source from main picture link)
                'book_img': ''.join(html.xpath("//*[@id='mainpic']/a/img/@src")).strip(),
                'url': response.url
            }
            
            # 提取作者信息 - Primary XPath: //*[@id='info']/span[1]/a/text()
            # Fallback XPath for cases where "作者:" label is used: u'//span[text()="作者:"]/../../a[1]/text()'
            author_name_elements = html.xpath("//*[@id='info']/span[1]/a/text()")
            author_name_str = ''.join(author_name_elements).strip()
            if not author_name_str:
                author_name_elements = html.xpath(u'//span[text()="作者:"]/following-sibling::a[1]/text()') # Corrected fallback
                author_name_str = re.sub(r'[\s\n]', "", ''.join(author_name_elements)).strip()
            book_info['author_name'] = author_name_str
            
            # 提取出版社信息 - XPath: u'//span[./text()="出版社:"]/following::text()[1]' (Text immediately following "出版社:" label)
           
            press = html.xpath(u'//span[./text()="出版社:"]/following::text()[2]')
            if not press or ''.join(press).lstrip() == "":
                press = html.xpath(u'//span[./text()="出版社:"]/following::text()[1]')
            book_info['press'] = ''.join(press).strip()
            
            # 提取其他基本信息
            # XPath for "出版年:": u'//span[./text()="出版年:"]/following::text()[1]'
            book_info['press_year'] = ''.join(html.xpath(u'//span[./text()="出版年:"]/following::text()[1]')).strip()
            # XPath for "页数:": u'//span[./text()="页数:"]/following::text()[1]'
            book_info['pages'] = ''.join(html.xpath(u'//span[./text()="页数:"]/following::text()[1]')).strip()
            # XPath for "定价:": u'//span[./text()="定价:"]/following::text()[1]'
            book_info['price'] = ''.join(html.xpath(u'//span[./text()="定价:"]/following::text()[1]')).strip()
            # XPath for "ISBN:": u'//span[./text()="ISBN:"]/following::text()[1]'
            book_info['ISBN'] = ''.join(html.xpath(u'//span[./text()="ISBN:"]/following::text()[1]')).strip()
            
            # Fields with default "无" if not found or empty
            # XPath for "出品方:": u'//span[./text()="出品方:"]/following-sibling::a[1]/text()' or u'//span[./text()="出品方:"]/following::text()[1]'
            brand_elements = html.xpath(u'//span[./text()="出品方:"]/following-sibling::a[1]/text()')
            book_info['brand'] = ''.join(brand_elements).strip() or ''.join(html.xpath(u'//span[./text()="出品方:"]/following::text()[1]')).strip() or "无"
            # XPath for "丛书:": u'//span[./text()="丛书:"]/following-sibling::a[1]/text()'
            series_elements = html.xpath(u'//span[./text()="丛书:"]/following-sibling::a[1]/text()')
            book_info['series'] = ''.join(series_elements).strip() or "无"
             # XPath for "装帧:": u'//span[./text()="装帧:"]/following::text()[1]'
            book_info['design'] = ''.join(html.xpath(u'//span[./text()="装帧:"]/following::text()[1]')).strip() or "无"
            # XPath for "豆瓣评分:": //*[@id='interest_sectl']/div/div[2]/strong/text()
            book_info['score'] = ''.join(html.xpath("//*[@id='interest_sectl']/div/div[2]/strong/text()")).strip()
            # XPath for "译者:": u'//span[./text()=" 译者"]/following-sibling::a[1]/text()' or u'//span[text()="译者:"]/following-sibling::a[1]/text()'
            translator_elements = html.xpath(u'//span[contains(text(),"译者")]/following-sibling::a[1]/text()')
            book_info['translator'] = ''.join(translator_elements).strip()
            
            # 处理数值类型 (pages, price, score)
            self._process_numeric_fields(book_info)
            
            # 处理出版日期
            book_info['publish_date'] = self._format_publish_date(book_info.get('press_year', ''))
            
            logger.info(f"Successfully scraped book: {book_info.get('book_name', 'Unknown Title')} (ISBN: {isbn})")
            return book_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取豆瓣信息失败 (ISBN: {isbn}, URL: {url}): {e}")
            return None
            
    def _process_numeric_fields(self, book_info: dict) -> None:
        """
        处理字典中图书信息的数值类型字段（价格, 页数, 评分）。
        如果字段不存在或无法转换，则赋予默认值。

        Args:
            book_info: 包含图书信息的字典。
        """
        # 处理价格
        price_str = book_info.get('price', '')
        if price_str:
            try:
                price_match = re.search(r'\d+\.?\d*', price_str)
                book_info['price'] = float(price_match.group(0)) if price_match else 0.0
            except (ValueError, TypeError, AttributeError):
                book_info['price'] = 0.0
        else:
            book_info['price'] = 0.0
            
        # 处理页数
        pages_str = book_info.get('pages', '')
        if pages_str:
            try:
                book_info['pages'] = int(re.search(r'\d+', pages_str).group(0)) if re.search(r'\d+', pages_str) else 0
            except (ValueError, TypeError, AttributeError):
                book_info['pages'] = 0
        else:
            book_info['pages'] = 0
            
        # 处理评分
        score_str = book_info.get('score', '')
        if score_str:
            try:
                book_info['score'] = float(score_str)
            except (ValueError, TypeError):
                book_info['score'] = 0.0
        else:
            book_info['score'] = 0.0
    
    def _format_publish_date(self, press_year: str) -> str:
        """
        格式化出版日期字符串。
        尝试从"YYYY-MM-DD", "YYYY-MM", "YYYY年MM月", "YYYY年"等格式中提取并规范化为"YYYY-MM-DD"。
        如果无法解析，则默认为 "YYYY-01-01" 或 "2022-01-01" (作为最终回退)。

        Args:
            press_year: 包含出版年份信息的字符串。

        Returns:
            格式化后的日期字符串 "YYYY-MM-DD"。
        """
        if not press_year:
            return "2022-01-01" # Default if no press_year provided
        
        press_year = press_year.strip()
        
        # Regex for YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD
        match = re.search(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", press_year)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # Regex for YYYY-MM, YYYY.MM, YYYY/MM, YYYY年MM月
        match = re.search(r"(\d{4})[-./年](\d{1,2})月?", press_year)
        if match:
            year, month = match.groups()
            return f"{year}-{month.zfill(2)}-01" # Default day to 01

        # Regex for YYYY年 or just YYYY
        match = re.search(r"(\d{4})年?", press_year)
        if match:
            year = match.group(1)
            return f"{year}-01-01" # Default month and day to 01
            
        # Fallback if no pattern matches, though the YYYY pattern should catch most years
        return "2022-01-01"