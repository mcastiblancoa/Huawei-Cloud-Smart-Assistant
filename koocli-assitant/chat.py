from graph import build_graph
from config import graph_config

def stream_graph_updates(user_input: str):
    graph = build_graph()
    for event in graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config=graph_config,
        stream_mode="values",
    ):
        last_msg = event["messages"][-1]
        # No reimprimir mensajes del usuario (ya lo vemos en consola)
        if last_msg.type != "human":
            last_msg.pretty_print()


def run_chat_loop():
    print("🤖 Asistente Huawei Cloud — Escribí 'quit' o 'q' para salir\n")

    while True:
        try:
            user_input = input("User: ")
        except (EOFError, KeyboardInterrupt):
            print("\n👋 ¡Hasta luego!")
            break

        if user_input.lower() in ["quit", "exit", "q"]:
            print("👋 ¡Hasta luego!")
            break

        if not user_input.strip():
            continue

        try:
            stream_graph_updates(user_input)
        except Exception as e:
            # Mostrar el error real en vez de ocultarlo
            print(f"\n❌ Error: {type(e).__name__}: {e}\n")