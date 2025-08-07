import duckdb
import os
import pandas as pd
import asyncio
from ....utils.logger import logger
from ....kernel.settings import settings

class DBManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = settings.PROMETHEUS_PIPELINE.database.main_db_path
        else:
            self.db_path = db_path
        self.logger = logger # 使用共享的 logger

        # 確保數據庫目錄存在
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

    async def save_data(self, data: pd.DataFrame, table_name: str):
        """
        以非同步方式儲存數據。
        """
        if data.empty:
            await self.logger.log("WARNING", "數據為空，沒有可以儲存的內容。", source=self.__class__.__name__)
            return

        try:
            await asyncio.to_thread(self._blocking_save_data, data, table_name)
        except Exception as e:
            await self.logger.log("ERROR", f"儲存數據時發生錯誤: {e}", source=self.__class__.__name__, exc_info=True)
            raise

    def _blocking_save_data(self, data: pd.DataFrame, table_name: str):
        """包含阻塞 I/O 的內部儲存方法。"""
        # Note: logging from this thread will use print.
        with duckdb.connect(self.db_path) as con:
            db_columns = self._get_table_columns(con, table_name)

            if not db_columns:
                print(f"INFO: [DBManager-Thread] 表格 '{table_name}' 不存在，將根據 DataFrame 結構創建。")
                create_sql = f"""
                CREATE TABLE {table_name} (
                    date TIMESTAMP,
                    symbol VARCHAR,
                    PRIMARY KEY (date, symbol)
                );
                """
                con.execute(create_sql)
                print(f"INFO: [DBManager-Thread] 成功創建表格 '{table_name}' 並定義了 (date, symbol) 複合主鍵。")

                con.register('df_to_insert', data)
                initial_cols = {'date', 'symbol'}
                remaining_cols = [col for col in data.columns if col not in initial_cols]
                for col in remaining_cols:
                    col_dtype = data[col].dtype
                    sql_type = self._map_dtype_to_sql(col_dtype)
                    con.execute(f"ALTER TABLE {table_name} ADD COLUMN \"{col}\" {sql_type};")

                all_cols = ['date', 'symbol'] + remaining_cols
                col_names_str = ", ".join(f'"{c}"' for c in all_cols)
                con.execute(f"INSERT INTO {table_name} ({col_names_str}) SELECT {col_names_str} FROM df_to_insert")
                print(f"INFO: [DBManager-Thread] 成功將 {len(data)} 筆初始數據插入到新創建的 '{table_name}' 表格中。")
            else:
                df_columns = data.columns.tolist()
                new_columns = set(df_columns) - set(db_columns)

                if new_columns:
                    print(f"INFO: [DBManager-Thread] 偵測到新欄位: {new_columns}。正在演進表格結構...")
                    for col in new_columns:
                        col_dtype = data[col].dtype
                        sql_type = self._map_dtype_to_sql(col_dtype)
                        con.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {sql_type};")
                    print("INFO: [DBManager-Thread] 表格結構演進完成。")

                con.register('df_to_upsert', data)
                all_columns = [f'"{c}"' for c in data.columns]
                update_columns = [col for col in all_columns if col.lower() not in ('"date"', '"symbol"')]

                if not update_columns:
                    print(f"WARNING: [DBManager-Thread] 沒有需要更新的欄位（除了主鍵），將只執行插入操作。")
                    upsert_sql = f"""
                    INSERT INTO {table_name} ({', '.join(all_columns)})
                    SELECT {', '.join(all_columns)} FROM df_to_upsert
                    ON CONFLICT (date, symbol) DO NOTHING;
                    """
                else:
                    set_clause = ", ".join([f'{col} = excluded.{col}' for col in update_columns])
                    upsert_sql = f"""
                    INSERT INTO {table_name} ({', '.join(all_columns)})
                    SELECT {', '.join(all_columns)} FROM df_to_upsert
                    ON CONFLICT (date, symbol) DO UPDATE SET
                        {set_clause};
                    """
                con.execute(upsert_sql)
                print(f"INFO: [DBManager-Thread] 成功將 {len(data)} 筆數據 UPSERT 到 '{table_name}'。")

    def _get_table_columns(self, con, table_name):
        """查詢並返回資料庫表的欄位列表（全部轉為小寫）。"""
        try:
            table_info = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            # 將所有列名轉為小寫，以實現不區分大小寫的比較
            return [str(info[1]).lower() for info in table_info]
        except duckdb.CatalogException:
            return []

    async def fetch_table(self, table_name: str) -> pd.DataFrame:
        """
        以非同步方式從數據庫中讀取整個表格。
        """
        try:
            # 將阻塞操作移至背景執行緒
            return await asyncio.to_thread(self._blocking_fetch_table, table_name)
        except Exception as e:
            await self.logger.log("ERROR", f"讀取表格 '{table_name}' 時發生錯誤: {e}", source=self.__class__.__name__, exc_info=True)
            return pd.DataFrame()

    def _blocking_fetch_table(self, table_name: str) -> pd.DataFrame:
        """
        包含阻塞 I/O 的內部讀取方法。
        注意：此方法在獨立執行緒中運行，因此日誌記錄使用 print。
        """
        try:
            with duckdb.connect(self.db_path) as con:
                tables = con.execute("SHOW TABLES").fetchall()
                if (table_name,) not in tables:
                    print(f"WARNING: [DBManager-Thread] 表格 '{table_name}' 在數據庫中不存在。")
                    return pd.DataFrame()
                df = con.table(table_name).to_df()
                print(f"INFO: [DBManager-Thread] 成功從 '{table_name}' 表格中讀取 {len(df)} 筆數據。")
                return df
        except Exception as e:
            print(f"ERROR: [DBManager-Thread] 讀取表格 '{table_name}' 時在執行緒中發生錯誤: {e}")
            return pd.DataFrame()

    def _map_dtype_to_sql(self, dtype):
        """將 Pandas 的 dtype 轉換為 SQL 類型字串。"""
        if pd.api.types.is_integer_dtype(dtype):
            return 'BIGINT'
        elif pd.api.types.is_float_dtype(dtype):
            return 'DOUBLE'
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return 'TIMESTAMP'
        elif pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
            return 'VARCHAR'
        else:
            return 'VARCHAR'
