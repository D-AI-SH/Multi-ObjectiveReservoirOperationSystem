import pandas as pd
import numpy as np
import sqlite3
import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import warnings
import json
import os

class SmartDataProcessor:
    """智能数据处理类，负责日期整合、数据库检查和列名智能匹配"""
    
    def __init__(self, db_conn: Optional[sqlite3.Connection] = None, ai_enabled: bool = False):
        self.db_conn = db_conn
        self.ai_enabled = ai_enabled
        self.ai_api_key = ""
        self.ai_api_url = "https://api.ai-assistant.com/v1/chat/completions"
        self.ai_model = "gpt-3.5-turbo"
        
        # 日期列名模式匹配（支持大小写，更精确的匹配）
        self.date_patterns = {
            'year': r'^(年|year|yr)$',
            'month': r'^(月|month|mon)$',
            'day': r'^(日|天|day)$',
            'hour': r'^(时|小时|hour|hr)$',
            'minute': r'^(分|分钟|minute|min)$',
            'second': r'^(秒|second|sec)$'
        }
        
        # 常见的中文列名映射
        self.column_translations = {
            # 时间相关
            'time': '时间',
            'date': '日期',
            'datetime': '日期时间',
            'timestamp': '时间戳',
            
            # 水文相关
            'flow': '流量',
            'discharge': '下泄流量',
            'inflow': '入库流量',
            'outflow': '出库流量',
            'water_level': '水位',
            'storage': '库容',
            'reservoir_level': '水库水位',
            'reservoir_storage': '水库库容',
            
            # 气象相关
            'precipitation': '降水量',
            'rainfall': '降雨量',
            'temperature': '温度',
            'humidity': '湿度',
            'evaporation': '蒸发量',
            
            # 发电相关
            'power': '发电量',
            'generation': '发电功率',
            'turbine_flow': '机组流量',
            'head': '水头',
            
            # 其他
            'quality': '水质',
            'turbidity': '浊度',
            'ph': 'pH值',
            'dissolved_oxygen': '溶解氧'
        }
    
    def check_and_fix_database_dates(self) -> Dict[str, Any]:
        """检查数据库中的日期列并进行整合"""
        if not self.db_conn:
            return {'status': 'error', 'message': '数据库未连接'}
        
        results = {
            'status': 'success',
            'tables_checked': 0,
            'tables_fixed': 0,
            'details': []
        }
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                results['tables_checked'] += 1
                
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # 检查是否有分离的日期列
                date_columns = self._identify_date_columns([col[1] for col in columns])
                
                if date_columns:
                    # 尝试整合日期列
                    fixed = self._consolidate_date_columns(table_name, date_columns)
                    if fixed:
                        results['tables_fixed'] += 1
                        results['details'].append({
                            'table': table_name,
                            'action': 'date_consolidation',
                            'columns_processed': list(date_columns.keys())
                        })
            
            return results
            
        except Exception as e:
            return {'status': 'error', 'message': f'数据库检查失败: {str(e)}'}
    
    def _identify_date_columns(self, column_names: List[str]) -> Dict[str, List[str]]:
        """识别可能的日期列组合"""
        date_groups = {}
        
        # 按类型分组
        year_cols = []
        month_cols = []
        day_cols = []
        hour_cols = []
        minute_cols = []
        second_cols = []
        
        for col in column_names:
            col_lower = col.lower()
            
            # 检查年份列（支持大小写）
            if re.search(self.date_patterns['year'], col_lower, re.IGNORECASE):
                year_cols.append(col)
            # 检查月份列（支持大小写）
            elif re.search(self.date_patterns['month'], col_lower, re.IGNORECASE):
                month_cols.append(col)
            # 检查日期列（支持大小写）
            elif re.search(self.date_patterns['day'], col_lower, re.IGNORECASE):
                day_cols.append(col)
            # 检查小时列（支持大小写）
            elif re.search(self.date_patterns['hour'], col_lower, re.IGNORECASE):
                hour_cols.append(col)
            # 检查分钟列（支持大小写）
            elif re.search(self.date_patterns['minute'], col_lower, re.IGNORECASE):
                minute_cols.append(col)
            # 检查秒列（支持大小写）
            elif re.search(self.date_patterns['second'], col_lower, re.IGNORECASE):
                second_cols.append(col)
        
        # 组合可能的日期列组
        if year_cols and month_cols and day_cols:
            # 年月日组合
            for year_col in year_cols:
                for month_col in month_cols:
                    for day_col in day_cols:
                        key = f"{year_col}_{month_col}_{day_col}"
                        date_groups[key] = [year_col, month_col, day_col]
                        
                        # 如果有小时列，也加入
                        if hour_cols:
                            for hour_col in hour_cols:
                                key_with_hour = f"{key}_{hour_col}"
                                date_groups[key_with_hour] = [year_col, month_col, day_col, hour_col]
        
        return date_groups
        
        return date_groups
    
    def _consolidate_date_columns(self, table_name: str, date_columns: Dict[str, List[str]]) -> bool:
        """整合日期列"""
        try:
            # 读取数据
            df = pd.read_sql(f"SELECT * FROM {table_name}", self.db_conn)
            
            consolidated = False
            
            for group_name, cols in date_columns.items():
                if len(cols) >= 3:  # 至少需要年月日
                    # 检查这些列是否都存在
                    if all(col in df.columns for col in cols):
                        # 尝试创建日期列
                        new_date_col = self._create_date_column(df, cols)
                        if new_date_col is not None:
                            # 添加新的日期列
                            df[f'date_{group_name}'] = new_date_col
                            
                            # 删除原始列
                            for col in cols:
                                if col in df.columns:
                                    df = df.drop(columns=[col])
                            
                            consolidated = True
            
            if consolidated:
                # 更新数据库表
                df.to_sql(table_name, self.db_conn, if_exists='replace', index=False)
                return True
            
            return False
            
        except Exception as e:
            print(f"整合日期列失败 {table_name}: {e}")
            return False
    
    def _create_date_column(self, df: pd.DataFrame, date_cols: List[str]) -> Optional[pd.Series]:
        """从多个列创建日期列"""
        try:
            # 尝试不同的日期格式
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%Y.%m.%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y.%m.%d %H:%M:%S'
            ]
            
            # 构建日期字符串
            if len(date_cols) >= 3:
                year_col, month_col, day_col = date_cols[0], date_cols[1], date_cols[2]
                
                # 确保数据类型
                df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
                df[month_col] = pd.to_numeric(df[month_col], errors='coerce')
                df[day_col] = pd.to_numeric(df[day_col], errors='coerce')
                
                # 构建基础日期
                date_str = df[year_col].astype(str) + '-' + \
                          df[month_col].astype(str).str.zfill(2) + '-' + \
                          df[day_col].astype(str).str.zfill(2)
                
                # 如果有小时列
                if len(date_cols) >= 4:
                    hour_col = date_cols[3]
                    df[hour_col] = pd.to_numeric(df[hour_col], errors='coerce')
                    date_str += ' ' + df[hour_col].astype(str).str.zfill(2) + ':00:00'
                else:
                    date_str += ' 00:00:00'
                
                # 尝试解析日期
                for fmt in date_formats:
                    try:
                        parsed_dates = pd.to_datetime(date_str, format=fmt, errors='coerce')
                        if not parsed_dates.isna().all():
                            return parsed_dates
                    except:
                        continue
            
            return None
            
        except Exception as e:
            print(f"创建日期列失败: {e}")
            return None
    
    def smart_column_matching(self, columns: List[str], target_columns: Optional[List[str]] = None) -> Dict[str, str]:
        """智能列名匹配和翻译"""
        matches = {}
        
        for col in columns:
            col_lower = col.lower()
            
            # 1. 直接匹配
            if col in self.column_translations:
                matches[col] = self.column_translations[col]
                continue
            
            # 2. 模糊匹配
            for eng, chn in self.column_translations.items():
                if eng in col_lower or col_lower in eng:
                    matches[col] = chn
                    break
            
            # 3. 模式匹配
            if not matches.get(col):
                translated = self._pattern_match_column(col)
                if translated:
                    matches[col] = translated
            
            # 4. 如果启用了AI，使用AI进行翻译
            if self.ai_enabled and not matches.get(col):
                ai_translation = self._ai_translate_column(col)
                if ai_translation:
                    matches[col] = ai_translation
        
        return matches
    
    def _pattern_match_column(self, column_name: str) -> Optional[str]:
        """使用模式匹配翻译列名"""
        col_lower = column_name.lower()
        
        # 水文相关模式
        if 'flow' in col_lower or 'discharge' in col_lower:
            if 'in' in col_lower:
                return '入库流量'
            elif 'out' in col_lower:
                return '出库流量'
            else:
                return '流量'
        
        if 'level' in col_lower or 'water' in col_lower:
            return '水位'
        
        if 'storage' in col_lower or 'volume' in col_lower:
            return '库容'
        
        if 'power' in col_lower or 'generation' in col_lower:
            return '发电量'
        
        if 'precipitation' in col_lower or 'rain' in col_lower:
            return '降水量'
        
        if 'temperature' in col_lower or 'temp' in col_lower:
            return '温度'
        
        if 'quality' in col_lower or 'turbidity' in col_lower:
            return '水质'
        
        # 时间相关模式
        if any(word in col_lower for word in ['time', 'date', 'hour', 'minute', 'second']):
            if 'year' in col_lower or '年' in column_name:
                return '年份'
            elif 'month' in col_lower or '月' in column_name:
                return '月份'
            elif 'day' in col_lower or '日' in column_name or '天' in column_name:
                return '日期'
            elif 'hour' in col_lower or '时' in column_name or '小时' in column_name:
                return '小时'
            else:
                return '时间'
        
        return None
    
    def _ai_translate_column(self, column_name: str) -> Optional[str]:
        """使用AI翻译列名（如果启用）"""
        if not self.ai_enabled:
            return None
        
        try:
            # 使用AI智能助手API进行列名翻译
            # 只用于水文、气象、发电等相关术语的列名整理
            ai_translation = self._call_ai_assistant_api(column_name)
            if ai_translation:
                return ai_translation
            return None
        except Exception as e:
            print(f"AI翻译失败: {e}")
            return None
    
    def _call_ai_assistant_api(self, column_name: str) -> Optional[str]:
        """调用AI智能助手API进行列名翻译"""
        try:
            # 构建专门用于列名翻译的提示词
            prompt = f"""
请将以下英文列名翻译为中文，只返回中文翻译结果，不要其他解释：

列名：{column_name}

要求：
1. 如果是水文相关术语（如flow、level、storage等），请翻译为对应的中文术语
2. 如果是气象相关术语（如temperature、precipitation等），请翻译为对应的中文术语  
3. 如果是发电相关术语（如power、generation等），请翻译为对应的中文术语
4. 如果是时间相关术语，请翻译为对应的中文时间术语
5. 如果无法识别或不属于以上类别，请返回原列名

只返回翻译结果，不要其他内容。
"""
            
            # 调用AI智能助手API
            import requests
            import json
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.ai_api_key}"
            }
            
            payload = {
                "model": self.ai_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            response = requests.post(
                self.ai_api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    translation = result['choices'][0]['message']['content'].strip()
                    # 清理可能的额外内容
                    translation = translation.replace('翻译结果：', '').replace('中文翻译：', '').strip()
                    return translation
                else:
                    print(f"AI API返回格式异常: {result}")
                    return None
            else:
                print(f"AI API调用失败: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"AI API网络请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"AI API响应解析失败: {e}")
            return None
        except (ValueError, KeyError, IndexError) as e:
            print(f"AI API响应格式错误: {e}")
            return None
            
        except Exception as e:
            print(f"AI助手API调用失败: {e}")
            return None
    
    def process_dataframe_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理DataFrame中的日期列"""
        df_processed = df.copy()
        
        # 检查是否有分离的日期列
        date_columns = self._identify_date_columns(df.columns.tolist())
        
        for group_name, cols in date_columns.items():
            if all(col in df.columns for col in cols):
                new_date_col = self._create_date_column(df_processed, cols)
                if new_date_col is not None:
                    df_processed[f'date_{group_name}'] = new_date_col
                    # 删除原始列
                    for col in cols:
                        if col in df_processed.columns:
                            df_processed = df_processed.drop(columns=[col])
        
        return df_processed
    
    def get_column_analysis(self, columns: List[str]) -> Dict[str, Any]:
        """分析列名并提供建议"""
        analysis = {
            'total_columns': len(columns),
            'date_columns': [],
            'numeric_columns': [],
            'categorical_columns': [],
            'suggestions': []
        }
        
        for col in columns:
            col_lower = col.lower()
            
            # 检查日期列
            if any(re.search(pattern, col_lower, re.IGNORECASE) for pattern in self.date_patterns.values()):
                analysis['date_columns'].append(col)
            
            # 检查数值列
            if any(word in col_lower for word in ['flow', 'level', 'storage', 'power', 'temperature', 'precipitation']):
                analysis['numeric_columns'].append(col)
            
            # 检查分类列
            if any(word in col_lower for word in ['type', 'category', 'status', 'quality']):
                analysis['categorical_columns'].append(col)
        
        # 生成建议
        if len(analysis['date_columns']) > 1:
            analysis['suggestions'].append('检测到多个日期相关列，建议整合为单一日期列')
        
        if len(analysis['numeric_columns']) > 0:
            analysis['suggestions'].append('检测到数值列，建议检查数据范围和单位')
        
        return analysis
