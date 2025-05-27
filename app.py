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

def _prepare_feishu_book_data(book_info: dict, douban_to_feishu_header_mappings: dict) -> Dict[str, Any]:
    """
    根据豆瓣图书信息和用户选择的映射关系（豆瓣字段名 -> 飞书表头字段名或字段ID）准备数据。
    此函数返回的 "fields" 字典的键始终是飞书的 *表头字段名*。
    如果输入的映射关系中，飞书侧的值是字段ID，此函数会尝试将其转换为对应的表头字段名。
    """
    logger.info(f"开始准备飞书数据，ISBN: {book_info.get('ISBN')}")
    logger.debug(f"输入参数 - book_info: {book_info.keys()}, mappings: {douban_to_feishu_header_mappings}")
    
    fields_data_with_headers: Dict[str, Any] = {}

    # 获取飞书字段结构用于ID到名称的映射
    try:
        feishu_fields_structure = feishu_api.get_table_fields()
        id_to_name_map = {field['field_id']: field['name'] for field in feishu_fields_structure} if feishu_fields_structure else {}
        name_set = {field['name'] for field in feishu_fields_structure} if feishu_fields_structure else set()
        logger.debug(f"获取到飞书字段结构: {len(id_to_name_map)} 个ID已映射, {len(name_set)} 个名称已找到.")
    except Exception as e:
        logger.error(f"获取飞书字段结构失败: {e}. 将无法准确转换字段ID到名称.", exc_info=True)
        id_to_name_map = {}
        name_set = set()

    logger.debug(f"开始处理字段映射，共 {len(douban_to_feishu_header_mappings)} 个字段")
    
    for douban_field_name, feishu_key_from_mapping in douban_to_feishu_header_mappings.items():
        value_to_set = None # 初始化为None，确保只有有效值才被添加
        logger.debug(f"处理豆瓣字段: {douban_field_name} -> 飞书键(来自映射): {feishu_key_from_mapping}")

        # 使用字典映射简化字段处理
        field_handlers = {
            'book_name': lambda: book_info.get('book_name'),
            'author_name': lambda: book_info.get('author_name'),
            'press': lambda: book_info.get('press'),
            'pages': lambda: int(book_info.get('pages')) if book_info.get('pages') else None,
            'ISBN': lambda: book_info.get('ISBN'),
            'brand': lambda: book_info.get('brand'),
            'score': lambda: float(book_info.get('score')) if book_info.get('score') else None,
            'url': lambda: {"link": book_info.get('url')} if book_info.get('url') else None,
            'translator': lambda: book_info.get('translator') if book_info.get('translator') else None,
            'book_img': lambda: feishu_api.upload_image_from_url(book_info.get('book_img')) if book_info.get('book_img') else None,
            'pub_date': lambda: book_info.get('pub_date'),
        }

        # 处理字段
        if douban_field_name in field_handlers:
            try:
                value_to_set = field_handlers[douban_field_name]()
                logger.debug(f"字段 '{douban_field_name}' 的值: {value_to_set}")
            except Exception as e:
                logger.warning(f"处理字段 '{douban_field_name}' 时出错: {e}")

        # 确定实际的飞书字段名作为键
        actual_feishu_field_name = _get_actual_feishu_field_name(feishu_key_from_mapping, id_to_name_map, name_set, douban_field_name, book_info)

        # 仅当确定了有效值和有效的飞书字段名时才添加到字典中
        if value_to_set is not None and actual_feishu_field_name is not None:
            fields_data_with_headers[actual_feishu_field_name] = value_to_set
            logger.debug(f"已添加字段 '{actual_feishu_field_name}' (值为: {type(value_to_set)}) 到准备好的飞书数据中.")

    # 记录最终数据摘要
    logger.info(f"飞书数据准备完成，共生成 {len(fields_data_with_headers)} 个字段")
    logger.debug(f"最终飞书数据: { {k: type(v) for k, v in fields_data_with_headers.items()} }")
    
    # 检查关键字段
    required_fields = ["书名", "作者", "ISBN", "封面"]
    missing_fields = [field for field in required_fields if field not in fields_data_with_headers]
    if missing_fields:
        logger.warning(f"缺少关键字段: {missing_fields} (ISBN: {book_info.get('ISBN')})")
    
    return {"fields": fields_data_with_headers}

