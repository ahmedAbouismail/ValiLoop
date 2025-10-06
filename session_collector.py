import sqlite3
import json
import time
from datetime import datetime
from typing import Dict, Optional
from data_moduels.validation_mode import ValidationMode
class SessionCollector:

    def __init__(self):
        self.session_id = None
        self.raw_text = None
        self.session_start_time = None
        self.session_data = []  # NEU: Diese Zeile hinzufügen

        # Tracking für AUTOMATIC mode
        self.auto_data = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_cost': 0.0,
            'iterations': 0,
            'transform_time': 0.0,
            'validation_time': 0.0,
            'quality_score': '',
            'errors': ''
        }

        # Tracking für HUMAN mode
        self.human_data = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_cost': 0.0,
            'iterations': 0,
            'transform_time': 0.0,
            'feedback_time': 0.0,
            'quality_score': '',
            'errors': ''
        }

        self.current_mode = None
        self.current_node_start = None

    def start_session(self, session_id: str, raw_text: str):
        """Startet neue Session"""
        self.session_id = session_id
        self.raw_text = raw_text
        self.session_start_time = time.time()

        # Reset data
        self.auto_data = {
            'input_tokens': 0, 'output_tokens': 0, 'total_cost': 0.0,
            'iterations': 0, 'transform_time': 0.0, 'validation_time': 0.0,
            'quality_score': '', 'errors': ''
        }
        self.human_data = {
            'input_tokens': 0, 'output_tokens': 0, 'total_cost': 0.0,
            'iterations': 0, 'transform_time': 0.0, 'feedback_time': 0.0,
            'quality_score': '', 'errors': ''
        }

    def start_node(self, node_name: str, validation_mode: ValidationMode):
        """Startet Node-Timing"""
        self.current_mode = validation_mode
        self.current_node_start = time.time()

    def end_transform_node(self, cost: float, input_tokens: int, output_tokens: int):
        """Beendet Transform Node"""
        if self.current_node_start is None:
            return

        execution_time = time.time() - self.current_node_start

        if self.current_mode == ValidationMode.AUTOMATIC:
            self.auto_data['input_tokens'] += input_tokens
            self.auto_data['output_tokens'] += output_tokens
            self.auto_data['total_cost'] += cost
            self.auto_data['transform_time'] += execution_time
            self.auto_data['iterations'] += 1

        else:
            self.human_data['input_tokens'] += input_tokens
            self.human_data['output_tokens'] += output_tokens
            self.human_data['total_cost'] += cost
            self.human_data['transform_time'] += execution_time
            self.human_data['iterations'] += 1

    def end_validation_node(self, quality_score: float, cost: float, input_tokens: int = 0, output_tokens: int = 0, errors: str = ''):
        """Beendet Validation Node (nur AUTOMATIC)"""
        if self.current_node_start is None or self.current_mode != ValidationMode.AUTOMATIC:
            return

        execution_time = time.time() - self.current_node_start
        self.auto_data['validation_time'] += execution_time
        self.auto_data['total_cost'] += cost
        self.auto_data['input_tokens'] += input_tokens
        self.auto_data['output_tokens'] += output_tokens
        self.auto_data['errors'] = errors
        self.auto_data['quality_score'] += ";" + str(quality_score)

    def end_human_feedback_node(self, quality_score: float):
        """Beendet Human Feedback Node (nur HUMAN)"""
        if self.current_node_start is None or self.current_mode != ValidationMode.HUMAN:
            return

        execution_time = time.time() - self.current_node_start
        self.human_data['feedback_time'] += execution_time
        self.human_data['quality_score'] +=  ";" + str(quality_score)

    # def set_final_quality_score(self, validation_mode: ValidationMode, quality_score: float):
    #     """Setzt finalen Quality Score"""
    #     if validation_mode == ValidationMode.AUTOMATIC:
    #         self.auto_data['quality_score'] += ";" + str( quality_score )
    #     else:
    #         self.human_data['quality_score'] += ";" + str( quality_score )

    def export_to_sqlite(self, db_path: str = "experiment_results.db"):
        """Exportiert 2 Einträge pro Session"""
        conn = sqlite3.connect(db_path)

        # Vereinfachte Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS session_results (
                session_id TEXT,
                validation_mode TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_cost REAL,
                total_time REAL,
                iterations INTEGER,
                quality_score TEXT,
                raw_text_length INTEGER,
                errors TEXT,
                timestamp TEXT
            )
        ''')

        timestamp = datetime.now().isoformat()
        raw_text_length = len(self.raw_text) if self.raw_text else 0

        # AUTOMATIC Eintrag (nur wenn Daten vorhanden)
        if self.auto_data['iterations'] > 0:
            auto_total_time = self.auto_data['transform_time'] + self.auto_data['validation_time']
            conn.execute('''
                INSERT INTO session_results 
                (session_id, validation_mode, input_tokens, output_tokens, total_cost, 
                 total_time, iterations, quality_score, raw_text_length, errors ,timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.session_id, 'AUTOMATIC',
                self.auto_data['input_tokens'], self.auto_data['output_tokens'],
                self.auto_data['total_cost'], auto_total_time,
                self.auto_data['iterations'], self.auto_data['quality_score'],
                raw_text_length, self.auto_data['errors'], timestamp
            ))

        # HUMAN Eintrag (nur wenn Daten vorhanden)
        if self.human_data['iterations'] > 0:
            human_total_time = self.human_data['transform_time'] + self.human_data['feedback_time']
            conn.execute('''
                INSERT INTO session_results 
                (session_id, validation_mode, input_tokens, output_tokens, total_cost, 
                 total_time, iterations, quality_score, raw_text_length, errors,timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.session_id, 'HUMAN',
                self.human_data['input_tokens'], self.human_data['output_tokens'],
                self.human_data['total_cost'], human_total_time,
                self.human_data['iterations'], self.human_data['quality_score'],
                raw_text_length, self.human_data['errors'],timestamp
            ))

        conn.commit()
        conn.close()
        print(f"Session {self.session_id} exported to {db_path}")

    def export_to_json(self, json_path: str = "experiment_results.json"):
        timestamp = datetime.now().isoformat()

        export_data = {
            'session_id': self.session_id,
            'export_timestamp': timestamp,
            'raw_text_length': len(self.raw_text) if self.raw_text else 0,
            'modes': {}
        }

        if self.auto_data['iterations'] > 0:
            export_data['modes']['AUTOMATIC'] = {
                **self.auto_data,
                'total_time': self.auto_data['transform_time'] + self.auto_data['validation_time']
            }

        if self.human_data['iterations'] > 0:
            export_data['modes']['HUMAN'] = {
                **self.human_data,
                'total_time': self.human_data['transform_time'] + self.human_data['feedback_time']
            }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"Session {self.session_id} exported to {json_path}")

    def get_summary(self) -> Dict:
        """Gibt Session-Summary zurück"""
        return {
            'session_id': self.session_id,
            'automatic': self.auto_data if self.auto_data['iterations'] > 0 else None,
            'human': self.human_data if self.human_data['iterations'] > 0 else None
        }