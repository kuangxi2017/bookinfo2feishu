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

def _prepare_feishu_book_data(
    book_info: dict, 
    douban_to_feishu_header_mappings: dict, # 例如: {"book_name": "书名", "author_name": "作者"}
    image_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    根据豆瓣图书信息和用户选择的映射关系（豆瓣字段名 -> 飞书表头字段名）准备数据。
    注意：此函数返回的 "fields" 字典的键是飞书的 *表头字段名*。
    调用方在将此数据发送给飞书API之前，需要将这些表头字段名转换为对应的飞书字段ID。
    """
    fields_data_with_headers: Dict[str, Any] = {}

    for douban_field_name, feishu_header_name in douban_to_feishu_header_mappings.items():
        value_to_set = None # 初始化为None，确保只有有效值才被添加

        if douban_field_name == 'book_name':
            value_to_set = book_info.get('book_name')
        elif douban_field_name == 'author_name':
            value_to_set = book_info.get('author_name')
        elif douban_field_name == 'press':
            value_to_set = book_info.get('press')
        elif douban_field_name == 'pages':
            pages_val = book_info.get('pages')
            if pages_val is not None: # 仅当 pages_val 不是 None 时尝试转换
                try:
                    value_to_set = int(pages_val)
                except (ValueError, TypeError):
                    logger.warning(f"无法将页数 '{pages_val}' 转换为整数 (ISBN: {book_info.get('ISBN')}).")
            # 如果 pages_val 是 None, value_to_set 保持 None
        elif douban_field_name == 'ISBN':
            value_to_set = book_info.get('ISBN')
        elif douban_field_name == 'brand': # 出品方
            value_to_set = book_info.get('brand')
        elif douban_field_name == 'score': # 评分
            score_val = book_info.get('score')
            if score_val is not None: # 仅当 score_val 不是 None 时尝试转换
                try:
                    value_to_set = float(score_val)
                except (ValueError, TypeError):
                    logger.warning(f"无法将评分 '{score_val}' 转换为数字 (ISBN: {book_info.get('ISBN')}).")
            # 如果 score_val 是 None, value_to_set 保持 None
        elif douban_field_name == 'url': # 链接
            link_url = book_info.get('url')
            if link_url: # 仅当 link_url 有值时设置
                value_to_set = {"link": link_url}
        elif douban_field_name == 'translator': # 译者
            translator_val = book_info.get('translator')
            if translator_val: # 仅当 translator_val 有值时设置 (处理 None 或空字符串)
                value_to_set = translator_val
        elif douban_field_name == 'image_token' and image_token: # 假设 'image_token' 是 douban_to_feishu_header_mappings 中的一个键
            value_to_set = [{"file_token": image_token}]
        # 可以添加一个通用回退，但不推荐，因为特定类型处理更好
        # elif douban_field_name in book_info:
        #     value_to_set = book_info.get(douban_field_name)

        # 仅当确定了有效值时才添加到字典中
        # 这避免了发送空字段，除非明确将 value_to_set 设置为 "" 或 {} 等
        if value_to_set is not None:
            fields_data_with_headers[feishu_header_name] = value_to_set

    return {"fields": fields_data_with_headers}

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
        # 传递空的mappings，让_prepare_feishu_book_data处理所有可识别字段
        feishu_data = _prepare_feishu_book_data(book_info, mappings={}, image_token=image_token_val)
        logger.debug(f"Prepared Feishu data for ISBN update: {feishu_data}")
        
        try:
            record_id = feishu_api.create_book(feishu_data)
            if record_id: # 修复：检查 record_id 是否为真 (非None)
                logger.info(f"成功添加图书到飞书: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 201, "message": "图书添加成功", "book_info": book_info})
            else:
                logger.error(f"更新飞书图书记录失败: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 500, "message": "更新飞书图书记录失败"})
        except Exception as e:
            logger.error(f"更新飞书图书记录时发生异常 (ISBN: {isbn}): {e}")
            return jsonify({"code": 500, "message": "更新飞书记录时发生错误"})

    else:
        # 4. 创建新记录
        logger.info(f"ISBN {isbn} 在飞书中不存在，开始创建新记录...")
        image_token_val = None # 使用不同的变量名以避免与外部的image_token混淆
        if book_info.get('book_img'):
            try:
                logger.info(f"开始为ISBN {isbn} 上传封面: {book_info['book_img']}")
                # 注意：之前的代码中这里调用的是 feishu_api.upload_image, 
                # 但根据之前的修改，我们应该使用 upload_image_from_url
                # 这里暂时保持 upload_image，假设它是处理本地文件或已下载的图片
                # 如果需要从URL上传，应改为 feishu_api.upload_image_from_url(book_info['book_img'])
                image_token_val = feishu_api.upload_image(book_info['book_img'])
                if image_token_val:
                    logger.info(f"封面上传成功 for ISBN {isbn}, image_token: {image_token_val}")
                    book_info['image_token'] = image_token_val # Store for response, if needed
                else:
                    logger.warning(f"封面上传失败 for ISBN {isbn}，未获取到image_token")
            except Exception as e:
                logger.error(f"上传封面图片失败 (ISBN: {isbn}): {e}")
        
        # 传递空的mappings，让_prepare_feishu_book_data处理所有可识别字段
        feishu_data = _prepare_feishu_book_data(book_info, mappings={}, image_token=image_token_val)
        logger.debug(f"Prepared Feishu data for ISBN create: {feishu_data}")
        
        try:
            record_id = feishu_api.create_book(feishu_data)
            if record_id: # 修复：检查 record_id 是否为真 (非None)
                logger.info(f"成功添加图书到飞书: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 201, "message": "图书添加成功", "book_info": book_info})
            else:
                logger.error(f"添加图书到飞书失败: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 500, "message": "添加图书到飞书失败"})
        except Exception as e:
            logger.error(f"添加飞书图书记录时发生异常 (ISBN: {isbn}): {e}")
            return jsonify({"code": 500, "message": "添加飞书记录时发生错误"})

@app.route('/get_book_info', methods=['GET'])
def get_book_info():
    """获取豆瓣图书信息"""
    isbn = request.args.get('isbn')
    if not isbn:
        logger.warning("请求缺少ISBN参数")
        return jsonify({"code": 400, "message": "缺少ISBN参数"})
    
    logger.info(f"获取豆瓣图书信息: {isbn}")

    # 从豆瓣获取图书信息
    book_info = douban_scraper.get_book_info(isbn)
    if not book_info:
        logger.warning(f"未找到ISBN为 {isbn} 的图书信息")
        return jsonify({"code": 404, "message": "未找到图书信息"})

    return jsonify({
        "code": 200, 
        "message": "获取图书信息成功", 
        "book_info": book_info
    })

@app.route('/sync_to_feishu', methods=['POST'])
def sync_to_feishu():
    """同步图书信息到飞书"""
    data = request.get_json()
    if not data or not data.get('book_info'):
        logger.warning("同步请求缺少图书信息")
        return jsonify({"code": 400, "message": "缺少图书信息"})
    
    book_info = data['book_info']
    isbn = book_info.get('ISBN')
    field_mappings = data.get('field_mappings', {})
    
    logger.info(f"开始同步图书到飞书: {book_info.get('book_name')} (ISBN: {isbn})")

    # 查询飞书中是否已存在该图书
    try:
        record_id = feishu_api.search_book_by_isbn(isbn)
    except Exception as e:
        logger.error(f"查询飞书记录失败 (ISBN: {isbn}): {e}")
        return jsonify({"code": 500, "message": "查询飞书记录失败"})

    # 使用 _prepare_feishu_book_data 方法准备飞书数据
    image_token_val = book_info.get('image_token') # 获取 image_token
    # feishu_data = _prepare_feishu_book_data(book_info, field_mappings, image_token=image_token_val) # 这行是准备用于创建或更新的通用数据，但在更新的逻辑块里又调用了一次，需要调整

    if record_id:
        # 更新现有记录
        logger.info(f"更新飞书记录: {record_id}")
        # 对于更新操作，也需要准备数据，mappings为空表示使用默认逻辑处理所有可识别字段
        # 如果需要更新图片，也应该传递 image_token
        image_token_val = None
        if book_info.get('book_img'): # 假设 book_img 是图片URL或本地路径
            try:
                # 假设 upload_image_from_url 更合适，如果 book_img 是 URL
                # 如果 book_img 是本地文件路径，确保 feishu_api 有对应处理方法
                # 这里暂时保留之前的逻辑，但实际应用中需要明确图片来源和上传方式
                # image_token_val = feishu_api.upload_image(book_info['book_img']) # 这行之前被注释了
                # 为了安全，暂时不处理图片更新，除非有明确的 image_token 传入
                pass
            except Exception as e:
                logger.error(f"为更新操作上传图片失败: {e}")
        
        feishu_data = _prepare_feishu_book_data(book_info, mappings={}, image_token=image_token_val) 
        logger.debug(f"Prepared Feishu data for sync update: {feishu_data}")
        
        try:
            updated_record_id = feishu_api.update_book(record_id, feishu_data)
            if updated_record_id:
                logger.info(f"成功更新图书: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 200, "message": "图书信息更新成功", "book_info": book_info})
            else:
                logger.error(f"更新飞书图书记录失败: {book_info.get('book_name')} (ISBN: {isbn})")
                return jsonify({"code": 500, "message": "更新飞书图书记录失败"})
        except Exception as e:
            logger.error(f"更新飞书记录时发生异常: {e}")
            return jsonify({"code": 500, "message": f"更新飞书记录时发生异常: {str(e)}"})
    else:
        # 创建新记录
        logger.info("创建新飞书记录")
        # 如果有封面图片URL，则先上传图片到飞书并获取 image_token
        # 注意：这里的 image_token_val 变量名与上面获取的不同，需要统一或确保逻辑正确
        # 假设这里的 image_token_val 是新上传的，或者从 book_info 中获取的
        current_image_token = book_info.get('image_token') # 优先使用 book_info 中已有的 image_token

        if 'image_url' in book_info and book_info['image_url'] and not current_image_token:
            try:
                logger.info(f"上传新封面: {book_info['image_url']}")
                current_image_token = feishu_api.upload_image_from_url(book_info['image_url'])
                if current_image_token:
                    logger.info(f"新封面上传成功, image_token: {current_image_token}")
                    book_info['image_token'] = current_image_token # 更新 book_info 中的 token
                else:
                    logger.warning("新封面上传失败，未获取到 image_token")
            except Exception as e:
                logger.error(f"上传新封面图片失败: {e}")
        
        feishu_data = _prepare_feishu_book_data(book_info, field_mappings, image_token=current_image_token)
        logger.debug(f"Prepared Feishu data for sync create: {feishu_data}")
        try:
            record_id = feishu_api.create_book(feishu_data)
            if record_id: # 修复：检查 record_id 是否为真 (非None)
                logger.info(f"成功添加图书: {book_info.get('book_name')}")
                return jsonify({"code": 201, "message": "图书添加成功"})
            return jsonify({"code": 500, "message": "添加图书到飞书失败"})
        except Exception as e:
            logger.error(f"添加飞书记录失败: {e}")
            return jsonify({"code": 500, "message": "添加飞书记录失败"})

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
    """获取飞书多维表格的表头字段，并标记哪些是建议的可选类型"""
    try:
        fields = feishu_api.get_table_fields()
        if fields:
            allowed_types_for_selection = [1, 2, 3, 13, 15, 17]  # 多行文本、数字、单选、电话号码、超链接、附件
            processed_fields = []
            for field in fields:
                field['is_selectable'] = field.get('type') in allowed_types_for_selection
                processed_fields.append(field)
            return jsonify({"code": 200, "message": "获取表头字段成功", "fields": processed_fields})
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