import igraph as ig
print('igraph imported OK, version:', ig.__version__)
try:
    G = ig.Graph.Read_Picklez('datasets/physics/graph_igraph_data.pklz')
    print(G.summary())
    print('igraph file is VALID')
except Exception as e:
    print('igraph file FAILED:', e)
