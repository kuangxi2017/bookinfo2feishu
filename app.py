# -*- coding: UTF-8 -*-
# 主应用文件

import json
import os
import sys
from pathlib import Path

# 确保项目根目录在Python路径中
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, render_template
from services.douban_scraper import DoubanScraper
from services.feishu_api import FeishuAPI
from typing import Optional, Dict, Any
from app_config import AppConfig
from utils.logger import logger

app = Flask(__name__)

# 初始化应用配置
AppConfig.initialize()

# 初始化服务
douban_scraper = DoubanScraper()
feishu_api = FeishuAPI()

def _prepare_feishu_book_data(book_info: dict, image_token: Optional[str] = None) -> Dict[str, Any]:
    """
    根据豆瓣图书信息和可选的图片token准备飞书API所需的数据格式。
    """
    fields_data: Dict[str, Any] = {
        "书名": book_info.get('book_name'),
        "作者": book_info.get('author_name'),
        "出版社": book_info.get('press'),
        "页数": book_info.get('pages'),
        "ISBN": book_info.get('ISBN'),
        "版权方": book_info.get('brand'),
        "豆瓣评分": book_info.get('score'),
        "豆瓣链接": {"link": book_info.get('url')},
    }

    # 添加译者信息（如果有）
    if book_info.get('translator'):
        fields_data["译者"] = book_info['translator']
    
    # 添加封面图片（如果有 image_token）
    if image_token:
        fields_data["封面"] = [{"file_token": image_token}]
        
    return {"fields": fields_data}

