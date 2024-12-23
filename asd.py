import subprocess
import json
import pymysql
from datetime import datetime, timedelta
import time
import sys

# [설정]
DB_HOST = "localhost"
DB_USER = "alswnddldy"
DB_PASSWORD = "1234"
DB_NAME = "alswnddldy"
TABLE_NAME = "upbit_data"
STATUS_FILE = "/home/one/mysql3/mysql/progress_second.txt"

# 수집할 코인 목록
COINS = {
    "KLAY": "KRW-KLAY",
    "ICX": "KRW-ICX",
    "AERGO": "KRW-AERGO",
    "META": "KRW-META",
    "BORA": "KRW-BORA",
    "BTC": "KRW-BTC",
    "ETH": "KRW-ETH",
    "BNB": "KRW-BNB",
    "USDT": "KRW-USDT",
    "ADA": "KRW-ADA",
}

# 필요한 모듈 및 환경 점검
def check_environment():
    try:
        import pymysql
        print("pymysql 모듈 확인 완료")
    except ImportError:
        print("pymysql 모듈이 누락되었습니다. 설치 명령: pip install pymysql")
        sys.exit(1)

    # curl 설치 확인
    result = subprocess.run(["curl", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        print("curl 설치 확인 완료")
    else:
        print("curl이 설치되지 않았습니다. 설치 명령: sudo apt install curl")
        sys.exit(1)

    # MySQL 연결 확인
    try:
        connection = pymysql.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD
        )
        print("MySQL 연결 확인 완료")
        connection.close()
    except pymysql.MySQLError as e:
        print(f"MySQL 연결 실패: {e}")
        sys.exit(1)

# 데이터베이스 생성
def create_database_if_not_exists():
    connection = pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD
    )
    cursor = connection.cursor()
    create_db_query = f"CREATE DATABASE IF NOT EXISTS {DB_NAME};"
    cursor.execute(create_db_query)
    connection.commit()
    cursor.close()
    connection.close()

# 테이블 생성
def create_table_if_not_exists():
    connection = pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    cursor = connection.cursor()
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date DATE NOT NULL,
        code VARCHAR(20) NOT NULL,               -- 마켓 코드 (예: KRW-BTC)
        opening_price DOUBLE NOT NULL,           -- 시가
        closing_price DOUBLE NOT NULL,           -- 종가
        high_price DOUBLE NOT NULL,              -- 고가
        low_price DOUBLE NOT NULL,               -- 저가
        volume DOUBLE NOT NULL,                  -- 거래량
        prev_closing_price DOUBLE NOT NULL,      -- 전일 종가
        UNIQUE(date, code)
    );
    """
    cursor.execute(create_table_query)
    connection.commit()
    cursor.close()
    connection.close()

# API 요청
def fetch_data(coin_market):
    url = f"https://api.upbit.com/v1/candles/days?count=1&market={coin_market}"
    print(f"DEBUG: 요청 URL = {url}")
    result = subprocess.run(
        [
            "curl", "--request", "GET",
            "--url", url,
            "--header", "Accept: application/json"
        ],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            print(f"DEBUG: {coin_market} 응답 데이터: {data}")
            return data
        except json.JSONDecodeError:
            print(f"JSON 파싱 실패: {result.stdout}")
            return None
    else:
        print(f"API 요청 실패: {result.stderr}")
        return None

# 데이터베이스 저장
def save_data_to_db(data, market):
    connection = pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    cursor = connection.cursor()
    insert_query = f"""
    INSERT IGNORE INTO {TABLE_NAME} 
    (date, code, opening_price, closing_price, high_price, low_price, volume, prev_closing_price)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    date = data["candle_date_time_kst"][:10]
    opening_price = data["opening_price"]
    closing_price = data["trade_price"]
    high_price = data["high_price"]
    low_price = data["low_price"]
    volume = data["candle_acc_trade_volume"]
    prev_closing_price = data["prev_closing_price"]

    cursor.execute(
        insert_query,
        (date, market, opening_price, closing_price, high_price, low_price, volume, prev_closing_price),
    )
    connection.commit()
    cursor.close()
    connection.close()

# 상태 파일 업데이트
def update_status_file(last_date):
    with open(STATUS_FILE, "w") as file:
        file.write(last_date)

# 상태 파일 읽기
def get_last_processed_date():
    try:
        with open(STATUS_FILE, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        return None

# 메인 실행
def main():
    check_environment()  # 환경 확인

    create_database_if_not_exists()
    create_table_if_not_exists()

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    last_processed_date = get_last_processed_date()

    if last_processed_date == yesterday:
        print("어제 날짜 데이터는 이미 수집됨.")
        return

    for coin_name, market in COINS.items():
        print(f"데이터 수집 중: {coin_name} ({market})")
        data = fetch_data(market)
        if data and len(data) > 0:
            print(f"{coin_name} 데이터 저장 중...")
            save_data_to_db(data[0], market)
        else:
            print(f"{coin_name}: 데이터 없음 또는 API 요청 실패.")

    update_status_file(yesterday)
    print("데이터 수집 및 저장 완료.")

if __name__ == "__main__":
    main()