def _get_actual_feishu_field_name(feishu_key_from_mapping, id_to_name_map, name_set, douban_field_name, book_info):
    if feishu_key_from_mapping in id_to_name_map:
        actual_feishu_field_name = id_to_name_map[feishu_key_from_mapping]
        logger.debug(f"映射提供的键 '{feishu_key_from_mapping}' 是一个字段ID, 已转换为字段名 '{actual_feishu_field_name}'.")
    elif feishu_key_from_mapping in name_set:
        actual_feishu_field_name = feishu_key_from_mapping
        logger.debug(f"映射提供的键 '{feishu_key_from_mapping}' 已经是一个有效的字段名.")
    else:
        logger.warning(f"映射提供的键 '{feishu_key_from_mapping}' (来自豆瓣字段 '{douban_field_name}') 既不是有效的飞书字段ID也不是已知的飞书字段名. 将尝试按原样使用. ISBN: {book_info.get('ISBN')}")
        actual_feishu_field_name = feishu_key_from_mapping
    return actual_feishu_field_name

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
    data = request.get_json()
    if not data or not data.get('book_info'):
        logger.warning("同步请求缺少图书信息")
        return jsonify({"code": 400, "message": "缺少图书信息"})
    
    book_info = data['book_info']
    isbn = book_info.get('ISBN')
    # user_field_mappings is douban_field_name -> feishu_header_name from the client
    user_field_mappings = data.get('field_mappings', {})
    
    logger.info(f"开始同步图书到飞书: {book_info.get('book_name')} (ISBN: {isbn})")
    logger.debug(f"接收到的用户字段映射: {user_field_mappings}")

    try:
       
        # 查找飞书记录
        record_id = feishu_api.search_book_by_isbn(isbn)
        
        # 更新或者创建图书记录
        if record_id:
            # 更新已经存在的图书记录
            logger.info(f"准备更新飞书记录 ID: {record_id} (ISBN: {isbn})")
            prepared_data_with_names = _prepare_feishu_book_data(
                book_info, 
                user_field_mappings  # Use mappings from request for both create/update
            )
            logger.debug(f"数据准备完成 (飞书表头名称为键): {prepared_data_with_names}")
            # Check if there are any fields to update in prepared_data_with_names
            if not prepared_data_with_names.get("fields"):
                 logger.info(f"没有要更新的字段 (记录ID: {record_id}). 跳过API调用.")
                 return jsonify({
                    "code": 200, 
                    "message": "没有要更新的字段，记录未更改.",
                    "book_info": book_info,
                    "record_id": record_id
                })
            try:
                # Pass data with field names directly
                updated_record_id = feishu_api.update_book(record_id, prepared_data_with_names)
                if updated_record_id:
                    logger.info(f"成功更新图书: {book_info.get('book_name')} (ISBN: {isbn}, 记录ID: {record_id})")
                    return jsonify({
                        "code": 200, 
                        "message": "图书信息更新成功",
                        "book_info": book_info,
                        "record_id": record_id
                    })
                else:
                    logger.error(f"更新飞书图书记录失败: API未确认成功 (ISBN: {isbn}, 记录ID: {record_id})")
                    return jsonify({"code": 500, "message": "更新飞书图书记录失败: API未确认成功", "record_id": record_id})
            except Exception as e:
                logger.error(f"更新飞书记录失败 (ISBN: {isbn}, 记录ID: {record_id}): {str(e)}", exc_info=True)
                return jsonify({"code": 500, "message": f"更新飞书记录失败: {str(e)}", "error_details": str(e), "record_id": record_id})
        else:
            # 新增图书记录
            logger.info(f"准备创建新飞书记录 (ISBN: {isbn})")
            
            prepared_data_with_names = _prepare_feishu_book_data(
                book_info, 
                user_field_mappings  # Use mappings from request for both create/update
            )
            logger.debug(f"数据准备完成 (飞书表头名称为键): {prepared_data_with_names}")

            # Check if there are any fields to create in prepared_data_with_names
            if not prepared_data_with_names.get("fields"):
                 logger.error(f"无法创建记录，没有要设置的字段 (ISBN: {isbn}).")
                 return jsonify({"code": 400, "message": "无法创建记录: 没有提供任何有效的字段数据."})
            try:
                # Pass data with field names directly
                new_record_id = feishu_api.create_book(prepared_data_with_names)
                if new_record_id:
                    logger.info(f"成功添加图书: {book_info.get('book_name')} (ISBN: {isbn}, 新记录ID: {new_record_id})")
                    return jsonify({"code": 201, "message": "图书添加成功", "record_id": new_record_id})
                else:
                    logger.error(f"添加图书到飞书失败: API未返回记录ID (ISBN: {isbn})")
                    return jsonify({"code": 500, "message": "添加图书到飞书失败: API未返回记录ID"})
            except Exception as e:
                logger.error(f"添加飞书记录失败 (ISBN: {isbn}): {str(e)}", exc_info=True)
                return jsonify({"code": 500, "message": f"添加飞书记录失败: {str(e)}", "error_details": str(e)})

    except Exception as e: # Catch-all for unexpected errors during setup (e.g., feishu_api.get_table_fields)
        logger.error(f"同步到飞书时发生顶层处理错误 (ISBN: {isbn}): {e}", exc_info=True)
        return jsonify({"code": 500, "message": f"同步操作意外失败: {str(e)}"})

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