@app.route('/isbn', methods=['GET'])
def process_isbn():
    """处理ISBN请求，获取图书信息并同步到飞书"""
    isbn = request.args.get('isbn')
    if not isbn:
        logger.warning("请求缺少ISBN参数")
        return jsonify({"code": 400, "message": "缺少ISBN参数"})
    
    logger.info(f"收到ISBN请求: {isbn}")

    # 1. 从豆瓣获取图书信息
    book_info = douban_scraper.get_book_info(isbn)
    if not book_info:
        logger.warning(f"未找到ISBN为 {isbn} 的图书信息")
        return jsonify({"code": 404, "message": "未找到图书信息"})

    # 2. 查询飞书中是否已存在该图书
    try:
        record_id = feishu_api.search_book_by_isbn(isbn)
    except Exception as e:
        logger.error(f"查询飞书记录失败 (ISBN: {isbn}): {e}")
        return jsonify({"code": 500, "message": "查询飞书记录失败"})

    if record_id:
        # 3. 更新现有记录
        logger.info(f"ISBN {isbn} 已存在于飞书，记录ID: {record_id}，开始更新信息...")
        # 对于更新操作，通常不更新封面，所以不传递 image_token
        feishu_data = _prepare_feishu_book_data(book_info) 
        
        try:
            success = feishu_api.update_book(record_id, feishu_data)
            if success:
                logger.info(f"成功更新图书: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 200, "message": "图书信息更新成功", "book_info": book_info})
            else:
                logger.error(f"更新飞书图书记录失败: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 500, "message": "更新飞书图书记录失败"})
        except Exception as e:
            logger.error(f"更新飞书图书记录时发生异常 (ISBN: {isbn}): {e}")
            return jsonify({"code": 500, "message": "更新飞书记录时发生错误"})

    else:
        # 4. 创建新记录
        logger.info(f"ISBN {isbn} 在飞书中不存在，开始创建新记录...")
        image_token = None
        if book_info.get('book_img'):
            try:
                logger.info(f"开始为ISBN {isbn} 上传封面: {book_info['book_img']}")
                image_token = feishu_api.upload_image(book_info['book_img'])
                if image_token:
                    logger.info(f"封面上传成功 for ISBN {isbn}, image_token: {image_token}")
                    book_info['image_token'] = image_token # Store for response, if needed
                else:
                    logger.warning(f"上传封面失败或未返回image_token for ISBN {isbn}")
            except Exception as e:
                logger.error(f"上传封面图片失败 for ISBN {isbn}: {e}")
                # 根据需求决定是否因封面上传失败而中止。目前选择继续，但不带封面。

        feishu_data = _prepare_feishu_book_data(book_info, image_token=image_token)
        
        try:
            success = feishu_api.create_book(feishu_data)
            if success:
                logger.info(f"成功添加图书到飞书: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 201, "message": "图书添加成功", "book_info": book_info})
            else:
                logger.error(f"添加图书到飞书失败: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 500, "message": "添加图书到飞书失败"})
        except Exception as e:
            logger.error(f"添加飞书图书记录时发生异常 (ISBN: {isbn}): {e}")
            return jsonify({"code": 500, "message": "添加飞书记录时发生错误"})

@app.route('/', methods=['GET'])
def index():
    """渲染首页"""
    return render_template('index.html')

@app.route('/config', methods=['GET', 'POST'])
def handle_config():
    """处理飞书API配置的获取和保存"""
    if request.method == 'GET':
        try:
            # 获取当前配置
            config = AppConfig.get_feishu_config()
            
            # 为了安全，只返回配置是否已设置，而不返回具体值
            sanitized_config = {
                "app_id": bool(config.get("FEISHU_APP_ID")),
                "app_secret": bool(config.get("FEISHU_APP_SECRET")),
                "app_token": bool(config.get("FEISHU_APP_TOKEN")),
                "table_id": bool(config.get("FEISHU_TABLE_ID")),
                "view_id": bool(config.get("FEISHU_VIEW_ID"))
            }
            
            return jsonify({
                "code": 200, 
                "message": "获取配置成功", 
                "config": sanitized_config
            })
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return jsonify({
                "code": 500, 
                "message": f"获取配置失败: {str(e)}"
            }), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"code": 400, "message": "缺少配置数据"}), 400

            # 验证必要的配置项
            required_fields = ["app_id", "app_secret", "app_token", "table_id"]
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        "code": 400, 
                        "message": f"缺少必要的配置项: {field}"
                    }), 400

            # 转换为配置格式
            config_data = {
                "FEISHU_APP_ID": data.get("app_id"),
                "FEISHU_APP_SECRET": data.get("app_secret"),
                "FEISHU_APP_TOKEN": data.get("app_token"),
                "FEISHU_TABLE_ID": data.get("table_id"),
                "FEISHU_VIEW_ID": data.get("view_id", "")  # 可选
            }
            
            # 更新配置
            if AppConfig.update_feishu_config(config_data):
                # 重新初始化 FeishuAPI 以应用新配置
                global feishu_api
                feishu_api = FeishuAPI()
                
                logger.info(f"飞书配置已更新: AppID: {data.get('app_id')}, TableID: {data.get('table_id')}")
                return jsonify({"code": 200, "message": "配置保存成功"})
            else:
                return jsonify({"code": 500, "message": "保存配置失败，请检查日志"}), 500
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return jsonify({"code": 500, "message": f"保存配置失败: {str(e)}"}), 500

@app.route('/feishu_fields', methods=['GET'])
def get_feishu_fields():
    """获取飞书多维表格的表头字段"""
    try:
        fields = feishu_api.get_table_fields()
        if fields:
            return jsonify({"code": 200, "message": "获取表头字段成功", "fields": fields})
        else:
            return jsonify({"code": 404, "message": "未能获取表头字段，请检查配置或API权限"}), 404
    except Exception as e:
        logger.error(f"获取表头字段失败: {e}")
        return jsonify({"code": 500, "message": f"获取表头字段失败: {str(e)}"}), 500


if __name__ == '__main__':
    # AppConfig.initialize() is called earlier, which ensures directories exist.
    # No need to manually create log_dir here again.
    
    # 启动Flask应用
    app.run(
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        debug=AppConfig.DEBUG
    )