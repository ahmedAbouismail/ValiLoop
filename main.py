import json
import os
import uuid
from langgraph.checkpoint.sqlite import SqliteSaver
from create_json_processing_graph import create_json_processing_graph
from data_moduels.validation_mode import ValidationMode
from shared_session_collector import session_collector

def main():
    # Create graph
    graph = create_json_processing_graph()

    # Load schema
    with open('assets/output_schema.json', 'r', encoding='utf-8') as f:
        recipe_schema = json.load(f)

    with SqliteSaver.from_conn_string(":memory:") as checkpointer:
        app = graph.compile(checkpointer=checkpointer)

        # Test both validation modes
        test_cases = [
            ("automatic", ValidationMode.AUTOMATIC),
            ("human", ValidationMode.HUMAN)
        ]

        # Alle Rezepte aus assets/recipes/ laden
        recipes_dir = 'assets/recipes'
        recipe_files = [f for f in os.listdir(recipes_dir) if f.endswith('.txt')]
        #recipe_files = ['erbsencremesuppe.txt']
        print(f"Gefundene Rezepte: {recipe_files}")

        for recipe_file in recipe_files:
            recipe_name = recipe_file[:-4]  # Entferne .txt Extension
            recipe_path = os.path.join(recipes_dir, recipe_file)

            # Rezept-Text laden
            with open(recipe_path, 'r', encoding='utf-8') as f:
                recipe_text = f.read()

            print(f"\n{'='*60}")
            print(f"VERARBEITE REZEPT: {recipe_name}")
            print(f"{'='*60}")

            # Eine Session pro Rezept starten
            session_id = str(uuid.uuid4())
            session_collector.start_session(session_id, recipe_text)

            for test_name, validation_mode in test_cases:
                print(f"\n{'='*50}")
                print(f"Testing {test_name.upper()} validation mode für {recipe_name}")
                print(f"{'='*50}")

                config = {"configurable": {"thread_id": f"{session_id}_{validation_mode.value}"}}

                result = app.invoke({
                    "recipe_name": recipe_name,
                    "raw_text": recipe_text,
                    "text": recipe_text,
                    "target_schema": recipe_schema,
                    "domain": "recipe",
                    "validation_mode": validation_mode,
                    "max_iterations": 2
                }, config)

                print(f"\n=== FINAL RESULT ({test_name}) ===")
                print(json.dumps(result["final_output"], indent=2, ensure_ascii=False))

                print(f"\n=== PROCESSING DETAILS ===")
                print(f"Recipe: {recipe_name}")
                print(f"Iterations used: {result.get('iteration_count', 0)}")
                print(f"Quality Score: {result.get('quality_score', 0):.2f}")

                if result.get('validation_errors'):
                    print(f"\nRemaining Issues ({len(result['validation_errors'])}):")
                    for error in result['validation_errors']:
                        severity = error.severity.upper() if isinstance(error.severity, str) else error.severity.value
                        print(f"- {severity}: {error.message}")


            session_collector.export_to_sqlite("experiment_results.db")
            session_collector.export_to_json("experiment_results.json")

            # Session Summary für aktuelles Rezept
            print(f"\n=== SESSION SUMMARY für {recipe_name} ===")
            summary = session_collector.get_summary()

            if summary['automatic']:
                auto = summary['automatic']
                total_time = auto['transform_time'] + auto['validation_time']
                print(f"\nAUTOMATIC Mode:")
                print(f"  Tokens: {auto['input_tokens']}/{auto['output_tokens']}")
                print(f"  Cost: ${auto['total_cost']:.4f}")
                print(f"  Time: {total_time:.2f}s")
                print(f"  Iterations: {auto['iterations']}")
                print(f"  Quality: {auto['quality_score']:.3f}")

            if summary['human']:
                human = summary['human']
                total_time = human['transform_time'] + human['feedback_time']
                print(f"\nHUMAN Mode:")
                print(f"  Tokens: {human['input_tokens']}/{human['output_tokens']}")
                print(f"  Cost: ${human['total_cost']:.4f}")
                print(f"  Time: {total_time:.2f}s")
                print(f"  Iterations: {human['iterations']}")
                print(f"  Quality: {human['quality_score']:.3f}")

    # Final Export und Analysis
    print(f"\n{'='*50}")
    print("FINAL ANALYSIS")
    print(f"{'='*50}")

    #session_collector.export_to_sqlite("experiment_results.db")
    #session_collector.export_to_json("experiment_results.json")
    show_basic_analysis()


def show_basic_analysis():
    """Zeigt grundlegende Analyse der vereinfachten Daten"""
    import sqlite3

    conn = sqlite3.connect("experiment_results.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT validation_mode, 
               COUNT(*) as sessions,
               AVG(quality_score) as avg_quality,
               AVG(total_time) as avg_time,
               SUM(total_cost) as total_cost,
               AVG(iterations) as avg_iterations
        FROM session_results 
        GROUP BY validation_mode
    """)

    print("\n" + "="*60)
    print("SESSION ANALYSIS:")
    print("="*60)
    print("Mode\t\tSessions\tAvg Quality\tAvg Time\tTotal Cost\tAvg Iter")
    print("-" * 70)

    rows = cursor.fetchall()
    if not rows:
        print("No session data found.")
    else:
        for row in rows:
            mode, sessions, quality, time_avg, cost, iterations = row
            mode_str = mode or "unknown"
            quality_str = f"{quality:.3f}" if quality is not None else "N/A"
            time_str = f"{time_avg:.1f}s" if time_avg is not None else "N/A"
            cost_str = f"${cost:.4f}" if cost is not None else "$0.0000"
            iter_str = f"{iterations:.1f}" if iterations is not None else "N/A"
            print(f"{mode_str}\t{sessions}\t\t{quality_str}\t\t{time_str}\t\t{cost_str}\t\t{iter_str}")

    # Session Details
    print("\n" + "="*60)
    print("SESSION DETAILS:")
    print("="*60)

    cursor.execute("""
        SELECT session_id, validation_mode, quality_score, total_time, iterations
        FROM session_results 
        ORDER BY session_id, validation_mode
    """)

    details = cursor.fetchall()
    if details:
        print("Session\t\tMode\t\tQuality\tTime\tIterations")
        print("-" * 60)
        for row in details:
            session_id, mode, quality, time_val, iterations = row
            short_session = session_id[:8] if session_id else "unknown"
            mode_str = mode or "unknown"
            quality_str = f"{quality:.3f}" if quality is not None else "N/A"
            time_str = f"{time_val:.1f}s" if time_val is not None else "N/A"
            iter_str = str(iterations) if iterations is not None else "N/A"
            print(f"{short_session}\t{mode_str}\t\t{quality_str}\t{time_str}\t{iter_str}")

    conn.close()


if __name__ == "__main__":
    main()