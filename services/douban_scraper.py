# -*- coding: UTF-8 -*-
# 豆瓣爬虫服务

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
    
    def get_book_info(self, isbn):
        """获取豆瓣图书信息"""
        url = f"{DoubanConfig.BASE_URL}{isbn}"
        try:
            response = requests.get(url, headers=self.headers, timeout=DoubanConfig.REQUEST_TIMEOUT)
            response.raise_for_status()  # 检查请求是否成功
            html = etree.HTML(response.text)
            
            # 提取书名
            book_name = html.xpath("//*[@id='mainpic']/a/@title")
            if not book_name or ''.join(book_name) == '':
                logger.info(f"{url}. 豆瓣无该图书信息，跳过录入。")
                return None
                
            # 提取图书信息
            book_info = {
                'book_name': ''.join(book_name),
                'book_img': ''.join(html.xpath("//*[@id='mainpic']/a/img/@src")),
                'url': response.url
            }
            
            # 提取作者信息
            author_name = html.xpath("//*[@id='info']/span[1]/a/text()")
            if not author_name or ''.join(author_name) == "":
                author_name = html.xpath(u'//span[text()="作者:"]/../../a[1]/text()')
                author_name = re.sub(r'[\s\n]', "", ''.join(author_name))
            book_info['author_name'] = ''.join(author_name).lstrip()
            
            # 提取出版社信息
            press = html.xpath(u'//span[./text()="出版社:"]/following::text()[2]')
            if not press or ''.join(press).lstrip() == "":
                press = html.xpath(u'//span[./text()="出版社:"]/following::text()[1]')
            book_info['press'] = ''.join(press).strip()
            
            # 提取其他基本信息
            book_info['press_year'] = ''.join(html.xpath(u'//span[./text()="出版年:"]/following::text()[1]')).lstrip()
            book_info['pages'] = ''.join(html.xpath(u'//span[./text()="页数:"]/following::text()[1]'))
            book_info['price'] = ''.join(html.xpath(u'//span[./text()="定价:"]/following::text()[1]')).lstrip()
            book_info['ISBN'] = ''.join(html.xpath(u'//span[./text()="ISBN:"]/following::text()[1]')).lstrip()
            book_info['brand'] = ''.join(html.xpath(u'//span[./text()="出品方:"]/following::text()[2]')).lstrip() or "无"
            book_info['series'] = ''.join(html.xpath(u'//span[./text()="丛书:"]/following::text()[2]')).lstrip() or "无"
            book_info['design'] = ''.join(html.xpath(u'//span[./text()="装帧:"]/following::text()[1]')).lstrip() or "无"
            book_info['score'] = ''.join(html.xpath("//*[@id='interest_sectl']/div/div[2]/strong/text()")).lstrip()
            book_info['translator'] = ''.join(html.xpath(u'//span[./text()=" 译者"]/following::text()[2]')).lstrip()
            
            # 处理数值类型
            self._process_numeric_fields(book_info)
            
            # 处理出版日期
            book_info['publish_date'] = self._format_publish_date(book_info['press_year'])
            
            return book_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取豆瓣信息失败: {e}")
            return None
    
    def _process_numeric_fields(self, book_info):
        """处理数值类型的字段"""
        # 处理价格
        if book_info['price']:
            try:
                price_match = re.search(r'\d+\.?\d*', book_info['price'], re.I)
                if price_match:
                    book_info['price'] = float(price_match.group(0))
                else:
                    book_info['price'] = 0.0
            except (ValueError, TypeError):
                book_info['price'] = 0.0
        else:
            book_info['price'] = 0.0
            
        # 处理页数
        if book_info['pages']:
            try:
                book_info['pages'] = int(book_info['pages'])
            except (ValueError, TypeError):
                book_info['pages'] = 0
        else:
            book_info['pages'] = 0
            
        # 处理评分
        if book_info['score']:
            try:
                book_info['score'] = float(book_info['score'])
            except (ValueError, TypeError):
                book_info['score'] = 0.0
        else:
            book_info['score'] = 0.0
    
    def _format_publish_date(self, press_year):
        """格式化出版日期"""
        if not press_year:
            return "2022-01-01"
            
        publish_date_list = press_year.split('-')
        if len(publish_date_list) >= 2:
            return f"{publish_date_list[0]}-{publish_date_list[1].zfill(2)}-01"
        elif len(publish_date_list) == 1 and publish_date_list[0]:
            return f"{publish_date_list[0]}-01-01"
        else:
            return "2022-01-01"