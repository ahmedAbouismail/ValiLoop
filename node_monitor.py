import time
from typing import List

from session_collector import SessionCollector


class NodeMonitor:
    def __init__(self, node_name: str, session_collector: SessionCollector):
        self.node_name = node_name
        self.collector = session_collector
        self.start_time = None

    def start_timing(self, iteration: int):
        self.start_time = time.time()
        self.iteration = iteration

    def end_timing(self, cost: float = 0, tokens_input: int = 0, tokens_output: int = 0,
                   quality_score: float = None, errors: List['ValidationError'] = None):

        if self.start_time is None:
            return

        execution_time = time.time() - self.start_time
        error_count = len(errors) if errors else 0

        self.collector.log_node_execution(
            node_name=self.node_name,
            iteration=self.iteration,
            execution_time=execution_time,
            cost=cost,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            quality_score=quality_score,
            error_count=error_count,
            error_details=errors
        )