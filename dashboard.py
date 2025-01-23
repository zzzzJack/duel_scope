# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime, timedelta
import os
from constants import SCHOOLS_MAP, GAME_MODES

app = Flask(__name__)

# 全局变量存储最新数据
latest_stats = {
    'today': [],
    'period': [],
    'last_update': None
}

def get_school_name(level, class_id):
    return SCHOOLS_MAP.get((level, class_id), f"未知{class_id}")

def get_latest_file(game_mode):
    """获取最新的数据文件"""
    data_dir = f"data/{game_mode}"
    if not os.path.exists(data_dir):
        return None
    files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
    if not files:
        return None
    return max(files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))

def parse_timestamp(timestamp):
    """
    解析时间戳为datetime对象
    这里假设时间戳需要特殊处理
    """
    # 先将时间戳转换为标准Unix时间戳
    # 这里需要根据实际情况调整转换逻辑
    unix_timestamp = timestamp - SOME_OFFSET
    # 或者
    unix_timestamp = timestamp / SOME_FACTOR
    
    return datetime.fromtimestamp(unix_timestamp)

def process_battle_records(file_path):
    records = []
    with open(file_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            
            parts = line.strip().split(':')
            if len(parts) != 8:
                continue
                
            timestamp = int(parts[0])
            dt = parse_timestamp(timestamp)
            
            # 其他处理逻辑...

def read_game_data(game_mode, start_date=None, end_date=None, last_matches=None, latest_only=False, level_filter=None):
    """读取指定玩法的对战数据"""
    data = []
    data_dir = f"data/{game_mode}"
    
    if not os.path.exists(data_dir):
        return pd.DataFrame()

    # 转换日期字符串为时间戳进行比较
    start_timestamp = None
    end_timestamp = None
    
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
            start_timestamp = int(start_datetime.timestamp())
        except ValueError:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            start_timestamp = int(start_datetime.timestamp())
        
    if end_date:
        try:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d %H:%M')
            end_timestamp = int(end_datetime.timestamp())
        except ValueError:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
            end_timestamp = int(end_datetime.timestamp())

    files_to_process = []
    if latest_only:
        latest_file = get_latest_file(game_mode)
        if latest_file:
            files_to_process = [latest_file]
    else:
        files_to_process = [f for f in os.listdir(data_dir) if f.endswith('.txt')]

    for file in files_to_process:
        file_path = os.path.join(data_dir, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(':')
                        if len(parts) >= 7:
                            timestamp = int(parts[0])
                            
                            # 日期筛选
                            if start_timestamp and timestamp < start_timestamp:
                                continue
                            if end_timestamp and timestamp > end_timestamp:
                                continue
                            
                            date = datetime.fromtimestamp(timestamp)
                            
                            # 等级筛选
                            if level_filter and int(parts[2]) != int(level_filter):
                                continue
                                
                            data.append({
                                'timestamp': timestamp,
                                'date': date,
                                'mode': parts[1],
                                'level': int(parts[2]),
                                'class1': get_school_name(int(parts[4]), int(parts[3])),
                                'class2': get_school_name(int(parts[6]), int(parts[5])),
                                'result': int(parts[7]) if len(parts) > 7 else 1
                            })
        except Exception as e:
            continue

    df = pd.DataFrame(data)
    
    # 最近场次筛选
    if last_matches and not df.empty:
        df = df.sort_values('timestamp', ascending=False).head(int(last_matches))
    
    return df

def calculate_winrates(df):
    """计算胜率统计"""
    results = []
    class_stats = {}
    
    for _, row in df.iterrows():
        # 处理职业1的统计
        if row['class1'] not in class_stats:
            class_stats[row['class1']] = {'wins': 0, 'total': 0}
        class_stats[row['class1']]['total'] += 1
        if row['result'] == 1:
            class_stats[row['class1']]['wins'] += 1
            
        # 处理职业2的统计
        if row['class2'] not in class_stats:
            class_stats[row['class2']] = {'wins': 0, 'total': 0}
        class_stats[row['class2']]['total'] += 1
        if row['result'] == 2:
            class_stats[row['class2']]['wins'] += 1
    
    for class_name, stats in class_stats.items():
        if stats['total'] > 0:
            winrate = (stats['wins'] / stats['total']) * 100
            results.append({
                'class_name': class_name,
                'winrate': round(winrate, 2),
                'matches': stats['total']
            })
    
    return sorted(results, key=lambda x: x['winrate'], reverse=True)

def update_stats():
    """更新统计数据"""
    try:
        columns = ['日期', '职业1', '流派1', '职业2', '流派2', '结果']
        df = pd.read_csv('data/matches.txt', names=columns)
        df['日期'] = pd.to_datetime(df['日期'])
        
        # 计算今日数据
        today = datetime.now().date()
        today_df = df[df['日期'].dt.date == today]
        today_stats = calculate_winrates(today_df)
        
        # 更新全局变量
        latest_stats['today'] = today_stats
        latest_stats['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"数据更新成功: {latest_stats['last_update']}")
    except Exception as e:
        print(f"数据更新失败: {str(e)}")

@app.route('/api/stats')
def get_stats():
    """API endpoint for getting stats with filters"""
    game_mode = request.args.get('mode', 'test_pvp')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    last_matches = request.args.get('last_matches')
    latest_only = request.args.get('latest_only') == 'true'
    level_filter = request.args.get('level')
    
    df = read_game_data(game_mode, start_date, end_date, last_matches, latest_only, level_filter)
    if df.empty:
        return jsonify({'stats': [], 'total_matches': 0})
        
    stats = calculate_winrates(df)
    total_matches = len(df)
    
    return jsonify({
        'stats': stats,
        'total_matches': total_matches
    })

@app.route('/')
def index():
    # 获取第一个玩法的默认数据
    default_mode = list(GAME_MODES.keys())[0]
    df = read_game_data(default_mode, latest_only=True)
    default_stats = calculate_winrates(df) if not df.empty else []
    total_matches = len(df)  # 计算默认数据的总场次
    
    return render_template('game_stats.html', 
                         game_modes=GAME_MODES,
                         default_mode=default_mode,
                         default_stats=default_stats,
                         total_matches=total_matches)  # 传递总场次到模板

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True) 

# 检查示例时间戳
timestamp = 1737512753
dt = datetime.fromtimestamp(timestamp)
print(f"时间戳 {timestamp} 对应的时间是: {dt}")

# 获取当前时间戳作为对比
now = datetime.now()
current_timestamp = int(now.timestamp())
print(f"当前时间戳是: {current_timestamp}") 