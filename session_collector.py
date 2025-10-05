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
            'quality_score': 0.0,
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
            'quality_score': 0.0,
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
            'quality_score': 0.0, 'errors': ''
        }
        self.human_data = {
            'input_tokens': 0, 'output_tokens': 0, 'total_cost': 0.0,
            'iterations': 0, 'transform_time': 0.0, 'feedback_time': 0.0,
            'quality_score': 0.0, 'errors': ''
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

    def end_validation_node(self, cost: float, input_tokens: int = 0, output_tokens: int = 0, errors: str = ''):
        """Beendet Validation Node (nur AUTOMATIC)"""
        if self.current_node_start is None or self.current_mode != ValidationMode.AUTOMATIC:
            return

        execution_time = time.time() - self.current_node_start
        self.auto_data['validation_time'] += execution_time
        self.auto_data['total_cost'] += cost
        self.auto_data['input_tokens'] += input_tokens
        self.auto_data['output_tokens'] += output_tokens
        self.auto_data['errors'] = errors

    def end_human_feedback_node(self):
        """Beendet Human Feedback Node (nur HUMAN)"""
        if self.current_node_start is None or self.current_mode != ValidationMode.HUMAN:
            return

        execution_time = time.time() - self.current_node_start
        self.human_data['feedback_time'] += execution_time

    def set_final_quality_score(self, validation_mode: ValidationMode, quality_score: float):
        """Setzt finalen Quality Score"""
        if validation_mode == ValidationMode.AUTOMATIC:
            self.auto_data['quality_score'] = quality_score
        else:
            self.human_data['quality_score'] = quality_score

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
                quality_score REAL,
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

# import json
# import sqlite3
# import time
# from datetime import datetime
# from typing import List
#
# from data_moduels.validation_mode import ValidationMode
#
#
# class SessionCollector:
#     """Zentrale Datensammlung für alle Nodes"""
#
#     def __init__(self):
#         self.session_data = []
#         self.current_session_id = None
#         self.current_run_id = None  # NEW: Track individual runs
#         self.session_start_time = None
#         self.validation_mode = None
#
#     def start_session(self, session_id: str, validation_mode: ValidationMode, raw_text: str):
#         """Startet neue Session-Tracking"""
#         self.current_session_id = session_id
#         self.current_run_id = f"{session_id}_{validation_mode.value}"  # NEW: Unique run identifier
#         self.validation_mode = validation_mode
#         self.session_start_time = time.time()
#
#         # Initial session record
#         self.log_data({
#             'session_id': session_id,
#             'run_id': self.current_run_id,  # NEW: Add run_id
#             'validation_mode': validation_mode.value,  # Fixed typo: was 'validation_mode.py'
#             'raw_text': raw_text,
#             'raw_text_length': len(raw_text),
#             'session_start': datetime.now().isoformat(),
#             'event_type': 'session_start'
#         })
#
#     def log_node_execution(self, node_name: str, iteration: int, execution_time: float,
#                            cost: float = 0, tokens_input: int = 0, tokens_output: int = 0,
#                            quality_score: float = None, error_count: int = 0,
#                            error_details: List['ValidationError'] = None):
#         """Loggt Node-Ausführung"""
#
#         data = {
#             'session_id': self.current_session_id,
#             'run_id': self.current_run_id,  # NEW: Add run_id
#             'validation_mode': self.validation_mode.value,
#             'iteration': iteration,
#             'node_name': node_name,
#             'execution_time': execution_time,
#             'cost': cost,
#             'tokens_input': tokens_input,
#             'tokens_output': tokens_output,
#             'quality_score': quality_score,
#             'error_count': error_count,
#             'timestamp': datetime.now().isoformat(),
#             'event_type': 'node_execution'
#         }
#
#         # Add error details if present
#         if error_details:
#             for error in error_details:
#                 error_data = data.copy()
#                 error_data.update({
#                     'error_type': error.type,
#                     'error_severity': error.severity if isinstance(error.severity, str) else error.severity.value,
#                     'error_field_path': error.field_path,
#                     'error_message': error.message,
#                     'suggested_fix': error.suggested_fix,
#                     'event_type': 'error_logged'
#                 })
#                 self.session_data.append(error_data)
#         else:
#             self.session_data.append(data)
#
#     def log_human_interaction(self, iteration: int, response_time: float,
#                               feedback_length: int, feedback_type: str):
#         """Loggt Human-Feedback Details"""
#         self.log_data({
#             'session_id': self.current_session_id,
#             'run_id': self.current_run_id,  # NEW: Add run_id
#             'validation_mode': self.validation_mode.value,
#             'iteration': iteration,
#             'human_response_time': response_time,
#             'feedback_length': feedback_length,
#             'feedback_type': feedback_type,
#             'event_type': 'human_interaction'
#         })
#
#     def finish_session(self, final_quality: float, success: bool, total_iterations: int):
#         """Beendet Session und loggt finale Metriken"""
#         total_time = time.time() - self.session_start_time
#
#         self.log_data({
#             'session_id': self.current_session_id,
#             'run_id': self.current_run_id,  # NEW: Add run_id
#             'validation_mode': self.validation_mode.value,
#             'total_time': total_time,
#             'final_quality': final_quality,
#             'success': success,
#             'total_iterations': total_iterations,
#             'session_end': datetime.now().isoformat(),
#             'event_type': 'session_end'
#         })
#
#     def log_data(self, data: dict):
#         """Interne Methode zum Hinzufügen von Daten"""
#         self.session_data.append(data)
#
#     def export_to_sqlite(self, db_path: str = "experiment_data.db"):
#         """Exportiert alle Daten zu SQLite (denormalisiert)"""
#         conn = sqlite3.connect(db_path)
#
#         # Create denormalized table with run_id
#         conn.execute('''
#             CREATE TABLE IF NOT EXISTS processing_data (
#                 session_id TEXT,
#                 run_id TEXT,
#                 validation_mode TEXT,
#                 raw_text TEXT,
#                 raw_text_length INTEGER,
#                 iteration INTEGER,
#                 node_name TEXT,
#                 execution_time REAL,
#                 cost REAL,
#                 tokens_input INTEGER,
#                 tokens_output INTEGER,
#                 quality_score REAL,
#                 error_count INTEGER,
#                 error_type TEXT,
#                 error_severity TEXT,
#                 error_field_path TEXT,
#                 error_message TEXT,
#                 suggested_fix TEXT,
#                 human_response_time REAL,
#                 feedback_length INTEGER,
#                 feedback_type TEXT,
#                 total_time REAL,
#                 final_quality REAL,
#                 success BOOLEAN,
#                 total_iterations INTEGER,
#                 timestamp TEXT,
#                 event_type TEXT
#             )
#         ''')
#
#         # Insert all collected data
#         for data in self.session_data:
#             # Fill missing fields with None
#             complete_data = {
#                 'session_id': data.get('session_id'),
#                 'run_id': data.get('run_id'),  # NEW: Add run_id
#                 'validation_mode': data.get('validation_mode'),  # Fixed typo
#                 'raw_text': data.get('raw_text'),
#                 'raw_text_length': data.get('raw_text_length'),
#                 'iteration': data.get('iteration'),
#                 'node_name': data.get('node_name'),
#                 'execution_time': data.get('execution_time'),
#                 'cost': data.get('cost'),
#                 'tokens_input': data.get('tokens_input'),
#                 'tokens_output': data.get('tokens_output'),
#                 'quality_score': data.get('quality_score'),
#                 'error_count': data.get('error_count'),
#                 'error_type': data.get('error_type'),
#                 'error_severity': data.get('error_severity'),
#                 'error_field_path': data.get('error_field_path'),
#                 'error_message': data.get('error_message'),
#                 'suggested_fix': data.get('suggested_fix'),
#                 'human_response_time': data.get('human_response_time'),
#                 'feedback_length': data.get('feedback_length'),
#                 'feedback_type': data.get('feedback_type'),
#                 'total_time': data.get('total_time'),
#                 'final_quality': data.get('final_quality'),
#                 'success': data.get('success'),
#                 'total_iterations': data.get('total_iterations'),
#                 'timestamp': data.get('timestamp'),
#                 'event_type': data.get('event_type')
#             }
#
#             placeholders = ', '.join(['?' for _ in complete_data])
#             columns = ', '.join(complete_data.keys())
#
#             conn.execute(
#                 f'INSERT INTO processing_data ({columns}) VALUES ({placeholders})',
#                 list(complete_data.values())
#             )
#
#         conn.commit()
#         conn.close()
#         print(f"Exported {len(self.session_data)} records to {db_path}")
#
#     def export_to_json(self, json_path: str = "experiment_data.json"):
#         """Exportiert Session-Daten zu JSON"""
#         export_data = {
#             'export_timestamp': datetime.now().isoformat(),
#             'total_records': len(self.session_data),
#             'runs': self._group_by_run(),  # CHANGED: Group by run instead of session
#             'raw_data': self.session_data
#         }
#
#         with open(json_path, 'w', encoding='utf-8') as f:
#             json.dump(export_data, f, indent=2, ensure_ascii=False)
#
#         print(f"Exported session data to {json_path}")
#
#     def _group_by_run(self):  # RENAMED and UPDATED
#         """Gruppiert Daten nach Runs (session_id + validation_mode) für bessere JSON-Struktur"""
#         runs = {}
#
#         for data in self.session_data:
#             run_id = data.get('run_id')
#             if run_id not in runs:
#                 runs[run_id] = {
#                     'run_info': {},
#                     'iterations': {},
#                     'errors': [],
#                     'human_interactions': [],
#                     'session_id': data.get('session_id'),
#                     'validation_mode': data.get('validation_mode')
#                 }
#
#             event_type = data.get('event_type')
#             if event_type == 'session_start':
#                 runs[run_id]['run_info'] = data
#             elif event_type == 'node_execution':
#                 iteration = data.get('iteration', 0)
#                 if iteration not in runs[run_id]['iterations']:
#                     runs[run_id]['iterations'][iteration] = []
#                 runs[run_id]['iterations'][iteration].append(data)
#             elif event_type == 'error_logged':
#                 runs[run_id]['errors'].append(data)
#             elif event_type == 'human_interaction':
#                 runs[run_id]['human_interactions'].append(data)
#
#         return runs
#
#     def clear_session_data(self):
#         """Leert gesammelte Daten nach Export"""
#         self.session_data = []
#         self.current_session_id = None
#         self.current_run_id = None  # NEW: Reset run_id
#         self.session_start_time = None