from graphviz import Digraph

def generate_cfg():
    dot = Digraph(comment='RAG API Control Flow', format='png')
    dot.attr(rankdir='TB')

    # Nodes
    dot.node('start', 'Start: POST /query', shape='oval')
    dot.node('init_check', 'Check: rag_system is None?', shape='diamond')
    dot.node('err_500_init', 'Return 500: Init Error', shape='box', color='red')
    dot.node('try_block', 'Try: full_pipeline(query)', shape='box')
    dot.node('retrieve', 'Func: retrieve()', shape='component')
    dot.node('generate', 'Func: generate()', shape='component')
    dot.node('success', 'Return 200: JSON Result', shape='oval', color='green')
    dot.node('except_block', 'Except: Exception caught', shape='diamond')
    dot.node('err_500_runtime', 'Return 500: Runtime Error', shape='box', color='red')

    # Edges
    dot.edge('start', 'init_check')
    dot.edge('init_check', 'err_500_init', label='True')
    dot.edge('init_check', 'try_block', label='False')
    dot.edge('try_block', 'retrieve')
    dot.edge('retrieve', 'generate')
    dot.edge('generate', 'success')
    dot.edge('try_block', 'except_block', label='Error', style='dashed')
    dot.edge('retrieve', 'except_block', label='Error', style='dashed')
    dot.edge('generate', 'except_block', label='Error', style='dashed')
    dot.edge('except_block', 'err_500_runtime')

    output_path = dot.render('api_flow_graph', view=False)
    print(f"Graph generated at: {output_path}")

if __name__ == "__main__":
    generate_cfg()