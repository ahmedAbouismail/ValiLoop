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
            'errors': '',
            'recipe_name': '',
            # Neue detaillierte Metriken
            'overall_f1': [],
            'overall_precision': [],
            'overall_recall': [],
            'ingredients_f1': [],
            'ingredients_precision': [],
            'ingredients_recall': [],
            'steps_f1': [],
            'steps_precision': [],
            'steps_recall': [],
            'metadata_f1': [],
            'metadata_precision': [],
            'metadata_recall': []
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
            'errors': '',
            'recipe_name': '',
            # Neue detaillierte Metriken
            'overall_f1': [],
            'overall_precision': [],
            'overall_recall': [],
            'ingredients_f1': [],
            'ingredients_precision': [],
            'ingredients_recall': [],
            'steps_f1': [],
            'steps_precision': [],
            'steps_recall': [],
            'metadata_f1': [],
            'metadata_precision': [],
            'metadata_recall': []
        }

        self.current_mode = None
        self.current_node_start = None

    def start_session(self, session_id: str, raw_text: str, recipe_name: str):
        """Startet neue Session"""
        self.session_id = session_id
        self.raw_text = raw_text
        self.session_start_time = time.time()

        # Reset data
        self.auto_data = {
            'input_tokens': 0, 'output_tokens': 0, 'total_cost': 0.0,
            'iterations': 0, 'transform_time': 0.0, 'validation_time': 0.0,
            'errors': '',
            'recipe_name': recipe_name,
            'overall_f1': [], 'overall_precision': [], 'overall_recall': [],
            'ingredients_f1': [], 'ingredients_precision': [], 'ingredients_recall': [],
            'steps_f1': [], 'steps_precision': [], 'steps_recall': [],
            'metadata_f1': [], 'metadata_precision': [], 'metadata_recall': []
        }
        self.human_data = {
            'input_tokens': 0, 'output_tokens': 0, 'total_cost': 0.0,
            'iterations': 0, 'transform_time': 0.0, 'feedback_time': 0.0,
            'errors': '',
            'recipe_name': recipe_name,
            'overall_f1': [], 'overall_precision': [], 'overall_recall': [],
            'ingredients_f1': [], 'ingredients_precision': [], 'ingredients_recall': [],
            'steps_f1': [], 'steps_precision': [], 'steps_recall': [],
            'metadata_f1': [], 'metadata_precision': [], 'metadata_recall': []
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

    def end_validation_node(self, quality_metrics: Dict, cost: float,
                            input_tokens: int = 0, output_tokens: int = 0, errors: str = ''):
        """Beendet Validation Node (nur AUTOMATIC) mit detaillierten Metriken"""
        if self.current_node_start is None or self.current_mode != ValidationMode.AUTOMATIC:
            return

        execution_time = time.time() - self.current_node_start
        self.auto_data['validation_time'] += execution_time
        self.auto_data['total_cost'] += cost
        self.auto_data['input_tokens'] += input_tokens
        self.auto_data['output_tokens'] += output_tokens
        self.auto_data['errors'] = errors

        # Speichere alle Metriken
        self.auto_data['overall_f1'].append(quality_metrics.get('overall_f1', 0.0))
        self.auto_data['overall_precision'].append(quality_metrics.get('overall_precision', 0.0))
        self.auto_data['overall_recall'].append(quality_metrics.get('overall_recall', 0.0))

        self.auto_data['ingredients_f1'].append(quality_metrics.get('ingredients_f1', 0.0))
        self.auto_data['ingredients_precision'].append(quality_metrics.get('ingredients_precision', 0.0))
        self.auto_data['ingredients_recall'].append(quality_metrics.get('ingredients_recall', 0.0))

        self.auto_data['steps_f1'].append(quality_metrics.get('steps_f1', 0.0))
        self.auto_data['steps_precision'].append(quality_metrics.get('steps_precision', 0.0))
        self.auto_data['steps_recall'].append(quality_metrics.get('steps_recall', 0.0))

        self.auto_data['metadata_f1'].append(quality_metrics.get('metadata_f1', 0.0))
        self.auto_data['metadata_precision'].append(quality_metrics.get('metadata_precision', 0.0))
        self.auto_data['metadata_recall'].append(quality_metrics.get('metadata_recall', 0.0))

    def end_human_feedback_node(self, quality_metrics: Dict):
        """Beendet Human Feedback Node (nur HUMAN) mit detaillierten Metriken"""
        if self.current_node_start is None or self.current_mode != ValidationMode.HUMAN:
            return

        execution_time = time.time() - self.current_node_start
        self.human_data['feedback_time'] += execution_time

        # Speichere alle Metriken
        self.human_data['overall_f1'].append(quality_metrics.get('overall_f1', 0.0))
        self.human_data['overall_precision'].append(quality_metrics.get('overall_precision', 0.0))
        self.human_data['overall_recall'].append(quality_metrics.get('overall_recall', 0.0))

        self.human_data['ingredients_f1'].append(quality_metrics.get('ingredients_f1', 0.0))
        self.human_data['ingredients_precision'].append(quality_metrics.get('ingredients_precision', 0.0))
        self.human_data['ingredients_recall'].append(quality_metrics.get('ingredients_recall', 0.0))

        self.human_data['steps_f1'].append(quality_metrics.get('steps_f1', 0.0))
        self.human_data['steps_precision'].append(quality_metrics.get('steps_precision', 0.0))
        self.human_data['steps_recall'].append(quality_metrics.get('steps_recall', 0.0))

        self.human_data['metadata_f1'].append(quality_metrics.get('metadata_f1', 0.0))
        self.human_data['metadata_precision'].append(quality_metrics.get('metadata_precision', 0.0))
        self.human_data['metadata_recall'].append(quality_metrics.get('metadata_recall', 0.0))

    # def set_final_quality_score(self, validation_mode: ValidationMode, quality_score: float):
    #     """Setzt finalen Quality Score"""
    #     if validation_mode == ValidationMode.AUTOMATIC:
    #         self.auto_data['quality_score'] += ";" + str( quality_score )
    #     else:
    #         self.human_data['quality_score'] += ";" + str( quality_score )

    def export_to_sqlite(self, db_path: str = "experiment_results.db"):
        """Exportiert Daten mit detaillierten Metriken in SQLite"""
        conn = sqlite3.connect(db_path)

        # Erweiterte Tabelle mit allen Metriken
        conn.execute('''
            CREATE TABLE IF NOT EXISTS session_results (
                session_id TEXT,
                validation_mode TEXT,
                recipe_name TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_cost REAL,
                total_time REAL,
                iterations INTEGER,
                raw_text_length INTEGER,
                errors TEXT,
                timestamp TEXT,
                
                -- Overall Metriken (als Komma-getrennte Liste für alle Iterationen)
                overall_f1 TEXT,
                overall_precision TEXT,
                overall_recall TEXT,
                
                -- Ingredients Metriken
                ingredients_f1 TEXT,
                ingredients_precision TEXT,
                ingredients_recall TEXT,
                
                -- Steps Metriken
                steps_f1 TEXT,
                steps_precision TEXT,
                steps_recall TEXT,
                
                -- Metadata Metriken
                metadata_f1 TEXT,
                metadata_precision TEXT,
                metadata_recall TEXT
            )
        ''')

        timestamp = datetime.now().isoformat()
        raw_text_length = len(self.raw_text) if self.raw_text else 0

        # Helper Funktion zum Konvertieren von Listen zu Strings
        def list_to_str(lst):
            return ','.join([f"{x:.4f}" for x in lst]) if lst else ''

        # AUTOMATIC Eintrag
        if self.auto_data['iterations'] > 0:
            auto_total_time = self.auto_data['transform_time'] + self.auto_data['validation_time']
            conn.execute('''
                INSERT INTO session_results 
                (session_id, validation_mode, recipe_name ,input_tokens, output_tokens, total_cost, 
                 total_time, iterations, raw_text_length, errors, timestamp,
                 overall_f1, overall_precision, overall_recall,
                 ingredients_f1, ingredients_precision, ingredients_recall,
                 steps_f1, steps_precision, steps_recall,
                 metadata_f1, metadata_precision, metadata_recall)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.session_id, 'AUTOMATIC', self.auto_data['recipe_name'],
                self.auto_data['input_tokens'], self.auto_data['output_tokens'],
                self.auto_data['total_cost'], auto_total_time,
                self.auto_data['iterations'], raw_text_length,
                self.auto_data['errors'], timestamp,
                list_to_str(self.auto_data['overall_f1']),
                list_to_str(self.auto_data['overall_precision']),
                list_to_str(self.auto_data['overall_recall']),
                list_to_str(self.auto_data['ingredients_f1']),
                list_to_str(self.auto_data['ingredients_precision']),
                list_to_str(self.auto_data['ingredients_recall']),
                list_to_str(self.auto_data['steps_f1']),
                list_to_str(self.auto_data['steps_precision']),
                list_to_str(self.auto_data['steps_recall']),
                list_to_str(self.auto_data['metadata_f1']),
                list_to_str(self.auto_data['metadata_precision']),
                list_to_str(self.auto_data['metadata_recall'])
            ))

        # HUMAN Eintrag
        if self.human_data['iterations'] > 0:
            human_total_time = self.human_data['transform_time'] + self.human_data['feedback_time']
            conn.execute('''
                INSERT INTO session_results 
                (session_id, validation_mode, recipe_name,input_tokens, output_tokens, total_cost, 
                 total_time, iterations, raw_text_length, errors, timestamp,
                 overall_f1, overall_precision, overall_recall,
                 ingredients_f1, ingredients_precision, ingredients_recall,
                 steps_f1, steps_precision, steps_recall,
                 metadata_f1, metadata_precision, metadata_recall)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.session_id, 'HUMAN', self.human_data['recipe_name'],
                self.human_data['input_tokens'], self.human_data['output_tokens'],
                self.human_data['total_cost'], human_total_time,
                self.human_data['iterations'], raw_text_length,
                self.human_data['errors'], timestamp,
                list_to_str(self.human_data['overall_f1']),
                list_to_str(self.human_data['overall_precision']),
                list_to_str(self.human_data['overall_recall']),
                list_to_str(self.human_data['ingredients_f1']),
                list_to_str(self.human_data['ingredients_precision']),
                list_to_str(self.human_data['ingredients_recall']),
                list_to_str(self.human_data['steps_f1']),
                list_to_str(self.human_data['steps_precision']),
                list_to_str(self.human_data['steps_recall']),
                list_to_str(self.human_data['metadata_f1']),
                list_to_str(self.human_data['metadata_precision']),
                list_to_str(self.human_data['metadata_recall'])
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